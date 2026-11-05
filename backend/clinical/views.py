from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from audit.services import record_audit
from doctors.models import Doctor
from .models import (
    Immunization,
    VitalSign,
    Allergy,
    ClinicalNote,
    Diagnosis,
    ServiceOrder,
    Procedure,
    MedicalRecord,
    Prescription,
    PrescriptionItem,
    MedicalCertificate,
    Referral,
)

from .serializers import (
    ImmunizationSerializer,
    VitalSignSerializer,
    AllergySerializer,
    ClinicalNoteSerializer,
    DiagnosisSerializer,
    ServiceOrderSerializer,
    ProcedureSerializer,
    MedicalRecordSerializer,
    PrescriptionSerializer,
    PrescriptionItemSerializer,
    PrescriptionTranscriptionSerializer,
    MedicalCertificateSerializer,
    ReferralSerializer,
)
from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    IsAdmin,
    IsCompounderReadOnly,
    IsHospitalManager,
    IsDoctor,
    IsNurse,
    IsNurseReadOnly,
    IsPharmacist,
    IsPharmacistReadOnly,
    IsPatientReadOnly,
    IsReceptionistReadOnly,
)


class VitalSignViewSet(HospitalScopedViewSet):
    queryset = VitalSign.objects.select_related(
        "visit", "visit__patient", "visit__doctor", "visit__hospital", "recorded_by").order_by("-recorded_at", "-id")
    serializer_class = VitalSignSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]

    def perform_create(self, serializer):
        # D2: the login that took the reading, never sent by the client.
        extra = self._check_tenancy(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user, **extra)
        self._audit("create", instance)


class AllergyViewSet(HospitalScopedViewSet):
    queryset = Allergy.objects.select_related("patient").order_by("-created_at", "-id")
    serializer_class = AllergySerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset


class ClinicalNoteViewSet(HospitalScopedViewSet):
    queryset = ClinicalNote.objects.select_related(
        "visit", "visit__patient", "visit__doctor", "visit__hospital", "doctor"
    ).order_by("-created_at", "-id")
    serializer_class = ClinicalNoteSerializer
    permission_classes = [IsAdmin | IsDoctor]


class DiagnosisViewSet(HospitalScopedViewSet):
    queryset = Diagnosis.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = DiagnosisSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user, **extra)
        self._audit("create", instance)


class ServiceOrderViewSet(HospitalScopedViewSet):
    queryset = ServiceOrder.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class ProcedureViewSet(HospitalScopedViewSet):
    queryset = Procedure.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = ProcedureSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]


class MedicalRecordViewSet(HospitalScopedViewSet):
    queryset = MedicalRecord.objects.select_related("patient", "visit", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


MAX_SAFETY_CHECK_ITEMS = 50


def _prescription_search(text, model):
    """RX number (RX-0001 or 1), patient name, the patient's UHID at that hospital, or doctor name."""
    from django.db.models import F, Q

    match = Q(patient__name__icontains=text) | Q(doctor__name__icontains=text) | Q(
        original_prescriber_name__icontains=text)
    number = text.upper().removeprefix("RX-").lstrip("0")
    if number.isdigit():
        match |= Q(pk=int(number))
    uhid = model.objects.filter(
        patient__hospital_memberships__hospital_id=F("hospital_id"),
        patient__hospital_memberships__uhid__icontains=text,
    ).values("pk")
    return match | Q(pk__in=uhid)


class PrescriptionViewSet(HospitalScopedViewSet):
    # Restrictable on the Permissions page as "Prescriptions" (users/module_access.py).
    access_module = "Prescriptions"
    queryset = Prescription.objects.select_related(
        "patient", "doctor", "hospital", "visit", "transcribed_by", "verified_by"
    ).prefetch_related("items", "items__pharmacy_sales", "patient__hospital_memberships")
    serializer_class = PrescriptionSerializer
    # Clinical records: not for the Hospital Manager. Nurses (MAR), the
    # compounder (dispensing) and the front desk (reports) only read them.
    # F13: pharmacists do not prescribe; they transcribe paper prescriptions
    # (transcribe) and check one another's transcriptions (verify).
    permission_classes = [
        IsAdmin | IsDoctor | IsPharmacistReadOnly | IsPatientReadOnly
        | IsReceptionistReadOnly | IsNurseReadOnly | IsCompounderReadOnly
    ]

    def get_permissions(self):
        if getattr(self, "action", None) in ("transcribe", "verify"):
            return [(IsAdmin | IsPharmacist)()]
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def transcribe(self, request):
        """
        A paper prescription copied in by the pharmacy (F13). Same body as a
        prescription plus original_prescription_date and either ``doctor`` (a
        doctor of this hospital) or original_prescriber_name and
        original_prescriber_registration (an outside doctor). Saved Pending
        Verification; it cannot be dispensed until someone else verifies it.
        """
        serializer = PrescriptionTranscriptionSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        extra = self._check_tenancy(serializer.validated_data)
        prescription = serializer.save(
            source=Prescription.Source.PAPER, status=Prescription.PENDING_VERIFICATION,
            transcribed_by=request.user, **extra,
        )
        record_audit(request, "clinical.prescription.transcribed", prescription, hospital=prescription.hospital_id,
                     details={"doctor": prescription.doctor_id,
                              "prescriber": prescription.original_prescriber_name,
                              "registration": prescription.original_prescriber_registration,
                              "paper_date": str(prescription.original_prescription_date)})
        return Response(PrescriptionSerializer(prescription, context=self.get_serializer_context()).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def verify(self, request, pk=None):
        """A second pharmacist or an Admin confirms a transcription matches the paper."""
        prescription = self.get_object()
        prescription = Prescription.objects.select_for_update().get(pk=prescription.pk)
        if prescription.status != Prescription.PENDING_VERIFICATION:
            raise ValidationError({"status": "Only a transcription waiting for verification can be verified."})
        if prescription.transcribed_by_id == request.user.pk:
            raise PermissionDenied("Someone other than the person who transcribed it must verify it.")
        prescription.status = "Confirmed"
        prescription.verified_by = request.user
        prescription.verified_at = timezone.now()
        prescription.save(update_fields=["status", "verified_by", "verified_at"])
        record_audit(request, "clinical.prescription.verified", prescription, hospital=prescription.hospital_id,
                     details={"transcribed_by": prescription.transcribed_by_id})
        return Response(self.get_serializer(prescription).data)

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        visit_id = self.request.query_params.get("visit")
        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)

        # F6: the pharmacy queue asks for several statuses at once ("Confirmed,Partially Dispensed").
        status_filter = self.request.query_params.get("status")
        if status_filter:
            statuses = [value.strip() for value in status_filter.split(",") if value.strip()]
            queryset = queryset.filter(status__in=statuses)

        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(_prescription_search(search, queryset.model))

        if self.request.query_params.get("order") == "oldest":
            queryset = queryset.order_by("created_at", "id")

        return queryset

    @action(detail=False, methods=["post"], url_path="safety-check")
    def safety_check(self, request):
        """
        Medication safety alerts for a prescription before it is saved.

        Body: {"hospital": id, "patient": id, "items": [{"name": "Tab Ibuprofen 400"}, ...]}
        """
        from hospital.models import Hospital
        from patients.models import Patient
        from users.permissions import get_user_hospital_ids

        from . import safety_rules
        from .medication_safety import check_items
        from .serializers import _patient_belongs_to_hospital

        try:
            hospital_id = int(request.data.get("hospital"))
            patient_id = int(request.data.get("patient"))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "hospital and patient are required."})
        if hospital_id not in get_user_hospital_ids(request.user):
            raise PermissionDenied("You do not have access to this hospital.")
        items = request.data.get("items") or []
        if not isinstance(items, list) or len(items) > MAX_SAFETY_CHECK_ITEMS:
            raise ValidationError({"items": f"Send a list of at most {MAX_SAFETY_CHECK_ITEMS} medicines."})

        hospital = Hospital.objects.filter(pk=hospital_id).first()
        patient = Patient.objects.filter(pk=patient_id).first()
        if hospital is None or patient is None or not _patient_belongs_to_hospital(patient, hospital):
            raise ValidationError({"patient": "This patient is not registered in this hospital."})

        names = [str(item.get("name") or "")[:200] for item in items if isinstance(item, dict)]
        return Response({
            "alerts": check_items(hospital, patient, names),
            "rules_version": safety_rules.RULES_VERSION,
            "review_status": safety_rules.REVIEW_STATUS,
        })


