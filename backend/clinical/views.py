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


class VitalSignViewSet(viewsets.ModelViewSet):
    queryset = VitalSign.objects.all()
    serializer_class = VitalSignSerializer


class AllergyViewSet(viewsets.ModelViewSet):
    queryset = Allergy.objects.all()
    serializer_class = AllergySerializer


class ClinicalNoteViewSet(viewsets.ModelViewSet):
    queryset = ClinicalNote.objects.all()
    serializer_class = ClinicalNoteSerializer


class DiagnosisViewSet(viewsets.ModelViewSet):
    queryset = Diagnosis.objects.all()
    serializer_class = DiagnosisSerializer


class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.all()
    serializer_class = ServiceOrderSerializer


class ProcedureViewSet(viewsets.ModelViewSet):
    queryset = Procedure.objects.all()
    serializer_class = ProcedureSerializer


class MedicalRecordViewSet(viewsets.ModelViewSet):
    queryset = MedicalRecord.objects.all()
    serializer_class = MedicalRecordSerializer


class PrescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PrescriptionSerializer

    def get_queryset(self):
        queryset = Prescription.objects.select_related(
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


class PrescriptionItemViewSet(viewsets.ModelViewSet):
    serializer_class = PrescriptionItemSerializer

    def get_queryset(self):
        queryset = PrescriptionItem.objects.select_related("prescription")

        prescription_id = self.request.query_params.get("prescription")
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)

        return queryset