"""Read-only provider checks, the e-mail channel, and no silent mock fallback.

Network calls are faked: these tests prove how each check classifies a
provider's answer. Real answers come from `manage.py check_providers`.
"""

import base64
import smtplib
import urllib.parse
from unittest import mock

from django.test import SimpleTestCase, override_settings

from ai_scribe.services.llm import LLMClinicalService
from ai_scribe.services.stt import SpeechToTextService
from config import provider_checks as checks
from notifications.services.providers import EmailProvider

GOOD_CLIENT = "123456789012-abcdefghijklmnopqrstuvwxyz012345.apps.googleusercontent.com"


def google_redirect(error_code):
    blob = base64.urlsafe_b64encode(f"\n\x0e{error_code}\x12 details".encode()).decode().rstrip("=")
    return f"https://accounts.google.com/signin/oauth/error?authError={urllib.parse.quote(blob)}&client_id=x"


def http_response(status_code=200, json_body=None, headers=None):
    response = mock.Mock(status_code=status_code, headers=headers or {})
    response.json.return_value = json_body or {}
    return response


class GoogleClientCheckTests(SimpleTestCase):
    def test_decodes_google_auth_errors(self):
        self.assertEqual(checks.google_auth_error(google_redirect("invalid_client")), "invalid_client")
        self.assertEqual(checks.google_auth_error(google_redirect("redirect_uri_mismatch")), "redirect_uri_mismatch")
        self.assertEqual(checks.google_auth_error("https://accounts.google.com/signin"), "")

    @override_settings(GOOGLE_CLIENT_ID=GOOD_CLIENT)
    def test_unknown_client_fails(self):
        location = google_redirect("invalid_client")
        with mock.patch.object(checks.requests, "get", return_value=http_response(302, headers={"Location": location})):
            self.assertEqual(checks.check_google_client().status, checks.FAIL)

    @override_settings(GOOGLE_CLIENT_ID=GOOD_CLIENT)
    def test_known_client_passes(self):
        location = google_redirect("redirect_uri_mismatch")
        with mock.patch.object(checks.requests, "get", return_value=http_response(302, headers={"Location": location})):
            self.assertEqual(checks.check_google_client().status, checks.PASS)

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_missing_client_is_blocked(self):
        self.assertEqual(checks.check_google_client().status, checks.BLOCKED)

    @override_settings(GOOGLE_CLIENT_ID="test-google-client")
    def test_malformed_client_fails_without_a_request(self):
        with mock.patch.object(checks.requests, "get") as get:
            self.assertEqual(checks.check_google_client().status, checks.FAIL)
        get.assert_not_called()


class TwilioVerifyCheckTests(SimpleTestCase):
    @override_settings(TWILIO_ACCOUNT_SID="", TWILIO_VERIFY_SERVICE_SID="", TWILIO_API_KEY="", TWILIO_API_SECRET="",
                       TWILIO_AUTH_TOKEN="")
    def test_missing_credentials_are_blocked(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(checks.check_twilio_verify().status, checks.BLOCKED)

    @override_settings(TWILIO_ACCOUNT_SID="AC" + "1" * 32, TWILIO_VERIFY_SERVICE_SID="SK" + "1" * 32,
                       TWILIO_API_KEY="SK" + "2" * 32, TWILIO_API_SECRET="s" * 32)
    def test_api_key_sid_in_the_verify_slot_fails(self):
        result = checks.check_twilio_verify()
        self.assertEqual(result.status, checks.FAIL)
        self.assertIn("'VA'", result.detail)
        self.assertNotIn("1" * 32, result.detail)


class OpenAICompatibleCheckTests(SimpleTestCase):
    def test_rejected_key_fails(self):
        with mock.patch.object(checks.requests, "get", return_value=http_response(401)):
            result = checks._check_openai_compatible("llm", "https://api.example.test/v1", "k", "m")
        self.assertEqual(result.status, checks.FAIL)

    def test_missing_model_fails(self):
        with mock.patch.object(checks.requests, "get", return_value=http_response(200, {"data": [{"id": "other"}]})):
            result = checks._check_openai_compatible("llm", "https://api.example.test/v1", "k", "m")
        self.assertEqual(result.status, checks.FAIL)

    def test_key_and_model_pass(self):
        with mock.patch.object(checks.requests, "get", return_value=http_response(200, {"data": [{"id": "m"}]})):
            result = checks._check_openai_compatible("llm", "https://api.example.test/v1", "k", "m")
        self.assertEqual(result.status, checks.PASS)


class EmailCheckTests(SimpleTestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_console_backend_is_reported_as_mock(self):
        self.assertEqual(checks.check_email().status, checks.MOCK)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="smtp.example.test",
                       EMAIL_PORT=587, EMAIL_HOST_USER="", EMAIL_HOST_PASSWORD="")
    def test_smtp_without_login_is_blocked(self):
        self.assertEqual(checks.check_email().status, checks.BLOCKED)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="smtp.example.test",
                       EMAIL_PORT=587, EMAIL_HOST_USER="apikey", EMAIL_HOST_PASSWORD="wrong", EMAIL_USE_TLS=True,
                       EMAIL_USE_SSL=False)
    def test_rejected_smtp_login_fails(self):
        smtp = mock.MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad credentials")
        with mock.patch.object(checks.smtplib, "SMTP", return_value=smtp):
            result = checks.check_email()
        self.assertEqual(result.status, checks.FAIL)
        self.assertNotIn("wrong", result.detail)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend", EMAIL_HOST="smtp.gmail.com")
    def test_notification_email_is_not_reported_sent_by_the_console_backend(self):
        self.assertFalse(EmailProvider().is_configured())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="smtp.example.test")
    def test_notification_email_uses_smtp_when_configured(self):
        self.assertTrue(EmailProvider().is_configured())


@override_settings(AI_SCRIBE_ALLOW_MOCK_PROVIDERS=False, AI_SCRIBE_API_KEY="", AI_SCRIBE_STT_API_KEY="",
                   AI_SCRIBE_STT_PROVIDER="")
class NoSilentMockFallbackTests(SimpleTestCase):
    """With mocks disallowed (production) and no keys, no mock is registered."""

    def test_stt_registers_no_mock(self):
        with mock.patch.dict("sys.modules", {"whisper": None}):
            service = SpeechToTextService()
        self.assertNotIn("development", service._providers)
        self.assertIsNone(service._default_provider)
        with mock.patch.dict("sys.modules", {"whisper": None}):
            self.assertEqual(checks.check_stt().status, checks.BLOCKED)

    def test_llm_registers_no_mock(self):
        service = LLMClinicalService()
        self.assertNotIn("development", service._providers)
        self.assertNotEqual(service._default_provider, "development")
