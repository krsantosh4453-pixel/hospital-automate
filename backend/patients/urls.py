from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PatientViewSet, PatientHospitalViewSet


router = DefaultRouter()

# Existing Patient API
router.register(
    r"patients",
    PatientViewSet,
    basename="patient"
)

# New Patient-Hospital API
router.register(
    r"patient-hospitals",
    PatientHospitalViewSet,
    basename="patient-hospital"
)


urlpatterns = [
    path("", include(router.urls)),
]
