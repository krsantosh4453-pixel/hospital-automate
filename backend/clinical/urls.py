from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    VitalSignViewSet,
    AllergyViewSet,
    ClinicalNoteViewSet,
    DiagnosisViewSet,
    ServiceOrderViewSet,
    ProcedureViewSet,
    MedicalRecordViewSet,
    PrescriptionViewSet,
    PrescriptionItemViewSet,
    MedicalCertificateViewSet,
    ReferralViewSet,
    ImmunizationViewSet,
)

router = DefaultRouter()

router.register(r"vitals", VitalSignViewSet, basename="vital")
router.register(r"allergies", AllergyViewSet, basename="allergy")
router.register(r"clinical-notes", ClinicalNoteViewSet, basename="clinical-note")
router.register(r"diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register(r"service-orders", ServiceOrderViewSet, basename="service-order")
router.register(r"procedures", ProcedureViewSet, basename="procedure")
router.register(r"medical-records", MedicalRecordViewSet, basename="medical-record")
router.register(r"prescriptions", PrescriptionViewSet, basename="prescription")
router.register(r"prescription-items", PrescriptionItemViewSet, basename="prescription-item")
router.register(r"certificates", MedicalCertificateViewSet, basename="medical-certificate")
router.register(r"referrals", ReferralViewSet, basename="referral")
router.register(r"immunizations", ImmunizationViewSet, basename="immunization")

urlpatterns = [
    path("", include(router.urls)),
]