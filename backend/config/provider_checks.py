"""
Live checks against the real external providers (Twilio Verify, SMTP e-mail,
speech-to-text, LLM, Google Sign-In, push).

Every check here is read-only: it proves the credentials and configuration
are accepted by the provider without sending an SMS, an e-mail or patient
data. Real deliveries are separate, explicit steps in the ``check_providers``
management command.

Each result is one of:
  PASS     the provider accepted the configuration
  FAIL     credentials are present but the provider rejected them
  BLOCKED  credentials or configuration are missing
  MOCK     only a development mock is wired up (never real delivery)

Details never include secrets, phone numbers or e-mail addresses.
"""

import base64
import re
import smtplib
import urllib.parse
from dataclasses import dataclass

import requests
from django.conf import settings

PASS, FAIL, BLOCKED, MOCK = "PASS", "FAIL", "BLOCKED", "MOCK"
HTTP_TIMEOUT_SECONDS = 15
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_CLIENT_ID_PATTERN = re.compile(r"^[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com$")
NON_DELIVERING_EMAIL_BACKENDS = ("console", "locmem", "dummy", "filebased")


@dataclass(frozen=True)
class CheckResult:
    provider: str
    status: str
    detail: str


def check_twilio_verify() -> CheckResult:
    """Fetch the configured Verify service with the configured credentials."""
    from twilio.base.exceptions import TwilioRestException

    from users.twilio_verify import TwilioVerifyService

    service = TwilioVerifyService()
    if not service.is_configured():
        return CheckResult("twilio_verify", BLOCKED, "TWILIO_ACCOUNT_SID, TWILIO_VERIFY_SERVICE_SID and an API key "
                                                     "(or auth token) are not all set")
    sid = str(service._verify_service_sid)
    if not sid.startswith("VA"):
        return CheckResult("twilio_verify", FAIL, f"TWILIO_VERIFY_SERVICE_SID must start with 'VA' (got '{sid[:2]}…')")
    try:
        verify = service._client.verify.v2.services(sid).fetch()
    except TwilioRestException as exc:
        return CheckResult("twilio_verify", FAIL, f"Twilio rejected the request: HTTP {exc.status}, code {exc.code}")
    except Exception as exc:  # network failures
        return CheckResult("twilio_verify", FAIL, f"Twilio unreachable: {type(exc).__name__}")
    return CheckResult("twilio_verify", PASS,
                       f"Verify service '{verify.friendly_name}' reachable (code length {verify.code_length})")


def check_email() -> CheckResult:
    """Log in to the SMTP server; no message is sent."""
    backend = str(getattr(settings, "EMAIL_BACKEND", ""))
    if "smtp" not in backend.lower():
        status = MOCK if any(n in backend for n in NON_DELIVERING_EMAIL_BACKENDS) else BLOCKED
        return CheckResult("email", status, f"EMAIL_BACKEND is {backend}; nothing is delivered")
    host, port = settings.EMAIL_HOST, int(settings.EMAIL_PORT)
    user, password = settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD
    if not (host and user and password):
        return CheckResult("email", BLOCKED, "EMAIL_HOST, EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required")
    try:
        if getattr(settings, "EMAIL_USE_SSL", False):
            connection = smtplib.SMTP_SSL(host, port, timeout=HTTP_TIMEOUT_SECONDS)
        else:
            connection = smtplib.SMTP(host, port, timeout=HTTP_TIMEOUT_SECONDS)
            if getattr(settings, "EMAIL_USE_TLS", False):
                connection.starttls()
        with connection:
            connection.login(user, password)
    except smtplib.SMTPAuthenticationError as exc:
        return CheckResult("email", FAIL, f"SMTP login rejected by {host} (code {exc.smtp_code})")
    except (smtplib.SMTPException, OSError) as exc:
        return CheckResult("email", FAIL, f"SMTP {host}:{port} failed: {type(exc).__name__}")
    return CheckResult("email", PASS, f"SMTP login accepted by {host}:{port}")


def _check_openai_compatible(name: str, base_url: str, api_key: str, model: str) -> CheckResult:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/models", headers={"Authorization": f"Bearer {api_key}"},
                                timeout=HTTP_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return CheckResult(name, FAIL, f"{base_url} unreachable: {type(exc).__name__}")
    if response.status_code != 200:
        return CheckResult(name, FAIL, f"{base_url} rejected the key: HTTP {response.status_code}")
    try:
        models = {item.get("id") for item in response.json().get("data", [])}
    except (ValueError, AttributeError):
        return CheckResult(name, FAIL, f"{base_url} returned an unreadable model list")
    if model not in models:
        return CheckResult(name, FAIL, f"key accepted, but model '{model}' is not offered by {base_url}")
    return CheckResult(name, PASS, f"key accepted by {base_url}; model '{model}' available")


