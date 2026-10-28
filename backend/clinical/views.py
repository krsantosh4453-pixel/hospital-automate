from rest_framework.exceptions import ValidationError

from doctors.models import Doctor
from .models import (
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
    VitalSignSerializer,
    AllergySerializer,
    ClinicalNoteSerializer,
    DiagnosisSerializer,
    ServiceOrderSerializer,
    ProcedureSerializer,
    MedicalRecordSerializer,
    PrescriptionSerializer,
    PrescriptionItemSerializer,
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
    IsPatientReadOnly,
    IsReceptionistReadOnly,
)


class VitalSignViewSet(HospitalScopedViewSet):
    queryset = VitalSign.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital")
    serializer_class = VitalSignSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class AllergyViewSet(HospitalScopedViewSet):
    queryset = Allergy.objects.select_related("patient")
    serializer_class = AllergySerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class ClinicalNoteViewSet(HospitalScopedViewSet):
    queryset = ClinicalNote.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital", "doctor")
    serializer_class = ClinicalNoteSerializer
    permission_classes = [IsAdmin | IsDoctor]


class DiagnosisViewSet(HospitalScopedViewSet):
    queryset = Diagnosis.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital")
    serializer_class = DiagnosisSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user, **extra)
        self._audit("create", instance)


class ServiceOrderViewSet(HospitalScopedViewSet):
    queryset = ServiceOrder.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital")
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class ProcedureViewSet(HospitalScopedViewSet):
    queryset = Procedure.objects.select_related("visit", "visit__patient", "visit__doctor", "visit__hospital")
    serializer_class = ProcedureSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]


class MedicalRecordViewSet(HospitalScopedViewSet):
    queryset = MedicalRecord.objects.select_related("patient", "visit", "visit__hospital")
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class PrescriptionViewSet(HospitalScopedViewSet):
    queryset = Prescription.objects.select_related(
        "patient", "doctor", "hospital", "visit"
    ).prefetch_related("items")
    serializer_class = PrescriptionSerializer
    # Clinical records: not for the Hospital Manager. Nurses (MAR), the
    # compounder (dispensing) and the front desk (reports) only read them.
    permission_classes = [
        IsAdmin | IsDoctor | IsPharmacist | IsPatientReadOnly
        | IsReceptionistReadOnly | IsNurseReadOnly | IsCompounderReadOnly
    ]

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

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset


class PrescriptionItemViewSet(HospitalScopedViewSet):
    queryset = PrescriptionItem.objects.select_related("prescription")
    serializer_class = PrescriptionItemSerializer
    permission_classes = [IsAdmin | IsDoctor | IsPharmacist | IsNurseReadOnly | IsCompounderReadOnly]

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
