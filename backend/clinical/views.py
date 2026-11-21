from django.db import IntegrityError, transaction
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
    PrescriptionRevision,
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
from users.models import StaffRole
from users.viewsets import HospitalScopedViewSet

from .signing import SignedRecordMixin, check_amends
from users.permissions import (
    get_request_hospital_id,
    get_user_hospital_ids,
    get_user_roles,
    IsAdminReadOnly,
    IsHospitalManagerReadOnly,
    IsCompounderReadOnly,
    IsNurseReadOnly,
    IsDoctorOnly,
    IsNurseOnly,
    IsPharmacistOnly,
    IsPharmacistReadOnly,
    IsPatientReadOnly,
    IsReceptionistReadOnly,
)


class VisitFilterMixin:
    """
    ``?visit=<id>`` narrows a per-visit clinical list to that visit. The
    hospital and care scope of the base queryset still apply first, so the
    filter can only ever remove rows. Without the parameter nothing changes.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        visit_id = self.request.query_params.get("visit")
        if visit_id in (None, ""):
            return queryset
        # isdigit() also accepts "²", which int() then rejects with a 500.
        if not (str(visit_id).isascii() and str(visit_id).isdecimal()):
            raise ValidationError({"visit": "Use a visit id (a number)."})
        return queryset.filter(visit_id=int(visit_id))


class VitalSignViewSet(VisitFilterMixin, HospitalScopedViewSet):
    queryset = VitalSign.objects.select_related(
        "visit", "visit__patient", "visit__doctor", "visit__hospital", "recorded_by").order_by("-recorded_at", "-id")
    serializer_class = VitalSignSerializer
    permission_classes = [IsDoctorOnly | IsNurseOnly | IsAdminReadOnly | IsHospitalManagerReadOnly]

    def perform_create(self, serializer):
        # D2: the login that took the reading, never sent by the client.
        extra = self._check_tenancy(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user, **extra)
        self._audit("create", instance)


class AllergyViewSet(HospitalScopedViewSet):
    queryset = Allergy.objects.select_related("patient").order_by("-created_at", "-id")
    serializer_class = AllergySerializer
    permission_classes = [IsDoctorOnly | IsNurseOnly | IsAdminReadOnly | IsHospitalManagerReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset

    def perform_create(self, serializer):
        super().perform_create(serializer)
        # An allergy on record replaces an earlier "No known allergies"; if it
        # is later entered in error the patient goes back to "Unknown", never
        # silently to "No known allergies" (Prompt 3).
        patient = serializer.instance.patient
        if patient.allergy_status != "Unknown":
            patient.allergy_status = "Unknown"
            patient.save(update_fields=["allergy_status"])


class ClinicalNoteViewSet(VisitFilterMixin, SignedRecordMixin, HospitalScopedViewSet):
    queryset = ClinicalNote.objects.select_related(
        "visit", "visit__patient", "visit__doctor", "visit__hospital", "doctor"
    ).order_by("-created_at", "-id")
    serializer_class = ClinicalNoteSerializer
    permission_classes = [IsDoctorOnly | IsAdminReadOnly]

    def author_id(self, record):
        return record.doctor.user_id if record.doctor_id else None

    def perform_create(self, serializer):
        # Always in the signed-in doctor's name (decision 2), never a name sent by the client.
        extra = self._check_tenancy(serializer.validated_data)
        check_amends(serializer.validated_data)
        visit = serializer.validated_data["visit"]
        doctor = Doctor.objects.filter(user=self.request.user, hospital_id=visit.hospital_id).first()
        if doctor is None:
            raise PermissionDenied("Only a doctor of this hospital can write a clinical note.")
        instance = serializer.save(doctor=doctor, **extra)
        self._audit("create", instance)


class DiagnosisViewSet(VisitFilterMixin, SignedRecordMixin, HospitalScopedViewSet):
    queryset = Diagnosis.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = DiagnosisSerializer
    permission_classes = [IsDoctorOnly | IsAdminReadOnly | IsHospitalManagerReadOnly]

    def author_id(self, record):
        return record.recorded_by_id

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        check_amends(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user, **extra)
        self._audit("create", instance)


class ServiceOrderViewSet(VisitFilterMixin, HospitalScopedViewSet):
    queryset = ServiceOrder.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsDoctorOnly | IsNurseOnly | IsAdminReadOnly | IsHospitalManagerReadOnly]


class ProcedureViewSet(HospitalScopedViewSet):
    queryset = Procedure.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = ProcedureSerializer
    permission_classes = [IsDoctorOnly | IsAdminReadOnly | IsHospitalManagerReadOnly]


class MedicalRecordViewSet(HospitalScopedViewSet):
    queryset = MedicalRecord.objects.select_related("patient", "visit", "visit__hospital").order_by("-created_at", "-id")
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsDoctorOnly | IsNurseOnly | IsAdminReadOnly | IsHospitalManagerReadOnly]


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


IDEMPOTENCY_KEY_LENGTH = Prescription._meta.get_field("idempotency_key").max_length
KEY_USED_ELSEWHERE = "This Idempotency-Key was already used for a different prescription."


def _text(value):
    return "" if value is None else str(value).strip()


def _quantity(value):
    try:
        return int(value) if value not in (None, "") else 1
    except (TypeError, ValueError):
        return value


def _line(item):
    """One medicine line in the form it is stored (the serializer trims text; quantity defaults to 1)."""
    if not isinstance(item, dict):
        return item
    return (
        _text(item.get("name")), _text(item.get("dosage")), _text(item.get("frequency")),
        _text(item.get("duration")), _quantity(item.get("quantity")), _text(item.get("instructions")),
    )


def _same_prescription(earlier, data):
    """Whether a retried request body asks for what ``earlier`` already holds."""
    if not hasattr(data, "get"):
        return False
    items = data.get("items")
    if not isinstance(items, list):
        return False
    stored = [
        (i.name, i.dosage, i.frequency, i.duration, i.quantity, i.instructions) for i in earlier.items.all()
    ]
    # The doctor is usually left out (the server signs as the requester); when named it must match.
    named_doctor = data.get("doctor")
    return (
        _text(data.get("patient")) == _text(earlier.patient_id)
        and _text(data.get("visit")) == _text(earlier.visit_id)
        and (named_doctor in (None, "") or _text(named_doctor) == _text(earlier.doctor_id))
        and [_line(item) for item in items] == stored
    )


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
    # The pharmacist's write access covers their own paper transcriptions only
    # (perform_create/perform_update below).
    permission_classes = [
        IsDoctorOnly | IsPharmacistOnly | IsAdminReadOnly | IsPatientReadOnly
        | IsReceptionistReadOnly | IsNurseReadOnly | IsCompounderReadOnly
    ]

    def get_permissions(self):
        # Q5 (2026-11-09): transcribing and verifying paper prescriptions is pharmacy work only.
        if getattr(self, "action", None) in ("transcribe", "verify"):
            return [IsPharmacistOnly()]
        return super().get_permissions()

    def _require_writer(self, prescription):
        # The prescriber corrects their prescription; the pharmacy handles its own
        # paper transcriptions (status, cancellation); nobody else changes either.
        user = self.request.user
        if prescription.doctor is not None and prescription.doctor.user_id == user.id:
            return
        if (prescription.source == Prescription.Source.PAPER
                and StaffRole.PHARMACIST in get_user_roles(user, prescription.hospital_id)):
            return
        raise PermissionDenied("Only the prescribing doctor can change this prescription.")

    def create(self, request, *args, **kwargs):
        """
        An optional ``Idempotency-Key`` header makes retries safe: repeating the
        request with the same key returns the prescription it already wrote
        (200) instead of a second one; the same key for different contents,
        or another person's key, is refused (409).
        """
        key = request.headers.get("Idempotency-Key", "").strip()
        if len(key) > IDEMPOTENCY_KEY_LENGTH:
            # Refused, not truncated: two long keys sharing a prefix would collide.
            raise ValidationError({"idempotency_key": f"Use at most {IDEMPOTENCY_KEY_LENGTH} characters."})
        self._idempotency_key = key
        replay = self._replay_prescription(key)
        if replay is not None:
            # Checked before validation so a late retry still gets its prescription
            # back even if, say, a new allergy now raises a safety alert.
            return replay
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError:
            # The same key arrived twice at once: the unique constraint let one
            # through; answer the other with that one instead of a 500.
            replay = self._replay_prescription(key)
            if replay is None:
                raise
            return replay

    def _replay_prescription(self, key):
        """The response for a retried request whose key already wrote a prescription, else None."""
        if not key:
            return None
        candidates = Prescription.objects.filter(
            idempotency_key=key, hospital_id__in=get_user_hospital_ids(self.request.user)
        )
        # The key is unique per hospital: look in the hospital this request writes to
        # (body, else ?hospital= / X-Hospital-ID), as _check_tenancy resolves it.
        data = self.request.data if hasattr(self.request.data, "get") else {}
        target = _text(data.get("hospital")) or _text(get_request_hospital_id(self.request, self))
        if target.isascii() and target.isdecimal():
            candidates = candidates.filter(hospital_id=int(target))
        earlier = candidates.select_related("doctor").order_by("pk").first()
        if earlier is None:
            return None
        mine = earlier.doctor is not None and earlier.doctor.user_id == self.request.user.id
        # Hospital and care scope only, not this view's list filters (?status=, ?visit=).
        earlier = HospitalScopedViewSet.get_queryset(self).filter(pk=earlier.pk).first() if mine else None
        if earlier is None or not _same_prescription(earlier, self.request.data):
            return Response({"error": KEY_USED_ELSEWHERE}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(earlier).data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        hospital = extra.get("hospital", serializer.validated_data.get("hospital"))
        if StaffRole.DOCTOR not in get_user_roles(self.request.user, getattr(hospital, "pk", hospital)):
            raise PermissionDenied("Only a doctor writes prescriptions; the pharmacy uses transcribe for paper ones.")
        instance = serializer.save(**extra, idempotency_key=getattr(self, "_idempotency_key", ""))
        self._audit("create", instance)

    def perform_destroy(self, instance):
        self._require_writer(instance)
        super().perform_destroy(instance)

    def update(self, request, *args, **kwargs):
        # Who may write is settled before the body is validated (403, not a field error).
        self._require_writer(self.get_object())
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        prescription = serializer.instance
        # Every earlier version is kept (PrescriptionRevision).
        self._require_writer(prescription)
        previous = self.get_serializer(prescription).data
        number = prescription.revisions.count() + 1
        super().perform_update(serializer)
        PrescriptionRevision.objects.create(prescription=prescription, number=number, content=previous,
                                            changed_by=self.request.user)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        """Earlier versions of this prescription, oldest first."""
        prescription = self.get_object()
        return Response({"revisions": [
            {"number": r.number, "changed_by": r.changed_by_id, "changed_at": r.changed_at, "content": r.content}
            for r in prescription.revisions.all()
        ]})

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
        """A second pharmacist confirms a transcription matches the paper."""
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
    permission_classes = [IsDoctorOnly | IsAdminReadOnly | IsPharmacistReadOnly | IsNurseReadOnly | IsCompounderReadOnly]
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
    permission_classes = [IsDoctorOnly | IsPatientReadOnly]
    http_method_names = ["get", "post", "head", "options"]


class ReferralViewSet(_SignedByDoctorViewSet):
    queryset = Referral.objects.select_related(
        "patient", "referring_doctor", "referred_to_doctor", "hospital"
    )
    serializer_class = ReferralSerializer
    permission_classes = [IsDoctorOnly | IsPatientReadOnly]
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
    permission_classes = [IsDoctorOnly | IsNurseOnly | IsPatientReadOnly | IsAdminReadOnly]
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
