"""
Django production settings for Hospital Management System.

Extends base settings with production-hardened configuration.
All secrets must be provided via environment variables.
"""

from .base import *  # noqa: F403,F401
import os
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured


# ============================================================
# Security - Production
# ============================================================

# SECRET_KEY must be set via environment variable
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY environment variable is required in production')

# DEBUG must be False in production
DEBUG = False

# ALLOWED_HOSTS must be explicitly configured
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ImproperlyConfigured('ALLOWED_HOSTS environment variable is required in production')

# HTTPS/SSL Settings
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Secure Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'

# HSTS
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# CSP (Content Security Policy) for responses Django serves (API, admin),
# via csp.middleware.CSPMiddleware in MIDDLEWARE. django-csp 4 reads only
# CONTENT_SECURITY_POLICY; the old CSP_* names are silently ignored.
# The SPA's own policy is set by nginx (nginx.conf.template).
_CSP_DIRECTIVES = {
    'default-src': ["'self'"],
    'style-src': ["'self'", "'unsafe-inline'"],  # unsafe-inline needed for some admin styles
    'script-src': ["'self'"],
    'img-src': ["'self'", "data:", "https:"],
    'font-src': ["'self'"],
    'connect-src': ["'self'"],
    'frame-ancestors': ["'none'"],
    'form-action': ["'self'"],
    'base-uri': ["'self'"],
    'object-src': ["'none'"],
}
# Report CSP violations
if os.environ.get('CSP_REPORT_URI'):
    _CSP_DIRECTIVES['report-uri'] = os.environ['CSP_REPORT_URI']
# CSP_REPORT_ONLY=True sends the policy as report-only while testing it.
if os.environ.get('CSP_REPORT_ONLY', 'False').lower() == 'true':
    CONTENT_SECURITY_POLICY_REPORT_ONLY = {'DIRECTIVES': _CSP_DIRECTIVES}
else:
    CONTENT_SECURITY_POLICY = {'DIRECTIVES': _CSP_DIRECTIVES}


# ============================================================
# Database - PostgreSQL for Production
# ============================================================

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ImproperlyConfigured('DATABASE_URL environment variable is required in production')

# Parse DATABASE_URL
# Format: postgres://user:password@host:port/dbname
db_url = urlparse(DATABASE_URL)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_url.path[1:],
        'USER': db_url.username,
        'PASSWORD': db_url.password,
        'HOST': db_url.hostname,
        'PORT': db_url.port or 5432,
        'CONN_MAX_AGE': 60,  # Persistent connections
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 second statement timeout
        },
        'TEST': {
            'NAME': 'test_' + db_url.path[1:],
        },
    }
}

# Connection pooling via PgBouncer (if configured)
# Use DATABASE_URL with pgbouncer host/port


# ============================================================
# Middleware - Production (add CSP middleware)
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",  # Content Security Policy
    "config.middleware.correlation.CorrelationIdMiddleware",
    "config.middleware.correlation.LoggingContextMiddleware",
    "config.middleware.ratelimit.RateLimitMiddleware",
]


# ============================================================
# CORS - Production
# ============================================================

CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured('CORS_ALLOWED_ORIGINS environment variable is required in production')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()


# ============================================================
# Email - Production (SMTP)
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Hospital Management System <noreply@hospital.example.com>')

if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    raise ImproperlyConfigured('EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required in production')


# ============================================================
# Static Files - Production (WhiteNoise or CDN)
# ============================================================

STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# If using CDN/Cloud Storage (AWS S3, GCS, Azure Blob)
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN')
# AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME')
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')


# ============================================================
# Media Files - Production (Private Storage)
# ============================================================

MEDIA_ROOT = BASE_DIR / 'media'

# For private media (patient documents, medical reports), use protected storage
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# PRIVATE_MEDIA_STORAGE = 'config.storage.PrivateMediaStorage'


# ============================================================
# JWT - Production (RS256 with Key Pair)
# ============================================================

# Load RSA private key for signing (RS256)
JWT_PRIVATE_KEY = os.environ.get('JWT_PRIVATE_KEY')
JWT_PUBLIC_KEY = os.environ.get('JWT_PUBLIC_KEY')
JWT_KEY_ID = os.environ.get('JWT_KEY_ID', 'hms-key-1')

