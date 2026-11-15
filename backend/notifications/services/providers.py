"""
Notification Provider Abstraction

Provides a pluggable architecture for sending notifications via multiple channels:
SMS, WhatsApp, Voice, Email, In-App.

Each provider implements the NotificationProvider protocol.
Configuration is externalized - no hardcoded credentials.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Supported notification channels."""
    IN_APP = "in_app"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    EMAIL = "email"


class NotificationEvent(Enum):
    """Queue and appointment lifecycle events that trigger notifications."""
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    QUEUE_TOKEN_CREATED = "queue_token_created"
    QUEUE_WAIT_ESTIMATE_UPDATED = "queue_wait_estimate_updated"
    PATIENT_CALLED = "patient_called"
    PATIENT_ACK_REQUIRED = "patient_ack_required"
    PATIENT_READY = "patient_ready"
    APPOINTMENT_DELAYED = "appointment_delayed"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    CONSULTATION_STARTED = "consultation_started"
    CONSULTATION_COMPLETED = "consultation_completed"


@dataclass
class NotificationPayload:
    """Data payload for a notification."""
    event: NotificationEvent
    patient_id: int
    hospital_id: int
    title: str
    message: str
    metadata: Optional[dict] = None
    channels: Optional[list[NotificationChannel]] = None
    scheduled_at: Optional[datetime] = None

    def __post_init__(self):
        if self.channels is None:
            self.channels = [NotificationChannel.IN_APP]
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """JSON-safe form, used to hand the payload to a Celery task."""
        return {
            "event": self.event.value,
            "patient_id": self.patient_id,
            "hospital_id": self.hospital_id,
            "title": self.title,
            "message": self.message,
            "metadata": self.metadata,
            "channels": [channel.value for channel in self.channels],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationPayload":
        return cls(
            event=NotificationEvent(data["event"]),
            patient_id=data["patient_id"],
            hospital_id=data["hospital_id"],
            title=data["title"],
            message=data["message"],
            metadata=data.get("metadata") or {},
            channels=[NotificationChannel(value) for value in data.get("channels") or []],
        )


@dataclass
class NotificationResult:
    """Result of a notification send attempt."""
    channel: NotificationChannel
    success: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: Optional[datetime] = None
    # True only for transient failures (network, provider outage) that a
    # later attempt may fix; consent, configuration and data problems are not.
    retryable: bool = False


class NotificationProvider(ABC):
    """Abstract interface for notification providers."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """The channel this provider handles."""
        pass

    @abstractmethod
    def send(self, payload: NotificationPayload) -> NotificationResult:
        """
        Send a notification.

        Args:
            payload: The notification payload.

        Returns:
            NotificationResult with success status and provider details.
        """
        pass

    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        return True


class InAppProvider(NotificationProvider):
    """In-app notification provider - stores notifications in the database."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.IN_APP

    def send(self, payload: NotificationPayload) -> NotificationResult:
        from notifications.models import Notification
        from patients.models import Patient

        try:
            patient = Patient.objects.get(pk=payload.patient_id)
            notification = Notification.objects.create(
                patient=patient,
                hospital_id=payload.hospital_id,
                title=payload.title,
                message=payload.message,
                notification_type=payload.event.value,
            )
            return NotificationResult(
                channel=self.channel,
                success=True,
                provider_message_id=str(notification.id),
                sent_at=datetime.now(),
            )
        except Exception as e:
            logger.error(f"InAppProvider failed: {e}")
            return NotificationResult(
                channel=self.channel,
                success=False,
                error=str(e),
            )


class ConsoleProvider(NotificationProvider):
    """Console/logging provider for development and testing."""

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SMS  # Acts as SMS for testing

    def send(self, payload: NotificationPayload) -> NotificationResult:
        logger.info(
            f"[NOTIFICATION] Channel: {self.channel.value} | "
            f"Event: {payload.event.value} | "
            f"Patient: {payload.patient_id} | "
            f"Title: {payload.title} | "
            f"Message: {payload.message} | "
            f"Metadata: {payload.metadata}"
        )
        return NotificationResult(
            channel=self.channel,
            success=True,
            provider_message_id=f"console-{datetime.now().timestamp()}",
            sent_at=datetime.now(),
        )


def _setting(name):
    from django.conf import settings

    return getattr(settings, name, "") or ""


def _twilio_client():
    """A Twilio REST client from the TWILIO_* settings (API key preferred), or None."""
    account = _setting("TWILIO_ACCOUNT_SID")
    key, secret, token = _setting("TWILIO_API_KEY"), _setting("TWILIO_API_SECRET"), _setting("TWILIO_AUTH_TOKEN")
    if not account or not ((key and secret) or token):
        return None
    from twilio.rest import Client

    return Client(key, secret, account) if key and secret else Client(account, token)


def _twilio_credentials_set():
    return bool(_setting("TWILIO_ACCOUNT_SID") and (
        (_setting("TWILIO_API_KEY") and _setting("TWILIO_API_SECRET")) or _setting("TWILIO_AUTH_TOKEN")))


# Twilio errors that a later attempt can fix: rate limits and its own outages.
def _retryable(status):
    return status == 429 or (status or 0) >= 500


class _TwilioMessagingProvider(NotificationProvider):
    """
    P1-09: one message to the patient's mobile through Twilio Messaging. The
    subclass says how to address it and what to send. Errors carry codes only,
    never message text, which may hold clinical details.
    """

    def _sender_ready(self) -> bool:  # pragma: no cover - subclasses decide
        raise NotImplementedError

    def _message(self, to: str, payload: NotificationPayload) -> dict:  # pragma: no cover
        raise NotImplementedError

    def is_configured(self) -> bool:
        return _twilio_credentials_set() and self._sender_ready()

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            logger.warning("%s sending is not configured; skipping", self.channel.value)
            return NotificationResult(channel=self.channel, success=False, error="Provider not configured")
        from patients.models import Patient
        from twilio.base.exceptions import TwilioRestException

        from .voice import to_e164

        phone = Patient.objects.filter(pk=payload.patient_id).values_list("phone", flat=True).first()
        to = to_e164(phone or "")
        if not to:
            return NotificationResult(channel=self.channel, success=False, error="Patient has no mobile number")
        message = self._message(to, payload)
        callback = _setting("TWILIO_STATUS_CALLBACK_URL")
        if callback:
            message["status_callback"] = callback
        try:
            sent = _twilio_client().messages.create(**message)
        except TwilioRestException as exc:
            logger.error("Twilio %s failed for patient %s: HTTP %s, code %s",
                         self.channel.value, payload.patient_id, exc.status, exc.code)
            return NotificationResult(channel=self.channel, success=False,
                                      error=f"Twilio error {exc.code or exc.status}", retryable=_retryable(exc.status))
        except Exception as exc:
            # Network trouble before Twilio answered.
            logger.error("Twilio %s failed for patient %s: %s", self.channel.value, payload.patient_id,
                         type(exc).__name__)
            return NotificationResult(channel=self.channel, success=False, error="Twilio could not be reached",
                                      retryable=True)
        return NotificationResult(channel=self.channel, success=True, provider_message_id=sent.sid,
                                  sent_at=datetime.now())


class SMSProvider(_TwilioMessagingProvider):
    """
    SMS through Twilio Messaging. TWILIO_MESSAGING_SERVICE_SID is preferred (it
    holds the DLT-registered sender Indian operators require); TWILIO_PHONE_NUMBER otherwise.
    """

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SMS

    def _sender_ready(self) -> bool:
        return bool(_setting("TWILIO_MESSAGING_SERVICE_SID") or _setting("TWILIO_PHONE_NUMBER"))

    def _message(self, to, payload):
        message = {"to": to, "body": f"{payload.title}: {payload.message}" if payload.title else payload.message}
        if _setting("TWILIO_MESSAGING_SERVICE_SID"):
            message["messaging_service_sid"] = _setting("TWILIO_MESSAGING_SERVICE_SID")
        else:
            message["from_"] = _setting("TWILIO_PHONE_NUMBER")
        return message


class WhatsAppProvider(_TwilioMessagingProvider):
    """
    WhatsApp through Twilio from TWILIO_WHATSAPP_FROM. WhatsApp accepts free text
    only within 24 hours of the patient's last message; messages the hospital
    starts need an approved template, TWILIO_WHATSAPP_CONTENT_SID, filled with
    {"1": title, "2": message}.
    """

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WHATSAPP

    def _sender_ready(self) -> bool:
        return bool(_setting("TWILIO_WHATSAPP_FROM"))

    def _message(self, to, payload):
        sender = _setting("TWILIO_WHATSAPP_FROM")
        message = {"to": f"whatsapp:{to}",
                   "from_": sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}"}
        template = _setting("TWILIO_WHATSAPP_CONTENT_SID")
        if template:
            import json

            message["content_sid"] = template
            message["content_variables"] = json.dumps({"1": payload.title, "2": payload.message})
        else:
            message["body"] = f"{payload.title}: {payload.message}" if payload.title else payload.message
        return message


class VoiceProvider(NotificationProvider):
    """
    Voice call provider abstraction.

    In production, implement with Twilio Voice, Plivo, or similar.
    Used for critical alerts where SMS/WhatsApp may not be sufficient.
    """

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.VOICE

    def is_configured(self) -> bool:
        import os
        return bool(os.getenv("VOICE_PROVIDER_ACCOUNT_SID") and os.getenv("VOICE_PROVIDER_AUTH_TOKEN"))

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            logger.warning("VoiceProvider not configured, skipping")
            return NotificationResult(
                channel=self.channel,
                success=False,
                error="Provider not configured",
            )

        # Not implemented yet: see _not_implemented.
        return _not_implemented(self.channel, payload)


class EmailProvider(NotificationProvider):
    """
    Email provider abstraction.

    In production, uses Django's email backend (SMTP, SendGrid, etc.)
    """

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    def is_configured(self) -> bool:
        from django.conf import settings
        return bool(getattr(settings, "EMAIL_HOST", None))

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            logger.warning("EmailProvider not configured, skipping")
            return NotificationResult(
                channel=self.channel,
                success=False,
                error="Provider not configured",
            )

        from django.conf import settings
        from django.core.mail import send_mail
        from patients.models import Patient

        patient = Patient.objects.select_related("user").filter(pk=payload.patient_id).first()
        address = getattr(getattr(patient, "user", None), "email", "") if patient else ""
        if not address:
            return NotificationResult(channel=self.channel, success=False, error="Patient has no email address")
        try:
            send_mail(payload.title, payload.message, settings.DEFAULT_FROM_EMAIL, [address])
        except Exception as e:
            # Ids only: the message may contain clinical details.
            logger.error("EmailProvider failed for patient %s: %s", payload.patient_id, type(e).__name__)
            return NotificationResult(channel=self.channel, success=False, error="Email could not be sent",
                                      retryable=True)
        return NotificationResult(channel=self.channel, success=True, sent_at=datetime.now())


def _not_implemented(channel: NotificationChannel, payload: NotificationPayload) -> NotificationResult:
    # Ids only: the message may contain clinical details.
    logger.warning("%s delivery is not implemented; nothing sent to patient %s", channel.value, payload.patient_id)
    return NotificationResult(channel=channel, success=False, error=f"{channel.value} sending is not implemented")