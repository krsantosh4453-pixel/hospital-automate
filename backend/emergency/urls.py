from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EmergencyVisitViewSet,
    EmergencyTriageViewSet,
    EmergencyVitalsViewSet,
    EmergencyOrderViewSet,
    EmergencyMedicationViewSet,
)

router = DefaultRouter()

router.register(
    r"emergency-visits",
    EmergencyVisitViewSet,
    basename="emergency-visit"
)
router.register(
    r"triage",
    EmergencyTriageViewSet,
    basename="emergency-triage"
)
router.register(
    r"vitals",
    EmergencyVitalsViewSet,
    basename="emergency-vitals"
)
router.register(
    r"orders",
    EmergencyOrderViewSet,
    basename="emergency-order"
)
router.register(
    r"medications",
    EmergencyMedicationViewSet,
    basename="emergency-medication"
)

urlpatterns = [
    path("", include(router.urls)),
]