if not JWT_PRIVATE_KEY or not JWT_PUBLIC_KEY:
    raise ImproperlyConfigured(
        'JWT_PRIVATE_KEY and JWT_PUBLIC_KEY environment variables are required in production. '
        'Generate with: openssl genrsa -out private.pem 2048 && openssl rsa -in private.pem -pubout -out public.pem'
    )

SIMPLE_JWT['SIGNING_KEY'] = JWT_PRIVATE_KEY
SIMPLE_JWT['VERIFYING_KEY'] = JWT_PUBLIC_KEY
SIMPLE_JWT['ALGORITHM'] = 'RS256'
SIMPLE_JWT['AUDIENCE'] = os.environ.get('JWT_AUDIENCE', 'hms-api')
SIMPLE_JWT['ISSUER'] = os.environ.get('JWT_ISSUER', 'hospital-management-system')
SIMPLE_JWT['JWK_URL'] = os.environ.get('JWK_URL')  # Optional: for key rotation via JWKS endpoint

# Token lifetime - shorter access tokens for better security
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(minutes=10)
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(days=1)


# ============================================================
# Google Auth - Production
# ============================================================

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
if not GOOGLE_CLIENT_ID:
    raise ImproperlyConfigured('GOOGLE_CLIENT_ID environment variable is required in production')
ADMIN_INVITE_CODE = os.environ.get("ADMIN_INVITE_CODE", "")


# ============================================================
# Logging - Production (Structured JSON)
# ============================================================

LOGGING['handlers']['console']['formatter'] = 'json'
LOGGING['handlers']['console']['level'] = 'INFO'
LOGGING['root']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['django.request']['level'] = 'ERROR'
LOGGING['loggers']['django.security']['level'] = 'ERROR'

# Add file handler for production
LOGGING['handlers']['file'] = {
    'level': 'INFO',
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': BASE_DIR / 'logs' / 'django.log',
    'maxBytes': 10 * 1024 * 1024,  # 10MB
    'backupCount': 10,
    'formatter': 'json',
}

# Add error file handler
LOGGING['handlers']['error_file'] = {
    'level': 'ERROR',
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': BASE_DIR / 'logs' / 'django_errors.log',
    'maxBytes': 10 * 1024 * 1024,
    'backupCount': 10,
    'formatter': 'json',
}

# Add handlers to root logger
LOGGING['root']['handlers'].extend(['file', 'error_file'])

# Add handlers to specific loggers
for logger_name in ['django', 'django.request', 'django.security']:
    if logger_name in LOGGING['loggers']:
        LOGGING['loggers'][logger_name]['handlers'].append('file')
        if logger_name in ['django.request', 'django.security']:
            LOGGING['loggers'][logger_name]['handlers'].append('error_file')

# Ensure logs directory exists
import pathlib
pathlib.Path(BASE_DIR / 'logs').mkdir(parents=True, exist_ok=True)


# ============================================================
# Cache - Redis for Production
# ============================================================

REDIS_URL = os.environ.get('REDIS_URL')
if not REDIS_URL:
    raise ImproperlyConfigured('REDIS_URL environment variable is required in production')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'hms',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'hms_session',
        'TIMEOUT': 86400,  # 24 hours
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'


# ============================================================
# Celery - Production
# ============================================================

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# Celery worker configuration
CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', '4'))
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# Result backend settings
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 86400  # 24 hours

# Task routing for priority queues
CELERY_TASK_ROUTES = {
    'notifications.tasks.send_*': {'queue': 'notifications'},
    'reports.tasks.generate_*': {'queue': 'reports'},
    'ai_scribe.tasks.*': {'queue': 'ai_processing'},
    'audit.tasks.*': {'queue': 'audit'},
    'backup.tasks.*': {'queue': 'maintenance'},
}

