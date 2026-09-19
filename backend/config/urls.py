"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# =========================
# OLD APP VIEWS
# =========================

from patients.views import PatientViewSet, PatientHospitalViewSet
from doctors.views import DoctorViewSet
from appointments.views import AppointmentViewSet
from nurses.views import NurseViewSet
from compounder.views import CompounderViewSet
from pharmacy.views import MedicineViewSet, SaleViewSet
from laboratory.views import LabTestViewSet


# =========================
# API ROUTER
# =========================

router = DefaultRouter()

# Old APIs
router.register("patients", PatientViewSet, basename="patients")
router.register(
    "patient-hospitals",
    PatientHospitalViewSet,
    basename="patient-hospital"
)
router.register("doctors", DoctorViewSet, basename="doctors")
router.register("appointments", AppointmentViewSet, basename="appointments")
router.register("nurses", NurseViewSet, basename="nurses")
router.register("compounder", CompounderViewSet, basename="compounder")
router.register("pharmacy", MedicineViewSet, basename="pharmacy")
router.register(
    "pharmacy-sales",
    SaleViewSet,
    basename="pharmacy-sale"
)
router.register("laboratory", LabTestViewSet, basename="laboratory")


# =========================
# URL PATTERNS
# =========================

urlpatterns = [
    path("api/auth/", include("users.urls")),
    # Django Admin
    path("admin/", admin.site.urls),

    # Old APIs + Patient-Hospital API
    path("api/", include(router.urls)),

    # Home Dashboard API
    path("api/home/", include("home.urls")),

    # New APIs
    path("api/hospital/", include("hospital.urls")),
    path("api/encounters/", include("encounters.urls")),
    path("api/clinical/", include("clinical.urls")),
    path("api/ipd/", include("ipd.urls")),
    path("api/emergency/", include("emergency.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/bloodbank/", include("bloodbank.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/audit/", include("audit.urls")),

    # Pharmacy procurement / purchase / GRN
    path("api/procurement/", include("procurement.urls")),
]