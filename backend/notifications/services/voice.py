"""
Automated voice calls, used as a fallback when SMS/WhatsApp delivery fails.

Providers implement ``VoiceCallProvider``. ``get_voice_call_provider`` picks
one from the environment:

    VOICE_CALL_PROVIDER=twilio        # default: noop
    TWILIO_ACCOUNT_SID=AC...
    TWILIO_AUTH_TOKEN=...
    TWILIO_VOICE_FROM_NUMBER=+91...   # a Twilio voice-capable number
    TWILIO_VOICE_LANGUAGE=en-IN       # optional, <Say> language

Without credentials the no-op provider is used: calls are recorded as
skipped and nothing is dialled, so the system runs without an account.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

NOT_CONFIGURED = "Voice calls are not configured"


@dataclass(frozen=True)
class VoiceCallResult:
    success: bool
    call_id: str = ""
    error: str = ""


class VoiceCallProvider(ABC):
    name = "base"

    def is_configured(self) -> bool:
        return True

    @abstractmethod
    def place_call(self, to_number: str, message: str) -> VoiceCallResult:
        """Dial ``to_number`` (E.164) and read ``message`` aloud."""


class NoopVoiceCallProvider(VoiceCallProvider):
    """Default: dials nothing and reports that voice calls are off."""

    name = "noop"

    def is_configured(self) -> bool:
        return False

    def place_call(self, to_number: str, message: str) -> VoiceCallResult:
        logger.info("Voice call not placed: no voice provider configured.")
        return VoiceCallResult(success=False, error=NOT_CONFIGURED)


def twiml_for(message: str, language: str = "en-IN") -> str:
    """TwiML that reads the message twice (people often miss the start of a call)."""
    say = f'<Say language="{escape(language)}">{escape(message)}</Say>'
    return f'<Response>{say}<Pause length="1"/>{say}</Response>'


class TwilioVoiceCallProvider(VoiceCallProvider):
    """Twilio Programmable Voice via the twilio SDK (already a dependency)."""

    name = "twilio"

    def __init__(self, account_sid: str, auth_token: str, from_number: str, language: str = "en-IN"):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.language = language
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)

    def _get_client(self):
        if self._client is None:
            from twilio.rest import Client

            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def place_call(self, to_number: str, message: str) -> VoiceCallResult:
        if not self.is_configured():
            return VoiceCallResult(success=False, error=NOT_CONFIGURED)
        try:
            call = self._get_client().calls.create(
                to=to_number, from_=self.from_number, twiml=twiml_for(message, self.language),
            )
        except Exception as exc:  # network, auth or Twilio API errors
            # Error class only: the message may echo the phone number.
            logger.warning("Twilio voice call failed: %s", type(exc).__name__)
            return VoiceCallResult(success=False, error=f"Twilio error: {type(exc).__name__}")
        return VoiceCallResult(success=True, call_id=str(call.sid))


def get_voice_call_provider() -> VoiceCallProvider:
    choice = os.getenv("VOICE_CALL_PROVIDER", "noop").strip().lower()
    if choice == "twilio":
        provider = TwilioVoiceCallProvider(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            from_number=os.getenv("TWILIO_VOICE_FROM_NUMBER", ""),
            language=os.getenv("TWILIO_VOICE_LANGUAGE", "en-IN"),
        )
        if provider.is_configured():
            return provider
        logger.warning("VOICE_CALL_PROVIDER=twilio but Twilio credentials are missing; voice calls are off.")
    elif choice not in ("", "noop"):
        logger.warning("Unknown VOICE_CALL_PROVIDER %r; voice calls are off.", choice)
    return NoopVoiceCallProvider()


def to_e164(phone: str, default_country_code: Optional[str] = None) -> str:
    """Stored phones are usually 10 local digits; prefix the country code."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if str(phone or "").strip().startswith("+"):
        return f"+{digits}"
    if len(digits) == 10:
        code = default_country_code or os.getenv("VOICE_CALL_DEFAULT_COUNTRY_CODE", "91")
        return f"+{code}{digits}"
    return f"+{digits}" if len(digits) > 10 else ""
