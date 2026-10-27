"""
Settings for the browser (Playwright) end-to-end tests.

A throwaway SQLite file (E2E_DB_PATH) holds the seed_demo hospital. Every
outside service is off, staff sign in with the password alone, and the
throttles are loose enough for many sign-ins in one run. Never use this for
a real server.
"""

import os

# development.py refuses to start without these; the e2e server needs no real ones.
os.environ.setdefault("DJANGO_SECRET_KEY", "e2e-only-not-a-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "e2e-google-client")

from .development import *  # noqa: E402,F403,F401

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("E2E_DB_PATH", str(BASE_DIR / "e2e.sqlite3")),  # noqa: F405
    }
}

# No SMS, e-mail, Google or dev-login shortcuts: the tests use the real password form.
OTP_PROVIDER = "console"
PATIENT_OTP_DELIVERY = "console"
SMS_PROVIDER = "console"
STAFF_LOGIN_REQUIRE_OTP = False
TWILIO_ACCOUNT_SID = TWILIO_API_KEY = TWILIO_API_SECRET = ""
TWILIO_VERIFY_SERVICE_SID = TWILIO_AUTH_TOKEN = TWILIO_PHONE_NUMBER = ""
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEV_LOGIN_ENABLED = False
AI_SCRIBE_ENABLED = False
FHIR_ENABLED = HL7_ENABLED = ABDM_ENABLED = False
CELERY_TASK_ALWAYS_EAGER = True

RATE_LIMIT_ENABLED = False
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# development.py logs every SQL query; keep the test output readable.
LOGGING["handlers"]["console"]["level"] = "WARNING"  # noqa: F405
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
for _logger in LOGGING["loggers"].values():  # noqa: F405
    _logger["level"] = "WARNING"
