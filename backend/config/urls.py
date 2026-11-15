"""
URL configuration for Hospital Management System.

Includes API endpoints, admin, health checks, and API documentation.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Import existing viewsets
from patients.views import PatientViewSet, PatientHospitalViewSet
from doctors.views import DoctorViewSet
from appointments.views import AppointmentViewSet
from compounder.views import CompounderViewSet
from pharmacy.views import MedicineViewSet, SaleViewSet
from laboratory.views import LabTestViewSet

# Import schema views
from config.schema import SchemaAPIView, SwaggerUIView, RedocView

# Import health check views
from config.health import HealthCheckView


# =========================
# API ROUTER
# =========================

router = DefaultRouter()

# Core APIs
router.register("patients", PatientViewSet, basename="patients")
router.register(
    "patient-hospitals",
    PatientHospitalViewSet,
    basename="patient-hospital"
)
router.register("doctors", DoctorViewSet, basename="doctors")
router.register("appointments", AppointmentViewSet, basename="appointments")
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

# Every API route, mounted twice below: at /api/v1/ (the versioned contract the
# mobile app uses and the schema documents) and at /api/ (the web app's
# original prefix, kept until it moves). Both run the same views.
api_patterns = [
    # Authentication
    path("auth/", include("users.urls")),

    # Hospital staff administration
    path("users/", include("users.staff_urls")),

    # Laboratory sub-resources (must precede the root router; see laboratory/urls.py)
    path("laboratory/", include("laboratory.urls")),

    # Core APIs
    path("", include(router.urls)),

    # Home Dashboard API
    path("home/", include("home.urls")),

    # Nursing APIs (includes all nurse-related endpoints: nurses, assessments, notes, care-tasks, mar, etc.)
    path("nurses/", include("nurses.urls")),

    # Hospital Management APIs
    path("hospital/", include("hospital.urls")),
    path("encounters/", include("encounters.urls")),
    path("clinical/", include("clinical.urls")),
    path("ipd/", include("ipd.urls")),
    path("emergency/", include("emergency.urls")),
    path("billing/", include("billing.urls")),
    path("bloodbank/", include("bloodbank.urls")),
    path("notifications/", include("notifications.urls")),
    path("audit/", include("audit.urls")),

    # Pharmacy Procurement
    path("procurement/", include("procurement.urls")),

    # AI Medical Scribe
    # AI discharge summary assist (before the scribe's catch-all ai/ routes)
    path("ai/discharge/", include("ai_advanced.urls")),

    path("ai/", include("ai_scribe.urls")),

    # Reports
    path("reports/", include("reports.urls")),

    # FHIR R4 read API (Admin only, off unless FHIR_ENABLED)
    path("fhir/", include("fhir.urls")),

    # ABDM/ABHA: verify and link an existing ABHA (off unless ABDM_ENABLED)
    path("abdm/", include("abdm.urls")),

    # Documents
    path("documents/", include("documents.urls")),

    # Consent
    path("consent/", include("consent.urls")),

    # Clinical terminology (ICD-10 search)
    path("terminology/", include("terminology.urls")),

    # Support services: OT, ambulance, mortuary, CSSD, laundry, leave, feedback, templates
    path("services/", include("hospital_services.urls")),
]

urlpatterns = [
    # Health Checks (no auth required)
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("health/live/", HealthCheckView.as_view(), name="health-live"),
    path("health/ready/", HealthCheckView.as_view(), name="health-ready"),

    # API Documentation
    path("api/schema/", SchemaAPIView.as_view(), name="schema"),
    path("api/docs/", SwaggerUIView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", RedocView.as_view(url_name="schema"), name="redoc"),

    # Django Admin
    path(settings.ADMIN_URL, admin.site.urls),

    # Versioned first: no /api/ route starts with "v1/", but keep the order explicit.
    # The "v1" namespace keeps app namespaces (abdm, consent, ...) unique; plain
    # reverse() names keep resolving to /api/, and "v1:<name>" to /api/v1/.
    path("api/v1/", include((api_patterns, "v1"))),
    path("api/", include(api_patterns)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Debug toolbar
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns