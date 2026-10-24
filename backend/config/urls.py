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

urlpatterns = [
    # Health Checks (no auth required)
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("health/live/", HealthCheckView.as_view(), name="health-live"),
    path("health/ready/", HealthCheckView.as_view(), name="health-ready"),

    # API Documentation
    path("api/schema/", SchemaAPIView.as_view(), name="schema"),
    path("api/docs/", SwaggerUIView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", RedocView.as_view(url_name="schema"), name="redoc"),

    # Authentication
    path("api/auth/", include("users.urls")),

    # Hospital staff administration
    path("api/users/", include("users.staff_urls")),

    # Django Admin
    path(settings.ADMIN_URL, admin.site.urls),

    # Laboratory sub-resources (must precede the root router; see laboratory/urls.py)
    path("api/laboratory/", include("laboratory.urls")),

    # Core APIs
    path("api/", include(router.urls)),

    # Home Dashboard API
    path("api/home/", include("home.urls")),

    # Nursing APIs (includes all nurse-related endpoints: nurses, assessments, notes, care-tasks, mar, etc.)
    path("api/nurses/", include("nurses.urls")),


    # Hospital Management APIs
    path("api/hospital/", include("hospital.urls")),
    path("api/encounters/", include("encounters.urls")),
    path("api/clinical/", include("clinical.urls")),
    path("api/ipd/", include("ipd.urls")),
    path("api/emergency/", include("emergency.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/bloodbank/", include("bloodbank.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/audit/", include("audit.urls")),

    # Pharmacy Procurement
    path("api/procurement/", include("procurement.urls")),

    # AI Medical Scribe
    path("api/ai/", include("ai_scribe.urls")),

    # Reports
    path("api/reports/", include("reports.urls")),

    # FHIR Interoperability (not implemented)
    # path("api/fhir/", include("fhir.urls")),

    # HL7 Messaging (not implemented)
    # path("api/hl7/", include("hl7.urls")),

    # ABDM/ABHA Integration (not implemented)
    # path("api/abdm/", include("abdm.urls")),

    # Reports (not implemented)
    # path("api/reports/", include("reports.urls")),

    # Documents
    path("api/documents/", include("documents.urls")),

    # Consent
    path("api/consent/", include("consent.urls")),

# Monitoring (if enabled)
    # path("metrics/", include("config.monitoring.metrics_view")),
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