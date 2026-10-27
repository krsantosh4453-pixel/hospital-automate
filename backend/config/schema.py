"""
OpenAPI/Swagger Schema Configuration for Hospital Management System API.

Uses drf-spectacular for automatic schema generation.
"""

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


# ============================================================
# Schema Views
# ============================================================

class SchemaAPIView(SpectacularAPIView):
    """OpenAPI schema endpoint."""

    permission_classes = [AllowAny]  # Public schema for documentation

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SwaggerUIView(SpectacularSwaggerView):
    """Swagger UI for API documentation."""

    permission_classes = [AllowAny]
    template_name = 'drf_spectacular/swagger_ui.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Hospital Management System API',
            'version': '1.0.0',
        })
        return context


class RedocView(SpectacularRedocView):
    """ReDoc for API documentation."""

    permission_classes = [AllowAny]
    template_name = 'drf_spectacular/redoc.html'


# ============================================================
# Custom Schema Extensions
# ============================================================

# Common parameters for hospital-scoped endpoints
HOSPITAL_PARAMETER = OpenApiParameter(
    name='hospital',
    description='Hospital ID to scope the request',
    required=True,
    type=str,
    location=OpenApiParameter.QUERY,
)

PATIENT_PARAMETER = OpenApiParameter(
    name='patient',
    description='Patient ID to filter results',
    required=False,
    type=str,
    location=OpenApiParameter.QUERY,
)

VISIT_PARAMETER = OpenApiParameter(
    name='visit',
    description='Visit/Encounter ID to filter results',
    required=False,
    type=str,
    location=OpenApiParameter.QUERY,
)

DATE_FROM_PARAMETER = OpenApiParameter(
    name='date_from',
    description='Start date for filtering (YYYY-MM-DD)',
    required=False,
    type=str,
    location=OpenApiParameter.QUERY,
)

DATE_TO_PARAMETER = OpenApiParameter(
    name='date_to',
    description='End date for filtering (YYYY-MM-DD)',
    required=False,
    type=str,
    location=OpenApiParameter.QUERY,
)

# Common error responses
ERROR_RESPONSES = {
    400: {'description': 'Bad Request - Invalid input'},
    401: {'description': 'Unauthorized - Authentication required'},
    403: {'description': 'Forbidden - Insufficient permissions'},
    404: {'description': 'Not Found - Resource does not exist'},
    429: {'description': 'Too Many Requests - Rate limited'},
    500: {'description': 'Internal Server Error'},
}

# Common examples
PATIENT_EXAMPLE = OpenApiExample(
    'Patient Example',
    value={
        'id': '123e4567-e89b-12d3-a456-426614174000',
        'name': 'John Doe',
        'age': 35,
        'gender': 'Male',
        'phone': '+1234567890',
        'condition': 'Hypertension',
        'status': 'Active',
        'hospital': '123e4567-e89b-12d3-a456-426614174001',
        'created_at': '2024-01-15T10:30:00Z',
    },
    response_only=True,
)

APPOINTMENT_EXAMPLE = OpenApiExample(
    'Appointment Example',
    value={
        'id': '123e4567-e89b-12d3-a456-426614174002',
        'patient': '123e4567-e89b-12d3-a456-426614174000',
        'doctor': '123e4567-e89b-12d3-a456-426614174003',
        'hospital': '123e4567-e89b-12d3-a456-426614174001',
        'appointment_date': '2024-01-20T10:00:00Z',
        'status': 'Scheduled',
        'reason': 'Regular checkup',
        'created_at': '2024-01-15T10:30:00Z',
    },
    response_only=True,
)


# ============================================================
# Schema Tags and Organization
# ============================================================

SCHEMA_TAGS = [
    {
        'name': 'Authentication',
        'description': 'Staff authentication, JWT tokens, Google OAuth, password reset',
    },
    {
        'name': 'Hospitals',
        'description': 'Hospital, department, ward, room, and bed management',
    },
    {
        'name': 'Patients',
        'description': 'Patient registration, documents, hospital memberships, medical records',
    },
    {
        'name': 'Doctors',
        'description': 'Doctor management, schedules, availability, specializations',
    },
    {
        'name': 'Appointments',
        'description': 'Appointment scheduling, rescheduling, cancellation, reminders',
    },
    {
        'name': 'Encounters',
        'description': 'Patient visits, queue management, doctor schedules, tokens',
    },
    {
        'name': 'Clinical',
        'description': 'Vitals, clinical notes, diagnoses, prescriptions, service orders, procedures',
    },
    {
        'name': 'IPD',
        'description': 'Admissions, bed allocation, discharge planning, discharge summaries',
    },
    {
        'name': 'Emergency',
        'description': 'Emergency visits, triage, orders, medications, disposition',
    },
    {
        'name': 'Laboratory',
        'description': 'Lab tests, sample collection/dispatch, results, verification',
    },
    {
        'name': 'Pharmacy',
        'description': 'Medicine inventory, sales, prescriptions, stock management',
    },
    {
        'name': 'Blood Bank',
        'description': 'Blood inventory, requests, transactions, component management',
    },
    {
        'name': 'Billing',
        'description': 'Invoices, payments, insurance claims, financial reports',
    },
    {
        'name': 'Nurses',
        'description': 'Nurse management, assessments, care tasks, MAR, patient assignments',
    },
    {
        'name': 'Notifications',
        'description': 'Patient notifications, consent management, OTP verification',
    },
    {
        'name': 'Audit',
        'description': 'Audit logs, AI interaction tracking',
    },
    {
        'name': 'Reports',
        'description': 'Patient summary, financial, clinical, operational reports',
    },
    {
        'name': 'Documents',
        'description': 'Document management, upload, download, access control',
    },
    {
        'name': 'Consent',
        'description': 'Consent forms, records, digital signatures',
    },
    {
        'name': 'AI Scribe',
        'description': 'AI medical scribe - consultation recording, transcription, clinical drafts, doctor review',
    },
    {
        'name': 'FHIR',
        'description': 'FHIR R4 interoperability endpoints for patient, observation, encounter resources',
    },
    {
        'name': 'HL7',
        'description': 'HL7 v2 messaging endpoints for ADT, ORM, ORU messages',
    },
    {
        'name': 'ABDM',
        'description': 'ABDM/ABHA integration endpoints for health ID, consent, records',
    },
]


# ============================================================
# Authentication Schemes
# ============================================================

SECURITY_SCHEMES = {
    'Bearer': {
        'type': 'http',
        'scheme': 'bearer',
        'bearerFormat': 'JWT',
        'description': 'JWT access token obtained from /api/auth/token/',
    },
}


# ============================================================
# Custom Schema Generator Settings
# ============================================================

def custom_preprocessing_hook(endpoints):
    """Custom preprocessing for schema generation."""
    # Filter out internal endpoints
    filtered = []
    for path, path_regex, method, callback in endpoints:
        # Skip admin endpoints
        if path.startswith('/admin/'):
            continue
        # Skip health check from main schema
        if path.startswith('/health/'):
            continue
        filtered.append((path, path_regex, method, callback))
    return filtered


def custom_postprocessing_hook(result, generator, request, public):
    """Custom postprocessing for schema generation."""
    # Add security schemes
    if 'components' not in result:
        result['components'] = {}
    result['components']['securitySchemes'] = SECURITY_SCHEMES

    # Add global security requirement
    result['security'] = [{'Bearer': []}]

    # Add tags
    result['tags'] = SCHEMA_TAGS

    return result