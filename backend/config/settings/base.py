"""
Django base settings for Hospital Management System.

Shared configuration across all environments.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Load .env file from project root
load_dotenv(PROJECT_ROOT / ".env")


# ============================================================
# Application definition
# ============================================================

INSTALLED_APPS = [
    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # REST API
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",
    # Required by CELERY_BEAT_SCHEDULER (DatabaseScheduler); without it beat cannot start.
    "django_celery_beat",
    "users",

    # Existing hospital apps
    "patients",
    "home",
    "doctors",
    "appointments",
    "nurses",
    "compounder",
    "pharmacy",
    "laboratory",

    # New hospital apps
    "hospital",
    "encounters",
    "clinical",
    "ipd",
    "emergency",
    "billing",
    "bloodbank",
    "notifications",
    "audit",

    # Pharmacy procurement / purchase / GRN
    "procurement",

    # AI Medical Scribe
    "ai_scribe",

    # Analytics & Reports
    "reports",

    # Consent forms and patient-controlled record sharing
    "consent",
]

# ============================================================
# Middleware
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.auth_cookies.AuthCookieMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.correlation.CorrelationIdMiddleware",
    "config.middleware.correlation.LoggingContextMiddleware",
    "config.middleware.ratelimit.RateLimitMiddleware",
]

# Custom middleware will be added in production/development settings
# Health check middleware


# ============================================================
# URL Configuration
# ============================================================

ROOT_URLCONF = 'config.urls'

# Admin URL prefix
ADMIN_URL = 'admin/'


# ============================================================
# Templates
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ============================================================
# WSGI/ASGI Application
# ============================================================

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# ============================================================
# Password Validation
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ============================================================
# Internationalization
# ============================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ============================================================
# Static Files
# ============================================================

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (user uploads)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ============================================================
# Default Auto Field
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# Custom User Model
# ============================================================

# Using Django's default User model (auth.User). StaffProfile extends it via OneToOneField.
# AUTH_USER_MODEL = 'users.User'  # Not using custom user model

# Public Google OAuth client id. The client secret is never sent to the browser.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

# console: log OTP on the server (development)
# cache: keep OTP in cache for tests
# sms: deliver only when Twilio is configured
PATIENT_OTP_DELIVERY = os.environ.get("PATIENT_OTP_DELIVERY", "sms")


# ============================================================
# Django REST Framework
# ============================================================

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Bearer header, or the httpOnly cookie the browser client uses (config/auth_cookies.py).
        'config.auth_cookies.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/minute',
        'otp': '3/minute',
        'password_reset': '2/hour',
        'ai': '30/minute',
        'audio_upload': '10/minute',
        'fhir': '60/minute',
        'hl7': '60/minute',
    },
}

# Reverse proxies in front of Django that append to X-Forwarded-For (nginx in
# production). 0 means "use REMOTE_ADDR": the header is client-controlled, so
# trusting it without a proxy would let anyone pick their rate-limit key.
TRUSTED_PROXY_COUNT = int(os.environ.get('TRUSTED_PROXY_COUNT', '0'))
REST_FRAMEWORK['NUM_PROXIES'] = TRUSTED_PROXY_COUNT

# httpOnly session cookies for the browser client (config/auth_cookies.py).
AUTH_COOKIE_SECURE = False
AUTH_COOKIE_SAMESITE = 'Lax'


# ============================================================
# Simple JWT Configuration
# ============================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',  # Override in production to RS256
    'SIGNING_KEY': None,  # Set in environment-specific settings
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=15),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}


# ============================================================
# CORS Configuration (Base - overridden in env-specific settings)
# ============================================================

CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Override in development

# Headers the frontend sends in addition to django-cors-headers' defaults.
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (*default_headers, "x-hospital-id", "idempotency-key", "x-request-id")


# ============================================================
# Email Configuration (Base - overridden in env-specific settings)
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'Hospital Management System <noreply@hospital.local>'
# Seconds before an unreachable SMTP server fails the send (Django's default waits forever).
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))


# ============================================================
# File Upload Settings
# ============================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644


# ============================================================
# Google Authentication
# ============================================================

GOOGLE_CLIENT_ID = None  # Set in environment-specific settings
ADMIN_INVITE_CODE = os.environ.get("ADMIN_INVITE_CODE", "")

# Temporary shared development sign-in (users/dev_login.py). Works only with
# DEBUG on; production.py switches it off.
DEV_LOGIN_ENABLED = os.environ.get("DEV_LOGIN_ENABLED", "False").lower() == "true"
DEV_LOGIN_MOBILE = os.environ.get("DEV_LOGIN_MOBILE", "")
DEV_LOGIN_EMAIL = os.environ.get("DEV_LOGIN_EMAIL", "")
DEV_LOGIN_PASSWORD = os.environ.get("DEV_LOGIN_PASSWORD", "")


# ============================================================
# Logging Configuration (Base - extended in env-specific settings)
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
        'json': {
            '()': 'config.logging.formatters.JsonFormatter',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}


# ============================================================
# Security Settings (Base - hardened in production)
# ============================================================

# These will be overridden in production settings
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# ============================================================
# Cache Configuration (Base - overridden in env-specific settings)
# ============================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


# ============================================================
# Session Configuration
# ============================================================

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'


# ============================================================
# CSRF Configuration
# ============================================================

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
CSRF_FAILURE_VIEW = 'config.views.csrf.csrf_failure'


# ============================================================
# Hospital Management System Specific Settings
# ============================================================

# Hospital isolation enforcement
ENFORCE_HOSPITAL_ISOLATION = True

# Audit logging
AUDIT_LOG_ENABLED = True
AUDIT_LOG_SENSITIVE_FIELDS = [
    'password', 'secret', 'token', 'key', 'credit_card',
    'ssn', 'medical_record_number', 'diagnosis', 'prescription',
]

# File storage
PATIENT_DOCUMENTS_UPLOAD_PATH = 'patient_documents/'
CONSULTATION_AUDIO_UPLOAD_PATH = 'consultation_audio/'
LAB_REPORTS_UPLOAD_PATH = 'lab_reports/'
PRESCRIPTION_UPLOAD_PATH = 'prescriptions/'
MEDICAL_REPORTS_UPLOAD_PATH = 'medical_reports/'

# AI Medical Scribe
AI_SCRIBE_ENABLED = True
# Mock STT/LLM providers return canned clinical text. Never allow them where
# real patients are documented.
AI_SCRIBE_ALLOW_MOCK_PROVIDERS = False
AI_SCRIBE_PROVIDER = 'openai'  # openai, anthropic, local
AI_SCRIBE_MODEL = 'gpt-4'
AI_SCRIBE_MAX_TOKENS = 4000
AI_SCRIBE_TEMPERATURE = 0.1

# FHIR Configuration
FHIR_ENABLED = True
FHIR_BASE_URL = None  # Set in environment-specific settings
FHIR_VERSION = 'R4'

# HL7 Configuration
HL7_ENABLED = True
HL7_LISTEN_PORT = 2575
HL7_MSH_SENDING_APPLICATION = 'HMS'
HL7_MSH_SENDING_FACILITY = 'HOSPITAL'
# HL7 Security - IP whitelist and API key for endpoint authentication
HL7_IP_WHITELIST = []  # List of allowed IPs for HL7 endpoints
HL7_API_KEY = None  # API key for HL7 endpoints (set in production)

# ABDM/ABHA Configuration
ABDM_ENABLED = True
ABDM_BASE_URL = None
ABDM_CLIENT_ID = None
ABDM_CLIENT_SECRET = None

# Notifications
NOTIFICATION_CHANNELS = ['email', 'sms', 'whatsapp', 'push', 'in_app']
SMS_PROVIDER = 'twilio'
WHATSAPP_PROVIDER = 'twilio'

# Twilio Verify v2 (for OTP authentication)
TWILIO_ACCOUNT_SID = None
TWILIO_API_KEY = None
TWILIO_API_SECRET = None
TWILIO_VERIFY_SERVICE_SID = None
# Legacy Twilio SMS (fallback)
TWILIO_AUTH_TOKEN = None
TWILIO_PHONE_NUMBER = None

# OTP Provider selection: 'twilio' (Verify v2) or 'console' (dev) or 'cache' (test)
OTP_PROVIDER = 'twilio'

# Rate Limiting (complements DRF throttling)
RATE_LIMIT_ENABLED = True

# Health Checks
HEALTH_CHECK_ENABLED = True

# Monitoring
MONITORING_ENABLED = False  # Enable in production with credentials

# Backup
BACKUP_ENABLED = False  # Enable in production


# ============================================================
# Celery Configuration (Base - overridden in env-specific settings)
# ============================================================

CELERY_BROKER_URL = None  # Set in environment-specific settings
CELERY_RESULT_BACKEND = None
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery task routes for priority queues
CELERY_TASK_ROUTES = {
    'notifications.tasks.send_*': {'queue': 'notifications'},
    'reports.tasks.generate_*': {'queue': 'reports'},
    'ai_scribe.tasks.*': {'queue': 'ai_processing'},
    'audit.tasks.*': {'queue': 'audit'},
    'backup.tasks.*': {'queue': 'maintenance'},
}

# When True, staff password sign-in never issues tokens: the SMS OTP step is mandatory.
STAFF_LOGIN_REQUIRE_OTP = os.environ.get('STAFF_LOGIN_REQUIRE_OTP', 'False').lower() == 'true'

# Audit rows older than this are purged daily; 0 keeps them forever.
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', '0'))

# Celery beat schedule for periodic tasks
# Only tasks that exist in the codebase are scheduled. Daily report generation
# and backup verification are run by the ops scripts in docs/OPERATIONS_RUNBOOK.md.
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-otp': {
        'task': 'notifications.tasks.cleanup_expired_otp',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-audit-logs': {
        'task': 'audit.tasks.cleanup_old_audit_logs',
        'schedule': 86400.0,  # Daily
    },
}


# ============================================================
# Django Health Check
# ============================================================

HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percent
    'MEMORY_MIN': 100,  # MB
}


# ============================================================
# API Documentation (DRF Spectacular)
# ============================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'Hospital Management System API',
    'DESCRIPTION': 'Comprehensive API for Hospital Management System including patient management, clinical workflows, pharmacy, laboratory, billing, and interoperability.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'TAGS': [
        {'name': 'Authentication', 'description': 'Staff authentication, JWT tokens, Google OAuth'},
        {'name': 'Hospitals', 'description': 'Hospital and department management'},
        {'name': 'Patients', 'description': 'Patient registration, documents, hospital memberships'},
        {'name': 'Doctors', 'description': 'Doctor management, schedules, availability'},
        {'name': 'Appointments', 'description': 'Appointment scheduling and management'},
        {'name': 'Encounters', 'description': 'Visits, queue management, doctor schedules'},
        {'name': 'Clinical', 'description': 'Vitals, clinical notes, diagnoses, prescriptions, service orders'},
        {'name': 'IPD', 'description': 'Admissions, bed management, discharge planning'},
        {'name': 'Emergency', 'description': 'Emergency visits, triage, orders, medications'},
        {'name': 'Laboratory', 'description': 'Lab tests, sample collection, results, verification'},
        {'name': 'Pharmacy', 'description': 'Medicine inventory, sales, procurement'},
        {'name': 'Blood Bank', 'description': 'Blood inventory, requests, transactions'},
        {'name': 'Billing', 'description': 'Invoices, payments, insurance claims'},
        {'name': 'Nurses', 'description': 'Nurse management, assessments, care tasks, MAR'},
        {'name': 'Notifications', 'description': 'Patient notifications, consent, OTP'},
        {'name': 'Audit', 'description': 'Audit logs, AI interactions'},
        {'name': 'Reports', 'description': 'Patient summary, financial, clinical, operational reports'},
        {'name': 'Documents', 'description': 'Document management and upload'},
        {'name': 'Consent', 'description': 'Consent forms and records'},
        {'name': 'AI Scribe', 'description': 'AI medical scribe - consultation recording, transcription, clinical drafts'},
        {'name': 'FHIR', 'description': 'FHIR R4 interoperability endpoints'},
        {'name': 'HL7', 'description': 'HL7 v2 messaging endpoints'},
        {'name': 'ABDM', 'description': 'ABDM/ABHA integration endpoints'},
    ],
    'SECURITY': [
        {'Bearer': []},
    ],
}