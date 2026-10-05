"""
Django development settings for Hospital Management System.

Extends base settings with development-specific configuration.
"""

from .base import *  # noqa: F403,F401
import os


# ============================================================
# Security - Development
# ============================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# Same public client id already used by the login page. Override with env in real deployments.
GOOGLE_CLIENT_ID = os.environ.get(
    'GOOGLE_CLIENT_ID',
    '1199500530711-s1ti1g061cno8d3tk2759hqrgitdect.apps.googleusercontent.com',
)
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

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True


# ============================================================
# Email - Console Backend for Development
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


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

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '1199500530711-s1ti1g061cno8d3tk2759hqrgitdect.apps.googleusercontent.com')
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
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

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