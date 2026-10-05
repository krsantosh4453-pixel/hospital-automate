from rest_framework import viewsets

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
)
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsDoctor, IsNurse, IsPharmacist, IsPatientReadOnly


class VitalSignViewSet(HospitalScopedViewSet):
    queryset = VitalSign.objects.all()
    serializer_class = VitalSignSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class AllergyViewSet(HospitalScopedViewSet):
    queryset = Allergy.objects.all()
    serializer_class = AllergySerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class ClinicalNoteViewSet(HospitalScopedViewSet):
    queryset = ClinicalNote.objects.all()
    serializer_class = ClinicalNoteSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]


class DiagnosisViewSet(HospitalScopedViewSet):
    queryset = Diagnosis.objects.all()
    serializer_class = DiagnosisSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]


class ServiceOrderViewSet(HospitalScopedViewSet):
    queryset = ServiceOrder.objects.all()
    serializer_class = ServiceOrderSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class ProcedureViewSet(HospitalScopedViewSet):
    queryset = Procedure.objects.all()
    serializer_class = ProcedureSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]


class MedicalRecordViewSet(HospitalScopedViewSet):
    queryset = MedicalRecord.objects.all()
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse]


class PrescriptionViewSet(HospitalScopedViewSet):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsPharmacist | IsPatientReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.select_related(
            "patient", "doctor", "hospital", "visit"
        ).prefetch_related("items")

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        visit_id = self.request.query_params.get("visit")
        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)

        return queryset


class PrescriptionItemViewSet(HospitalScopedViewSet):
    queryset = PrescriptionItem.objects.all()
    serializer_class = PrescriptionItemSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsPharmacist]

    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.select_related("prescription")

        prescription_id = self.request.query_params.get("prescription")
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)

        return queryset