"""Twilio Verify v2 service for SMS OTP authentication."""

import logging
import os
from dataclasses import dataclass

from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioException, TwilioRestException

logger = logging.getLogger(__name__)

TWILIO_VERIFY_NOT_CONFIGURED = "Twilio Verify is not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_VERIFY_SERVICE_SID, and either TWILIO_API_KEY + TWILIO_API_SECRET or TWILIO_AUTH_TOKEN."


MSG_LIMITED_SEND = "Too many requests. Please try again later."
MSG_LIMITED_CHECK = "Too many verification attempts. Please try again later."
MSG_INVALID_OR_EXPIRED = "Invalid or expired OTP."
MSG_INVALID_NUMBER = "Invalid phone number format"
MSG_SEND_FAILED = "Unable to send OTP. Please try again."
MSG_CHECK_FAILED = "Unable to verify OTP. Please try again."

# Twilio error codes (https://www.twilio.com/docs/api/errors) mapped to outcomes.
# Only the code is ever logged: Twilio's message text echoes the phone number.
TWILIO_AUTH_FAILED = {20003}
TWILIO_NOT_FOUND = 20404  # check: verification expired, approved or never started
TWILIO_RATE_LIMITED = {20429, 60202, 60203, 60212}
TWILIO_INVALID_NUMBER = {21211, 21214, 21614, 60200, 60205}
TWILIO_UNDELIVERABLE = {21408, 21608, 21610, 60220, 60410, 60605}


@dataclass
class VerifyResult:
    ok: bool
    message: str
    sid: str | None = None
    # Machine-readable outcome: sent, approved, rejected, limited, invalid_number,
    # expired, not_configured, provider_auth, undeliverable, provider_error.
    reason: str = ""