# Beat schedule
# Only tasks that exist in the codebase are scheduled. Daily report generation
# and backup verification are run by the ops scripts in docs/OPERATIONS_RUNBOOK.md.
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-otp': {
        'task': 'notifications.tasks.cleanup_expired_otp',
        'schedule': 3600.0,
    },
    'cleanup-old-audit-logs': {
        'task': 'audit.tasks.cleanup_old_audit_logs',
        'schedule': 86400.0,
    },
}


# ============================================================
# AI Scribe - Production
# ============================================================

AI_SCRIBE_ENABLED = os.environ.get('AI_SCRIBE_ENABLED', 'True').lower() == 'true'
# Mock providers produce canned clinical content and are never allowed here.
AI_SCRIBE_ALLOW_MOCK_PROVIDERS = False
AI_SCRIBE_PROVIDER = os.environ.get('AI_SCRIBE_PROVIDER', 'openai')
AI_SCRIBE_API_KEY = os.environ.get('AI_SCRIBE_API_KEY')
AI_SCRIBE_MODEL = os.environ.get('AI_SCRIBE_MODEL', 'gpt-4')
AI_SCRIBE_MAX_TOKENS = int(os.environ.get('AI_SCRIBE_MAX_TOKENS', '4000'))
AI_SCRIBE_TEMPERATURE = float(os.environ.get('AI_SCRIBE_TEMPERATURE', '0.1'))

# AI Scribe is optional - without an API key it is switched off (mock
# providers are never allowed in production, see above).
if AI_SCRIBE_ENABLED and not AI_SCRIBE_API_KEY:
    import warnings
    warnings.warn('AI_SCRIBE_API_KEY not set - AI Scribe is disabled')
    AI_SCRIBE_ENABLED = False


# ============================================================
# FHIR - Production
# ============================================================

# FHIR/HL7/ABDM routes are not mounted (config/urls.py); keep them off unless
# a deployment has completed their conformance and security review.
FHIR_ENABLED = os.environ.get('FHIR_ENABLED', 'False').lower() == 'true'
FHIR_BASE_URL = os.environ.get('FHIR_BASE_URL')
FHIR_VERSION = os.environ.get('FHIR_VERSION', 'R4')


# ============================================================
# HL7 - Production
# ============================================================

HL7_ENABLED = os.environ.get('HL7_ENABLED', 'False').lower() == 'true'
HL7_LISTEN_PORT = int(os.environ.get('HL7_LISTEN_PORT', '2575'))
HL7_MSH_SENDING_APPLICATION = os.environ.get('HL7_MSH_SENDING_APPLICATION', 'HMS')
HL7_MSH_SENDING_FACILITY = os.environ.get('HL7_MSH_SENDING_FACILITY', 'HOSPITAL')

# HL7 Security - Required in production
HL7_IP_WHITELIST = [
    ip.strip() for ip in os.environ.get('HL7_IP_WHITELIST', '').split(',')
    if ip.strip()
]
if HL7_ENABLED and not HL7_IP_WHITELIST:
    raise ImproperlyConfigured('HL7_IP_WHITELIST environment variable is required when HL7_ENABLED=True')

HL7_API_KEY = os.environ.get('HL7_API_KEY')
if HL7_ENABLED and not HL7_API_KEY:
    raise ImproperlyConfigured('HL7_API_KEY environment variable is required when HL7_ENABLED=True')


# ============================================================
# ABDM/ABHA - Production
# ============================================================

ABDM_ENABLED = os.environ.get('ABDM_ENABLED', 'False').lower() == 'true'
ABDM_BASE_URL = os.environ.get('ABDM_BASE_URL')
ABDM_CLIENT_ID = os.environ.get('ABDM_CLIENT_ID')
ABDM_CLIENT_SECRET = os.environ.get('ABDM_CLIENT_SECRET')

if ABDM_ENABLED and (not ABDM_BASE_URL or not ABDM_CLIENT_ID or not ABDM_CLIENT_SECRET):
    raise ImproperlyConfigured('ABDM_BASE_URL, ABDM_CLIENT_ID, and ABDM_CLIENT_SECRET are required when ABDM_ENABLED=True')


# ============================================================
# Notifications - Production
# ============================================================

SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'twilio')

