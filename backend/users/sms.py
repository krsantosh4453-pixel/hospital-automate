"""SMS delivery for patient OTP. Development never pretends a text was sent."""

import base64
import logging
import os
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

SMS_NOT_CONFIGURED = "Unable to send SMS OTP. SMS service is not configured."


class SMSResult:
    def __init__(self, ok, delivery, message):
        self.ok = ok
        self.delivery = delivery
        self.message = message


class SMSService:
    """Send a one-time code through the configured provider."""

    def send_otp(self, phone, otp):
        mode = getattr(settings, "PATIENT_OTP_DELIVERY", "sms")
        if mode == "cache":
            cache.set(f"patient-otp:{phone}", otp, timeout=300)
            return SMSResult(True, "cache", "Verification code stored for the test runner.")
        if mode == "console":
            cache.set(f"patient-otp:{phone}", otp, timeout=300)
            logger.warning(
                "Patient OTP for %s (development console only, not sent by SMS): %s",
                phone,
                otp,
            )
            return SMSResult(
                True,
                "console",
                "SMS service is in development mode. The code was written to the server console and was not sent to the phone.",
            )
        return self._send_twilio(phone, otp)

    def _send_twilio(self, phone, otp):
        sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.environ.get("TWILIO_ACCOUNT_SID")
        token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.environ.get("TWILIO_AUTH_TOKEN")
        sender = getattr(settings, "TWILIO_PHONE_NUMBER", None) or os.environ.get("TWILIO_PHONE_NUMBER")
        if not (sid and token and sender):
            logger.error("SMS OTP provider is not configured")
            return SMSResult(False, "sms", SMS_NOT_CONFIGURED)

        try:
            payload = urllib.parse.urlencode(
                {
                    "To": f"+91{phone}",
                    "From": sender,
                    "Body": f"Your hospital verification code is {otp}. It expires in 5 minutes.",
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data=payload,
                method="POST",
            )
            request.add_header(
                "Authorization",
                "Basic " + base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii"),
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                if 200 <= response.status < 300:
                    return SMSResult(
                        True,
                        "sms",
                        "A verification code was sent to your mobile number.",
                    )
        except Exception:
            logger.exception("Patient OTP SMS delivery failed")
        return SMSResult(False, "sms", "Unable to send SMS OTP. SMS service is not configured.")
