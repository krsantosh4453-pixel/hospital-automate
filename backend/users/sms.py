"""SMS delivery for patient OTP using Twilio Verify v2. Development never pretends a text was sent."""

import logging
import os

from django.conf import settings
from django.core.cache import cache

from users.twilio_verify import get_twilio_verify_service, TWILIO_VERIFY_NOT_CONFIGURED

logger = logging.getLogger(__name__)

SMS_NOT_CONFIGURED = "Unable to send SMS OTP. SMS service is not configured."


class SMSResult:
    def __init__(self, ok, delivery, message, sid=None):
        self.ok = ok
        self.delivery = delivery
        self.message = message
        self.sid = sid


class SMSService:
    """Send a one-time code through the configured provider using Twilio Verify v2."""

    def send_otp(self, phone, otp=None):
        """
        Start OTP verification via Twilio Verify.
        The otp parameter is kept for backward compatibility but is ignored
        since Twilio Verify generates its own OTP.
        """
        mode = getattr(settings, "PATIENT_OTP_DELIVERY", "sms")
        if mode == "cache":
            # For testing: store a dummy OTP in cache
            test_otp = otp or "123456"
            cache.set(f"patient-otp:{phone}", test_otp, timeout=300)
            return SMSResult(True, "cache", "Verification code stored for the test runner.")
        if mode == "console":
            # For development: log to console
            test_otp = otp or "123456"
            cache.set(f"patient-otp:{phone}", test_otp, timeout=300)
            logger.warning(
                "Patient OTP for %s (development console only, not sent by SMS): %s",
                phone,
                test_otp,
            )
            return SMSResult(
                True,
                "console",
                "SMS service is in development mode. The code was written to the server console and was not sent to the phone.",
            )
        return self._send_twilio_verify(phone)

    def _send_twilio_verify(self, phone):
        """Start verification using Twilio Verify v2 API."""
        verify_service = get_twilio_verify_service()

        if not verify_service.is_configured():
            logger.error("Twilio Verify not configured")
            return SMSResult(False, "sms", TWILIO_VERIFY_NOT_CONFIGURED)

        result = verify_service.start_verification(phone, channel="sms")
        return SMSResult(result.ok, "sms" if result.ok else "sms", result.message, result.sid)

    def verify_otp(self, phone, otp):
        """Verify OTP using the configured provider."""
        mode = getattr(settings, "PATIENT_OTP_DELIVERY", "sms")
        if mode == "cache" or mode == "console":
            cached_otp = cache.get(f"patient-otp:{phone}")
            if cached_otp and str(cached_otp) == str(otp):
                cache.delete(f"patient-otp:{phone}")
                return SMSResult(True, mode, "OTP verified successfully.")
            return SMSResult(False, mode, "Invalid or expired OTP.")

        verify_service = get_twilio_verify_service()

        if not verify_service.is_configured():
            logger.error("Twilio Verify not configured")
            return SMSResult(False, "sms", TWILIO_VERIFY_NOT_CONFIGURED)

        result = verify_service.check_verification(phone, otp)
        return SMSResult(result.ok, "sms", result.message, result.sid)