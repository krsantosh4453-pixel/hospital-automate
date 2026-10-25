"""Twilio Verify v2 service for SMS OTP authentication."""

import logging
import os
from dataclasses import dataclass

from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)

TWILIO_VERIFY_NOT_CONFIGURED = "Twilio Verify is not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_VERIFY_SERVICE_SID, and either TWILIO_API_KEY + TWILIO_API_SECRET or TWILIO_AUTH_TOKEN."


@dataclass
class VerifyResult:
    ok: bool
    message: str
    sid: str | None = None


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
            logger.error(f"Failed to initialize Twilio Verify client: {e}")
            self._initialized = True

    def is_configured(self) -> bool:
        self._initialize()
        return self._client is not None and self._verify_service_sid is not None

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format (+91XXXXXXXXXX for India)."""
        digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
        if len(digits) == 10:
            return f"+91{digits}"
        elif len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"
        elif len(digits) == 13 and digits.startswith("+91"):
            return digits
        elif digits.startswith("+"):
            return digits
        return f"+91{digits[-10:]}" if len(digits) >= 10 else ""

    def start_verification(self, phone: str, channel: str = "sms") -> VerifyResult:
        """Start a new verification via Twilio Verify."""
        self._initialize()

        if not self.is_configured():
            logger.error("Twilio Verify not configured")
            return VerifyResult(False, TWILIO_VERIFY_NOT_CONFIGURED)

        to = self._normalize_phone(phone)
        if not to:
            return VerifyResult(False, "Invalid phone number format")

        try:
            verification = self._client.verify.v2.services(self._verify_service_sid).verifications.create(
                to=to,
                channel=channel,
            )
            logger.info(f"Twilio Verify started for {to}: {verification.sid} (status: {verification.status})")
            return VerifyResult(True, "OTP sent to your registered mobile number.", verification.sid)
        except TwilioException as e:
            logger.exception(f"Twilio Verify start failed for {to}")
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                return VerifyResult(False, "Too many requests. Please try again later.")
            return VerifyResult(False, "Unable to send OTP. Please try again.")
        except Exception as e:
            logger.exception(f"Unexpected error starting Twilio Verify for {to}")
            return VerifyResult(False, "Unable to send OTP. Please try again.")

    def check_verification(self, phone: str, code: str) -> VerifyResult:
        """Verify the OTP code via Twilio Verify."""
        self._initialize()

        if not self.is_configured():
            logger.error("Twilio Verify not configured")
            return VerifyResult(False, TWILIO_VERIFY_NOT_CONFIGURED)

        to = self._normalize_phone(phone)
        if not to:
            return VerifyResult(False, "Invalid phone number format")

        clean_code = "".join(ch for ch in str(code or "") if ch.isdigit())
        if len(clean_code) != 6:
            return VerifyResult(False, "Invalid OTP format")

        try:
            verification_check = self._client.verify.v2.services(self._verify_service_sid).verification_checks.create(
                to=to,
                code=clean_code,
            )
            logger.info(f"Twilio Verify check for {to}: {verification_check.status}")

            if verification_check.status == "approved":
                return VerifyResult(True, "OTP verified successfully.", verification_check.sid)
            elif verification_check.status == "pending":
                return VerifyResult(False, "Invalid or expired OTP.")
            else:
                return VerifyResult(False, "Invalid or expired OTP.")
        except TwilioException as e:
            logger.exception(f"Twilio Verify check failed for {to}")
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                return VerifyResult(False, "Too many verification attempts. Please try again later.")
            return VerifyResult(False, "Unable to verify OTP. Please try again.")
        except Exception as e:
            logger.exception(f"Unexpected error checking Twilio Verify for {to}")
            return VerifyResult(False, "Unable to verify OTP. Please try again.")


_twilio_verify_service = None


def get_twilio_verify_service() -> TwilioVerifyService:
    """Get singleton TwilioVerifyService instance."""
    global _twilio_verify_service
    if _twilio_verify_service is None:
        _twilio_verify_service = TwilioVerifyService()
    return _twilio_verify_service