# Twilio Verify v2 (required for OTP in production)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_API_KEY = os.environ.get('TWILIO_API_KEY')
TWILIO_API_SECRET = os.environ.get('TWILIO_API_SECRET')
TWILIO_VERIFY_SERVICE_SID = os.environ.get('TWILIO_VERIFY_SERVICE_SID')

# Legacy Twilio SMS (fallback)
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# OTP Provider: must be 'twilio' in production for real SMS
OTP_PROVIDER = os.environ.get('OTP_PROVIDER', 'twilio')
if OTP_PROVIDER != 'twilio':
    raise ImproperlyConfigured("OTP_PROVIDER must be 'twilio' in production")

# Staff must complete SMS OTP after the password in production unless explicitly disabled.
STAFF_LOGIN_REQUIRE_OTP = os.environ.get('STAFF_LOGIN_REQUIRE_OTP', 'True').lower() == 'true'

# Validate Twilio Verify configuration in production
if not (TWILIO_ACCOUNT_SID and TWILIO_API_KEY and TWILIO_API_SECRET and TWILIO_VERIFY_SERVICE_SID):
    raise ImproperlyConfigured(
        'TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, and TWILIO_VERIFY_SERVICE_SID '
        'are required in production for Twilio Verify OTP'
    )

WHATSAPP_PROVIDER = os.environ.get('WHATSAPP_PROVIDER', 'twilio')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')

PUSH_NOTIFICATION_PROVIDER = os.environ.get('PUSH_NOTIFICATION_PROVIDER', 'firebase')
FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')


# ============================================================
# Monitoring - Production
# ============================================================

MONITORING_ENABLED = os.environ.get('MONITORING_ENABLED', 'False').lower() == 'true'

# Sentry
SENTRY_DSN = os.environ.get('SENTRY_DSN')
SENTRY_ENVIRONMENT = os.environ.get('SENTRY_ENVIRONMENT', 'production')
SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
SENTRY_PROFILES_SAMPLE_RATE = float(os.environ.get('SENTRY_PROFILES_SAMPLE_RATE', '0.1'))

# Prometheus metrics (if using django-prometheus)
# PROMETHEUS_EXPORT_MIGRATIONS = False


# ============================================================
# Backup - Production
# ============================================================

BACKUP_ENABLED = os.environ.get('BACKUP_ENABLED', 'False').lower() == 'true'
BACKUP_STORAGE_PATH = os.environ.get('BACKUP_STORAGE_PATH', '/backups')
BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
BACKUP_ENCRYPTION_KEY = os.environ.get('BACKUP_ENCRYPTION_KEY')


# ============================================================
# File Storage - Production (Cloud Storage)
# ============================================================

# AWS S3 Configuration (example)
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
# AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
# AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN')
# AWS_DEFAULT_ACL = 'private'
# AWS_S3_OBJECT_PARAMETERS = {
#     'CacheControl': 'max-age=86400',
# }

# Private media storage for sensitive documents
# PRIVATE_MEDIA_STORAGE = 'config.storage.PrivateMediaStorage'


# ============================================================
# Rate Limiting - Production
# ============================================================

RATE_LIMIT_ENABLED = True

# nginx sits in front of Django (docker-compose.prod.yml); see base.py.
TRUSTED_PROXY_COUNT = int(os.environ.get('TRUSTED_PROXY_COUNT', '1'))
REST_FRAMEWORK['NUM_PROXIES'] = TRUSTED_PROXY_COUNT

# DRF Throttle rates (override base)
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour',
    'login': '5/minute',
    'otp': '3/minute',
    'password_reset': '2/hour',
    'ai': '30/minute',
    'audio_upload': '10/minute',
    'fhir': '60/minute',
    'hl7': '60/minute',
}


# ============================================================
# Health Checks - Production
# ============================================================

HEALTH_CHECK_ENABLED = True
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 85,
    'MEMORY_MIN': 500,  # MB
}


# ============================================================
# Additional Production Security
# ============================================================

# Admin URL obfuscation
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')

# Disable browsable API in production
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer']

# Ensure secure password reset
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour


# ============================================================
# Import local overrides if any (for secret management)
# ============================================================

try:
    from .local import *  # noqa: F403,F401
except ImportError:
    pass