class PrescriptionItemViewSet(HospitalScopedViewSet):
    """
    Read-only. Medicines change only through the prescription itself
    (PrescriptionSerializer), which re-runs the medication safety check;
    writing a line here would skip it (RL-01).
    """

    queryset = PrescriptionItem.objects.select_related("prescription")
    serializer_class = PrescriptionItemSerializer
    permission_classes = [IsAdmin | IsDoctor | IsPharmacistReadOnly | IsNurseReadOnly | IsCompounderReadOnly]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()

        prescription_id = self.request.query_params.get("prescription")
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)

        return queryset


def _signing_doctor(user, hospital):
    """The signed-in user's doctor profile at ``hospital``: only a doctor signs."""
    doctor = Doctor.objects.filter(user=user, hospital=hospital).first()
    if doctor is None:
        raise ValidationError("Only a doctor of this hospital can sign this; your account has no doctor profile here.")
    return doctor


class _SignedByDoctorViewSet(HospitalScopedViewSet):
    """Creates rows signed by the requesting doctor, stored in ``signer_field``."""

    signer_field = "doctor"

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        hospital = serializer.validated_data.get("hospital") or extra.get("hospital")
        if hospital is None:
            raise ValidationError({"hospital": "Choose the hospital."})
        extra[self.signer_field] = _signing_doctor(self.request.user, hospital)
        instance = serializer.save(**extra)
        self._audit("create", instance)


class MedicalCertificateViewSet(_SignedByDoctorViewSet):
    """Certificates are legal documents: issued and read, never edited or deleted."""

    queryset = MedicalCertificate.objects.select_related("patient", "doctor", "hospital")
    serializer_class = MedicalCertificateSerializer
    permission_classes = [IsDoctor | IsPatientReadOnly]
    http_method_names = ["get", "post", "head", "options"]


class ReferralViewSet(_SignedByDoctorViewSet):
    queryset = Referral.objects.select_related(
        "patient", "referring_doctor", "referred_to_doctor", "hospital"
    )
    serializer_class = ReferralSerializer
    permission_classes = [IsDoctor | IsPatientReadOnly]
    http_method_names = ["get", "post", "patch", "head", "options"]
    signer_field = "referring_doctor"

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class ImmunizationViewSet(HospitalScopedViewSet):
    """Vaccination register (D15). Corrections are audited; doses are never deleted."""

    queryset = Immunization.objects.select_related("patient", "hospital", "recorded_by")
    serializer_class = ImmunizationSerializer
    permission_classes = [IsAdmin | IsDoctor | IsNurse | IsPatientReadOnly]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if self.request.query_params.get("due") == "1":
            queryset = queryset.filter(next_due_on__isnull=False).order_by("next_due_on")
        return queryset

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user, **extra)
        self._audit("create", instance)
