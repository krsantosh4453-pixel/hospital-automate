"""
Django testing settings for Hospital Management System.

Optimized for fast test execution with in-memory databases.
"""

from .base import *  # noqa: F403,F401
import os
from datetime import timedelta


# ============================================================
# Security - Testing
# ============================================================

SECRET_KEY = 'django-insecure-test-key-for-testing-only'
GOOGLE_CLIENT_ID = 'test-google-client'
PATIENT_OTP_DELIVERY = 'cache'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']


# ============================================================
# Database - In-Memory SQLite for Fast Tests
# ============================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


# ============================================================
# CORS - Testing
# ============================================================

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True


# ============================================================
# Email - Locmem for Testing
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


# ============================================================
# Static/Media - Testing
# ============================================================

STATIC_ROOT = BASE_DIR / 'test_staticfiles'
MEDIA_ROOT = BASE_DIR / 'test_media'

# Use default storage for tests
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# ============================================================
# JWT - Testing
# ============================================================

SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(minutes=5)
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(hours=1)


# ============================================================
# Google Auth - Testing
# ============================================================

ADMIN_INVITE_CODE = 'test-admin-invite'


# ============================================================
# Logging - Testing (Minimal)
# ============================================================

LOGGING['handlers']['console']['level'] = 'WARNING'
LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['django.request']['level'] = 'ERROR'
LOGGING['loggers']['django.security']['level'] = 'ERROR'

# Disable all loggers except critical
for logger_name in LOGGING['loggers']:
    LOGGING['loggers'][logger_name]['level'] = 'ERROR'


# ============================================================
# Cache - Locmem for Testing
# ============================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-sessions',
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'


# ============================================================
# Celery - Testing (Eager Mode)
# ============================================================

CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache://'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BEAT_SCHEDULE = {}


# ============================================================
# AI Scribe - Testing (Disabled)
# ============================================================

AI_SCRIBE_ENABLED = False
AI_SCRIBE_ALLOW_MOCK_PROVIDERS = True


# ============================================================
# FHIR/HL7/ABDM - Testing (Disabled)
# ============================================================

FHIR_ENABLED = False
HL7_ENABLED = False
ABDM_ENABLED = False


# ============================================================
# Monitoring - Testing (Disabled)
# ============================================================

MONITORING_ENABLED = False


# ============================================================
# Backup - Testing (Disabled)
# ============================================================

BACKUP_ENABLED = False


# ============================================================
# Password Hashing - Fast for Tests
# ============================================================

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]


# ============================================================
# Rate Limiting - Disabled for Tests
# ============================================================

RATE_LIMIT_ENABLED = False
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}


# ============================================================
# Health Checks - Testing
# ============================================================

HEALTH_CHECK_ENABLED = True


# ============================================================
# Migrations - Disable for Tests (if needed)
# ============================================================

# Uncomment to disable migrations for faster tests
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()


# ============================================================
# Test-Specific Settings
# ============================================================

# Test runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Parallel test execution (if supported)
# TEST_PARALLEL = True