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


@dataclass
class NotificationResult:
    """Result of a notification send attempt."""
    channel: NotificationChannel
    success: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: Optional[datetime] = None


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


class SMSProvider(NotificationProvider):
    """
    SMS provider abstraction.

    In production, implement with Twilio, Plivo, or similar.
    Configuration via environment variables.
    """

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SMS

    def is_configured(self) -> bool:
        import os
        return bool(os.getenv("SMS_PROVIDER_ACCOUNT_SID") and os.getenv("SMS_PROVIDER_AUTH_TOKEN"))

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            logger.warning("SMSProvider not configured, skipping")
            return NotificationResult(
                channel=self.channel,
                success=False,
                error="Provider not configured",
            )

        # Not implemented yet (Twilio Messaging, Plivo, ...): report the
        # failure instead of recording a delivery that never happened.
        return _not_implemented(self.channel, payload)


class WhatsAppProvider(NotificationProvider):
    """
    WhatsApp provider abstraction.

    In production, implement with Twilio WhatsApp Business API or similar.
    """

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WHATSAPP

    def is_configured(self) -> bool:
        import os
        return bool(os.getenv("WHATSAPP_PROVIDER_ACCOUNT_SID") and os.getenv("WHATSAPP_PROVIDER_AUTH_TOKEN"))

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            logger.warning("WhatsAppProvider not configured, skipping")
            return NotificationResult(
                channel=self.channel,
                success=False,
                error="Provider not configured",
            )

        # Not implemented yet: see _not_implemented.
        return _not_implemented(self.channel, payload)


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
            return NotificationResult(channel=self.channel, success=False, error="Email could not be sent")
        return NotificationResult(channel=self.channel, success=True, sent_at=datetime.now())


def _not_implemented(channel: NotificationChannel, payload: NotificationPayload) -> NotificationResult:
    # Ids only: the message may contain clinical details.
    logger.warning("%s delivery is not implemented; nothing sent to patient %s", channel.value, payload.patient_id)
    return NotificationResult(channel=channel, success=False, error=f"{channel.value} sending is not implemented")