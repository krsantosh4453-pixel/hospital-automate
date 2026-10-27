"""
Django development settings for Hospital Management System.

Extends base settings with development-specific configuration.
"""

from .base import *  # noqa: F403,F401
import os
from django.core.exceptions import ImproperlyConfigured


# ============================================================
# Security - Development
# ============================================================

# SECURITY WARNING: keep the secret key used in production secret!
# Must be set via DJANGO_SECRET_KEY environment variable
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY environment variable is required')

# Google OAuth - Must be set via GOOGLE_CLIENT_ID environment variable
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
if not GOOGLE_CLIENT_ID:
    raise ImproperlyConfigured('GOOGLE_CLIENT_ID environment variable is required')

# console: log the SMS code on the server. Set PATIENT_OTP_DELIVERY=sms with Twilio
# credentials when a real text message should be sent.
PATIENT_OTP_DELIVERY = os.environ.get('PATIENT_OTP_DELIVERY', 'console')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '[::1]', 'testserver']


# ============================================================
# Database - SQLite for Development
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ============================================================
# CORS - Development
# ============================================================

# Even in development, restrict to known origins for security
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
]
# Vite moves to 5174, 5175, ... when 5173 is taken; accept any port, loopback hosts only.
# The Vite proxy rewrites Host to the backend, so cookie-authenticated writes
# need the dev-server origins trusted for CSRF (ports cannot be wildcarded).
CSRF_TRUSTED_ORIGINS = [
    f'http://{host}:{port}'
    for host in ('localhost', '127.0.0.1')
    for port in [3000, *range(5173, 5200)]
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^http://(localhost|127\.0\.0\.1|\[::1\]):\d+$',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False


# ============================================================
# Email - Console unless SMTP credentials are configured
# ============================================================

# With EMAIL_HOST_USER and EMAIL_HOST_PASSWORD set, OTP emails are really sent
# over SMTP; otherwise they are only printed to the runserver console.
# EMAIL_BACKEND overrides the choice explicitly.
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL') or EMAIL_HOST_USER or DEFAULT_FROM_EMAIL  # noqa: F405
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND') or (
    'django.core.mail.backends.smtp.EmailBackend'
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
    else 'django.core.mail.backends.console.EmailBackend'
)


# ============================================================
# Static Files - Development
# ============================================================

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]


# ============================================================
# JWT - Development (uses SECRET_KEY from base)
# ============================================================

SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY


# ============================================================
# Google Auth - Development
# ============================================================

ADMIN_INVITE_CODE = os.environ.get("ADMIN_INVITE_CODE", "")


# ============================================================
# Logging - Development (Verbose)
# ============================================================

LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}


# ============================================================
# Cache - Local Memory for Development
# ============================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


# ============================================================
# Celery - Development (Eager mode for synchronous execution)
# ============================================================

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'True').lower() == 'true'
CELERY_TASK_EAGER_PROPAGATES = True


# ============================================================
# Redis - Development
# ============================================================

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


# ============================================================
# AI Scribe - Development
# ============================================================

AI_SCRIBE_ENABLED = True
AI_SCRIBE_ALLOW_MOCK_PROVIDERS = os.environ.get('AI_SCRIBE_ALLOW_MOCK_PROVIDERS', 'True').lower() == 'true'
AI_SCRIBE_PROVIDER = os.environ.get('AI_SCRIBE_PROVIDER', 'openai')
AI_SCRIBE_API_KEY = os.environ.get('AI_SCRIBE_API_KEY', '')


# ============================================================
# FHIR - Development
# ============================================================

FHIR_ENABLED = True
FHIR_BASE_URL = os.environ.get('FHIR_BASE_URL', 'http://localhost:8000/api/fhir/')


# ============================================================
# HL7 - Development
# ============================================================

HL7_ENABLED = True
HL7_LISTEN_PORT = int(os.environ.get('HL7_LISTEN_PORT', '2575'))


# ============================================================
# ABDM - Development
# ============================================================

ABDM_ENABLED = True
ABDM_BASE_URL = os.environ.get('ABDM_BASE_URL', 'https://dev.abdm.gov.in')
ABDM_CLIENT_ID = os.environ.get('ABDM_CLIENT_ID', '')
ABDM_CLIENT_SECRET = os.environ.get('ABDM_CLIENT_SECRET', '')


# ============================================================
# Notifications - Development
# ============================================================

SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'twilio')

# Twilio Verify v2
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_API_KEY = os.environ.get('TWILIO_API_KEY', '')
TWILIO_API_SECRET = os.environ.get('TWILIO_API_SECRET', '')
TWILIO_VERIFY_SERVICE_SID = os.environ.get('TWILIO_VERIFY_SERVICE_SID', '')

# Legacy Twilio SMS (fallback)
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# OTP Provider: 'twilio' (Verify v2), 'console' (dev), 'cache' (test)
OTP_PROVIDER = os.environ.get('OTP_PROVIDER', 'console')

WHATSAPP_PROVIDER = os.environ.get('WHATSAPP_PROVIDER', 'twilio')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')


# ============================================================
# Monitoring - Disabled in Development
# ============================================================

MONITORING_ENABLED = False


# ============================================================
# Debug Toolbar (if installed)
# ============================================================

if os.environ.get('DEBUG_TOOLBAR', 'False').lower() == 'true':
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1', 'localhost']


# ============================================================
# Django Extensions (if installed)
# ============================================================

if os.environ.get('DJANGO_EXTENSIONS', 'False').lower() == 'true':
    INSTALLED_APPS += ['django_extensions']


# ============================================================
# Test Settings Override
# ============================================================

if 'test' in os.environ.get('DJANGO_SETTINGS_MODULE', ''):
    # Speed up tests
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
# Local development reloads the login pages and dashboards many times an hour
# from one address (localhost); the base 100/hour anonymous limit then hides
# the sign-in forms. Raise only the general limits here. Sign-in, OTP and
# password-reset limits stay as in base; production sets its own rates.
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # noqa: F405
    **REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'],  # noqa: F405
    'anon': '2000/hour',
    'user': '10000/hour',
}
