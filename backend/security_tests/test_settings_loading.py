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
        # Synthetic values only; production settings refuse to load without them.
        env = {
            "DJANGO_SECRET_KEY": "synthetic-" + "x" * 50, "ALLOWED_HOSTS": "hms.example.test",
            "DATABASE_URL": "postgres://u:p@localhost:5432/db", "CORS_ALLOWED_ORIGINS": "https://hms.example.test",
            "EMAIL_HOST_USER": "x", "EMAIL_HOST_PASSWORD": "x", "GOOGLE_CLIENT_ID": "x",
            "REDIS_URL": "redis://localhost:6399/0", "JWT_PRIVATE_KEY": "x", "JWT_PUBLIC_KEY": "x",
            "TWILIO_ACCOUNT_SID": "x", "TWILIO_API_KEY": "x", "TWILIO_API_SECRET": "x",
            "TWILIO_VERIFY_SERVICE_SID": "x", "FHIR_ENABLED": "False", "HL7_ENABLED": "False",
            "ABDM_ENABLED": "False", "AI_SCRIBE_ENABLED": "False",
        }
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

    def test_package_settings_still_require_development_secret(self):
        result = load_settings("config.settings")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY environment variable is required", result.stderr)
