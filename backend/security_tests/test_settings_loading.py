"""
Each settings module must load on its own. config/settings/__init__.py runs
before any submodule, and it used to import development.py unconditionally,
so the test and production settings failed without development-only
variables (a fresh clone or CI could not run the test suite).
"""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BACKEND_DIR = Path(__file__).resolve().parents[1]


# Synthetic values only; production settings refuse to load without them.
PRODUCTION_ENV = {
    "DJANGO_SECRET_KEY": "synthetic-" + "x" * 50, "ALLOWED_HOSTS": "hms.example.test",
    "DATABASE_URL": "postgres://u:p@localhost:5432/db", "CORS_ALLOWED_ORIGINS": "https://hms.example.test",
    "EMAIL_HOST_USER": "x", "EMAIL_HOST_PASSWORD": "x", "GOOGLE_CLIENT_ID": "x",
    "REDIS_URL": "redis://localhost:6399/0", "JWT_PRIVATE_KEY": "x", "JWT_PUBLIC_KEY": "x",
    "TWILIO_ACCOUNT_SID": "x", "TWILIO_API_KEY": "x", "TWILIO_API_SECRET": "x",
    "TWILIO_VERIFY_SERVICE_SID": "x", "FHIR_ENABLED": "False", "HL7_ENABLED": "False",
    "ABDM_ENABLED": "False", "AI_SCRIBE_ENABLED": "False",
}


def load_settings(module, **env):
    # Blank, not removed: load_dotenv never overrides a variable that is set,
    # so a developer's local .env cannot hide the failure.
    child_env = {**os.environ, "DJANGO_SECRET_KEY": "", "GOOGLE_CLIENT_ID": "", "DJANGO_ENV": ""}
    child_env.update(env, DJANGO_SETTINGS_MODULE=module)
    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup(); from django.conf import settings; print(settings.SECRET_KEY[:4])"],
        cwd=BACKEND_DIR,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


class SettingsLoadingTests(SimpleTestCase):
    def test_testing_settings_load_without_development_variables(self):
        result = load_settings("config.settings.testing")
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])

    def test_production_settings_send_a_content_security_policy(self):
        env = PRODUCTION_ENV
        script = (
            "import django; django.setup()\n"
            "from django.http import HttpResponse\n"
            "from django.test import RequestFactory\n"
            "from csp.middleware import CSPMiddleware\n"
            "resp = CSPMiddleware(lambda r: HttpResponse())(RequestFactory().get('/'))\n"
            "print(resp.get('Content-Security-Policy'))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=BACKEND_DIR, capture_output=True, text=True, timeout=120,
            env={**os.environ, **env, "DJANGO_SETTINGS_MODULE": "config.settings.production", "DJANGO_ENV": ""},
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("script-src 'self'", result.stdout)
        self.assertIn("frame-ancestors 'none'", result.stdout)

    # --- Twilio is needed only when SMS OTP is used (RL-06) -------------------

    def production(self, **env):
        """Load production settings with ``env`` on top of PRODUCTION_ENV; print OTP_PROVIDER."""
        result = subprocess.run(
            [sys.executable, "-c", "import django; django.setup(); from django.conf import settings; "
                                   "print(settings.OTP_PROVIDER)"],
            cwd=BACKEND_DIR, capture_output=True, text=True, timeout=120,
            env={**os.environ, **PRODUCTION_ENV, **env, "DJANGO_SETTINGS_MODULE": "config.settings.production",
                 "DJANGO_ENV": ""},
        )
        return result

    NO_TWILIO = {"TWILIO_ACCOUNT_SID": "", "TWILIO_API_KEY": "", "TWILIO_API_SECRET": "",
                 "TWILIO_VERIFY_SERVICE_SID": ""}

    def test_production_boots_without_twilio_when_sms_otp_is_off(self):
        result = self.production(**self.NO_TWILIO, STAFF_LOGIN_REQUIRE_OTP="False", PATIENT_OTP_DELIVERY="off")

        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual(result.stdout.strip().splitlines()[-1], "disabled")

    def test_production_still_requires_twilio_for_staff_sms_otp(self):
        result = self.production(**self.NO_TWILIO, PATIENT_OTP_DELIVERY="off")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("STAFF_LOGIN_REQUIRE_OTP=False", result.stderr)

    def test_production_still_requires_twilio_for_patient_sms_otp(self):
        result = self.production(**self.NO_TWILIO, STAFF_LOGIN_REQUIRE_OTP="False")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PATIENT_OTP_DELIVERY=off", result.stderr)

    def test_production_refuses_development_otp_delivery(self):
        for mode in ("console", "cache"):
            with self.subTest(mode=mode):
                result = self.production(PATIENT_OTP_DELIVERY=mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("PATIENT_OTP_DELIVERY", result.stderr)

    def test_production_with_twilio_keeps_sms_otp(self):
        result = self.production()

        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual(result.stdout.strip().splitlines()[-1], "twilio")

    def test_package_settings_still_require_development_secret(self):
        result = load_settings("config.settings")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY environment variable is required", result.stderr)

    def test_production_static_files_get_content_hashed_names(self):
        # nginx caches /static/ for a year as immutable, so every file name must
        # change with its content (Django 6 ignores the old STATICFILES_STORAGE).
        script = (
            "import tempfile, pathlib, django; django.setup()\n"
            "from django.conf import settings\n"
            "from django.core.management import call_command\n"
            "from django.test.utils import override_settings\n"
            "print(settings.STORAGES['staticfiles']['BACKEND'])\n"
            "with override_settings(STATIC_ROOT=tempfile.mkdtemp()):\n"
            "    call_command('collectstatic', interactive=False, verbosity=0)\n"
            "    from django.contrib.staticfiles.storage import staticfiles_storage as s\n"
            "    print(pathlib.Path(settings.STATIC_ROOT, 'staticfiles.json').exists(), s.url('admin/css/base.css'))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=BACKEND_DIR, capture_output=True, text=True, timeout=300,
            env={**os.environ, **PRODUCTION_ENV, "DJANGO_SETTINGS_MODULE": "config.settings.production", "DJANGO_ENV": ""},
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        backend, collected = result.stdout.strip().splitlines()[-2:]
        self.assertEqual(backend, "django.contrib.staticfiles.storage.ManifestStaticFilesStorage")
        manifest, url = collected.split()
        self.assertEqual(manifest, "True")
        self.assertRegex(url, r"^/static/admin/css/base\.[0-9a-f]{12}\.css$")