def mask_phone(phone: str) -> str:
    """Keep the last four digits only, for logs."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    return f"***{digits[-4:]}" if len(digits) >= 4 else "***"


def _twilio_failure(exc: Exception, to: str, step: str, limited_msg: str, failed_msg: str) -> VerifyResult:
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    if code in TWILIO_AUTH_FAILED or status == 401:
        logger.critical("Twilio Verify rejected the credentials (%s, code %s); check TWILIO_* settings", step, code)
        return VerifyResult(False, failed_msg, reason="provider_auth")
    logger.warning("Twilio Verify %s failed for %s: HTTP %s code %s", step, mask_phone(to), status, code)
    if step == "check" and code == TWILIO_NOT_FOUND:
        return VerifyResult(False, MSG_INVALID_OR_EXPIRED, reason="expired")
    if code in TWILIO_RATE_LIMITED or status == 429:
        return VerifyResult(False, limited_msg, reason="limited")
    if code in TWILIO_INVALID_NUMBER:
        return VerifyResult(False, MSG_INVALID_NUMBER, reason="invalid_number")
    if code in TWILIO_UNDELIVERABLE:
        return VerifyResult(False, failed_msg, reason="undeliverable")
    return VerifyResult(False, failed_msg, reason="provider_error")


class TwilioVerifyService:
    """Twilio Verify v2 API wrapper for SMS OTP."""

    def __init__(self):
        self._client = None
        self._verify_service_sid = None
        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return

        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.environ.get("TWILIO_ACCOUNT_SID")
        api_key = getattr(settings, "TWILIO_API_KEY", None) or os.environ.get("TWILIO_API_KEY")
        api_secret = getattr(settings, "TWILIO_API_SECRET", None) or os.environ.get("TWILIO_API_SECRET")
        verify_service_sid = getattr(settings, "TWILIO_VERIFY_SERVICE_SID", None) or os.environ.get("TWILIO_VERIFY_SERVICE_SID")
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.environ.get("TWILIO_AUTH_TOKEN")

        # API key + secret is preferred; the account auth token works too.
        has_api_key = bool(api_key and api_secret)
        if not (account_sid and verify_service_sid and (has_api_key or auth_token)):
            logger.warning("Twilio Verify credentials not fully configured")
            self._initialized = True
            return

        try:
            if has_api_key:
                self._client = Client(api_key, api_secret, account_sid)
            else:
                self._client = Client(account_sid, auth_token)
            self._verify_service_sid = verify_service_sid
            self._initialized = True
        except Exception as e:
            logger.error("Failed to initialize Twilio Verify client: %s", type(e).__name__)
            self._initialized = True

    def is_configured(self) -> bool:
        self._initialize()
        return self._client is not None and self._verify_service_sid is not None

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format (+91XXXXXXXXXX for India)."""
        digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
        if len(digits) == 10:
            return f"+91{digits}"
        if len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"
        return f"+91{digits[-10:]}" if len(digits) >= 10 else ""

    def start_verification(self, phone: str, channel: str = "sms") -> VerifyResult:
        """Start a new verification via Twilio Verify."""
        self._initialize()

        if not self.is_configured():
            logger.error("Twilio Verify not configured")
            return VerifyResult(False, TWILIO_VERIFY_NOT_CONFIGURED, reason="not_configured")

        to = self._normalize_phone(phone)
        if not to:
            return VerifyResult(False, MSG_INVALID_NUMBER, reason="invalid_number")

        try:
            verification = self._client.verify.v2.services(self._verify_service_sid).verifications.create(
                to=to,
                channel=channel,
            )
        except TwilioRestException as e:
            return _twilio_failure(e, to, "start", MSG_LIMITED_SEND, MSG_SEND_FAILED)
        except TwilioException as e:
            logger.error("Twilio Verify start failed for %s: %s", mask_phone(to), type(e).__name__)
            return VerifyResult(False, MSG_SEND_FAILED, reason="provider_error")
        except Exception as e:
            logger.error("Unexpected error starting Twilio Verify for %s: %s", mask_phone(to), type(e).__name__)
            return VerifyResult(False, MSG_SEND_FAILED, reason="provider_error")
        logger.info("Twilio Verify started for %s: %s (status: %s)", mask_phone(to), verification.sid, verification.status)
        return VerifyResult(True, "OTP sent to your registered mobile number.", verification.sid, reason="sent")

    def check_verification(self, phone: str, code: str) -> VerifyResult:
        """Verify the OTP code via Twilio Verify."""
        self._initialize()

        if not self.is_configured():
            logger.error("Twilio Verify not configured")
            return VerifyResult(False, TWILIO_VERIFY_NOT_CONFIGURED, reason="not_configured")

        to = self._normalize_phone(phone)
        if not to:
            return VerifyResult(False, MSG_INVALID_NUMBER, reason="invalid_number")

        clean_code = "".join(ch for ch in str(code or "") if ch.isdigit())
        if len(clean_code) != 6:
            return VerifyResult(False, "Invalid OTP format", reason="rejected")

        try:
            verification_check = self._client.verify.v2.services(self._verify_service_sid).verification_checks.create(
                to=to,
                code=clean_code,
            )
        except TwilioRestException as e:
            return _twilio_failure(e, to, "check", MSG_LIMITED_CHECK, MSG_CHECK_FAILED)
        except TwilioException as e:
            logger.error("Twilio Verify check failed for %s: %s", mask_phone(to), type(e).__name__)
            return VerifyResult(False, MSG_CHECK_FAILED, reason="provider_error")
        except Exception as e:
            logger.error("Unexpected error checking Twilio Verify for %s: %s", mask_phone(to), type(e).__name__)
            return VerifyResult(False, MSG_CHECK_FAILED, reason="provider_error")

        logger.info("Twilio Verify check for %s: %s", mask_phone(to), verification_check.status)
        if verification_check.status == "approved":
            return VerifyResult(True, "OTP verified successfully.", verification_check.sid, reason="approved")
        return VerifyResult(False, MSG_INVALID_OR_EXPIRED, reason="rejected")

_twilio_verify_service = None


def get_twilio_verify_service() -> TwilioVerifyService:
    """Get singleton TwilioVerifyService instance."""
    global _twilio_verify_service
    if _twilio_verify_service is None:
        _twilio_verify_service = TwilioVerifyService()
    return _twilio_verify_service