def check_stt() -> CheckResult:
    from ai_scribe.services.stt import SpeechToTextService

    service = SpeechToTextService()
    default = service._default_provider
    if default is None:
        return CheckResult("stt", BLOCKED, "no speech-to-text provider configured (AI_SCRIBE_STT_API_KEY)")
    if default == "development":
        return CheckResult("stt", MOCK, "only the development mock transcriber is available")
    if default != "whisper_api":
        return CheckResult("stt", PASS, f"local provider '{default}' installed (not a network service)")
    provider = service.get_provider()
    return _check_openai_compatible("stt", provider.base_url, provider.api_key, provider.model)


def check_llm() -> CheckResult:
    from ai_scribe.services.llm import LLMClinicalService

    service = LLMClinicalService()
    default = service._default_provider
    if default is None:
        return CheckResult("llm", BLOCKED, "no LLM provider configured (AI_SCRIBE_API_KEY)")
    if default == "development":
        return CheckResult("llm", MOCK, "only the development mock LLM is available")
    if default != "openai":
        return CheckResult("llm", PASS, f"provider '{default}' registered; no read-only probe implemented for it")
    provider = service.get_provider()
    return _check_openai_compatible("llm", provider.base_url, provider.api_key, provider.default_model)


def google_auth_error(redirect_url: str) -> str:
    """Google reports a bad client in an encoded ``authError`` query value."""
    match = re.search(r"authError=([^&]+)", redirect_url or "")
    if not match:
        return ""
    raw = urllib.parse.unquote(match.group(1))
    try:
        decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "ignore")
    except ValueError:
        return "unknown_error"
    for code in ("invalid_client", "deleted_client", "disabled_client", "redirect_uri_mismatch"):
        if code in decoded:
            return code
    return "unknown_error"


def check_google_client() -> CheckResult:
    """Ask Google whether the OAuth client behind GOOGLE_CLIENT_ID exists."""
    client_id = (getattr(settings, "GOOGLE_CLIENT_ID", "") or "").strip()
    if not client_id:
        return CheckResult("google_signin", BLOCKED, "GOOGLE_CLIENT_ID is not set")
    if not GOOGLE_CLIENT_ID_PATTERN.match(client_id):
        return CheckResult("google_signin", FAIL, "GOOGLE_CLIENT_ID is not a Google OAuth client ID")
    query = urllib.parse.urlencode({
        "client_id": client_id, "response_type": "id_token", "scope": "openid email",
        "nonce": "provider-check", "redirect_uri": "http://localhost",
    })
    try:
        response = requests.get(f"{GOOGLE_AUTH_URL}?{query}", allow_redirects=False, timeout=HTTP_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return CheckResult("google_signin", FAIL, f"Google unreachable: {type(exc).__name__}")
    error = google_auth_error(response.headers.get("Location", ""))
    if error in ("invalid_client", "deleted_client", "disabled_client"):
        return CheckResult("google_signin", FAIL, f"Google reports {error} for GOOGLE_CLIENT_ID")
    # redirect_uri_mismatch for the probe URI means Google found the client.
    return CheckResult("google_signin", PASS, "Google recognises the OAuth client")


def check_twilio_messaging() -> CheckResult:
    """SMS/WhatsApp notifications: credentials accepted and a sender configured."""
    from twilio.base.exceptions import TwilioRestException

    from notifications.services.providers import _setting, _twilio_client

    client = _twilio_client()
    if client is None:
        return CheckResult("twilio_messaging", BLOCKED, "TWILIO_ACCOUNT_SID and an API key (or auth token) are not set")
    try:
        account = client.api.v2010.accounts(_setting("TWILIO_ACCOUNT_SID")).fetch()
    except TwilioRestException as exc:
        return CheckResult("twilio_messaging", FAIL, f"Twilio rejected the credentials: HTTP {exc.status}, code {exc.code}")
    except Exception as exc:
        return CheckResult("twilio_messaging", FAIL, f"Twilio unreachable: {type(exc).__name__}")
    senders = [name for name in ("TWILIO_MESSAGING_SERVICE_SID", "TWILIO_PHONE_NUMBER", "TWILIO_WHATSAPP_FROM")
               if _setting(name)]
    if not senders:
        return CheckResult("twilio_messaging", BLOCKED, f"credentials accepted ({account.type} account) but no sender: "
                                                        "set TWILIO_MESSAGING_SERVICE_SID or TWILIO_PHONE_NUMBER")
    return CheckResult("twilio_messaging", PASS, f"credentials accepted ({account.type} account); "
                                                 f"senders: {', '.join(senders)}")


def check_push() -> CheckResult:
    return CheckResult("push", BLOCKED, "there is no push channel in notifications/services/providers.py "
                                        "(FIREBASE_CREDENTIALS_PATH is unused); in-app notifications are unaffected")


ALL_CHECKS = (check_twilio_verify, check_twilio_messaging, check_email, check_stt, check_llm,
              check_google_client, check_push)


def run_all_checks() -> list:
    return [check() for check in ALL_CHECKS]
