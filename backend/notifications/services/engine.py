"""
Notification Engine

Orchestrates notification delivery across multiple providers.
Handles consent checking, channel selection, and delivery tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Optional
import logging

from django.db import models
from collections import deque

from .providers import (
    NotificationChannel,
    NotificationEvent,
    NotificationPayload,
    NotificationProvider,
    NotificationResult,
    InAppProvider,
    ConsoleProvider,
    SMSProvider,
    WhatsAppProvider,
    VoiceProvider,
    EmailProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class DeliveryRecord:
    """Record of a notification delivery attempt."""
    payload: NotificationPayload
    results: list[NotificationResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class NotificationEngine:
    """
    Central notification orchestration service.

    Responsibilities:
    - Provider registration and management
    - Consent verification before sending
    - Channel selection and fallback
    - Delivery tracking and audit
    """

    def __init__(self):
        self._providers: dict[NotificationChannel, NotificationProvider] = {}
        self._default_providers = [
            InAppProvider(),
            ConsoleProvider(),  # Development fallback
            SMSProvider(),
            WhatsAppProvider(),
            VoiceProvider(),
            EmailProvider(),
        ]
        self._register_defaults()
        # Recent attempts for diagnostics only; the durable record is
        # notifications.NotificationDelivery.
        self._delivery_history: deque[DeliveryRecord] = deque(maxlen=500)

    def _register_defaults(self):
        for provider in self._default_providers:
            self.register_provider(provider)

    def register_provider(self, provider: NotificationProvider):
        """Register a notification provider."""
        self._providers[provider.channel] = provider
        logger.info(f"Registered notification provider: {provider.channel.value}")

    def unregister_provider(self, channel: NotificationChannel):
        """Unregister a provider."""
        if channel in self._providers:
            del self._providers[channel]

    def get_provider(self, channel: NotificationChannel) -> Optional[NotificationProvider]:
        """Get a provider by channel."""
        return self._providers.get(channel)

    def get_available_channels(self) -> list[NotificationChannel]:
        """Get list of configured and available channels."""
        return [
            channel for channel, provider in self._providers.items()
            if provider.is_configured()
        ]

    def check_consent(self, patient_id: int, event: NotificationEvent, channel: NotificationChannel,
                      hospital_id: Optional[int] = None) -> bool:
        """
        Check if patient has consented to this notification type/channel.

        Args:
            patient_id: Patient ID
            event: The notification event
            channel: The delivery channel

        Returns:
            True if consent granted or not required, False otherwise.
        """
        from notifications.models import Consent

        # In-app notifications don't require explicit consent (they're in the app)
        if channel == NotificationChannel.IN_APP:
            return True

        # Check for specific consent
        # The most recent answer for this purpose wins, so a later opt-out
        # (granted=False) overrides an earlier opt-in.
        for purpose in (f"{event.value}_{channel.value}", f"notifications_{channel.value}"):
            latest = (
                Consent.objects.filter(patient_id=patient_id, purpose=purpose)
                .filter(models.Q(hospital_id=hospital_id) | models.Q(hospital__isnull=True))
                .order_by("-created_at", "-id")
                .first()
            )
            if latest is not None:
                return latest.granted
        return False

    def send(self, payload: NotificationPayload) -> list[NotificationResult]:
        """
        Send a notification now on every channel in the payload and record
        each attempt.

        Returns:
            List of NotificationResult for each channel attempted.
        """
        results = [self._deliver(payload, channel) for channel in payload.channels]
        self._record(payload, results)
        return results

    def send_channel(self, payload: NotificationPayload, channel: NotificationChannel) -> NotificationResult:
        """Send and record one channel; used by the Celery retry task."""
        return self.send(replace(payload, channels=[channel]))[0]

    def send_async(self, payload: NotificationPayload) -> list[NotificationResult]:
        """
        In-app notifications are written now. External channels that pass
        the consent and configuration checks are queued to Celery after the
        current transaction commits, so a slow or failing provider never
        holds up or breaks the request; the task retries transient failures.
        Channels that fail the checks are recorded as skipped straight away.
        """
        immediate = []
        for channel in payload.channels:
            if channel == NotificationChannel.IN_APP:
                immediate.append(self._deliver(payload, channel))
                continue
            skipped = self._precheck(payload, channel)
            if skipped is not None:
                immediate.append(skipped)
            else:
                self._enqueue(payload, channel)
        self._record(payload, immediate)
        return immediate

    def _enqueue(self, payload: NotificationPayload, channel: NotificationChannel):
        from django.db import transaction

        data = replace(payload, channels=[channel]).to_dict()

        def publish():
            from kombu.exceptions import OperationalError

            from notifications.tasks import send_notification_channel

            try:
                # retry=False: fail fast when the broker is down instead of
                # blocking the request while kombu reconnects.
                send_notification_channel.apply_async(args=[data, channel.value], retry=False)
            except (OperationalError, ConnectionError):
                # Only broker failures fall back; anything else may come after
                # the message was handed to the provider, so resending could
                # notify the patient twice.
                logger.exception("Could not queue %s notification for patient %s; sending now",
                                 channel.value, payload.patient_id)
                self.send_channel(payload, channel)

        transaction.on_commit(publish)

    def _precheck(self, payload: NotificationPayload, channel: NotificationChannel) -> Optional[NotificationResult]:
        """A skip result when the channel must not or cannot be used, else None."""
        if not self.check_consent(payload.patient_id, payload.event, channel, payload.hospital_id):
            logger.info(
                f"Consent not granted for patient {payload.patient_id}, "
                f"event {payload.event.value}, channel {channel.value}"
            )
            return NotificationResult(channel=channel, success=False, error="Consent not granted")

        provider = self._providers.get(channel)
        if not provider:
            logger.warning(f"No provider registered for channel: {channel.value}")
            return NotificationResult(channel=channel, success=False, error="No provider available")

        if not provider.is_configured():
            logger.warning(f"Provider {channel.value} not configured")
            return NotificationResult(channel=channel, success=False, error="Provider not configured")
        return None

    def _deliver(self, payload: NotificationPayload, channel: NotificationChannel) -> NotificationResult:
        skipped = self._precheck(payload, channel)
        if skipped is not None:
            return skipped
        try:
            result = self._providers[channel].send(payload)
        except Exception as e:
            logger.error(f"Notification error via {channel.value}: {e}")
            return NotificationResult(channel=channel, success=False, error=str(e), retryable=True)

        if result.success:
            logger.info(f"Notification sent via {channel.value} to patient {payload.patient_id}")
        else:
            logger.warning(f"Notification failed via {channel.value}: {result.error}")
        return result

    def _record(self, payload: NotificationPayload, results: list[NotificationResult]):
        if not results:
            return
        self._delivery_history.append(DeliveryRecord(payload=payload, results=results))
        self._persist(payload, results)

    def _persist(self, payload, results):
        """Write one NotificationDelivery row per channel attempt; never raises."""
        from notifications.models import NotificationDelivery

        try:
            for result in results:
                if result.success:
                    status = NotificationDelivery.Status.SENT
                elif result.error in ("Consent not granted", "No provider available", "Provider not configured"):
                    status = NotificationDelivery.Status.SKIPPED
                else:
                    status = NotificationDelivery.Status.FAILED
                notification_id = None
                if result.channel == NotificationChannel.IN_APP and result.provider_message_id:
                    notification_id = int(result.provider_message_id)
                NotificationDelivery.objects.create(
                    hospital_id=payload.hospital_id,
                    patient_id=payload.patient_id,
                    notification_id=notification_id,
                    event=payload.event.value,
                    channel=result.channel.value,
                    status=status,
                    error=(result.error or "")[:255],
                    provider_message_id=(result.provider_message_id or "")[:100],
                )
        except Exception:
            logger.exception("Could not record notification delivery")

    def get_delivery_history(
        self,
        patient_id: Optional[int] = None,
        event: Optional[NotificationEvent] = None,
        limit: int = 100,
    ) -> list[DeliveryRecord]:
        """Get delivery history with optional filters."""
        history = self._delivery_history

        if patient_id:
            history = [r for r in history if r.payload.patient_id == patient_id]

        if event:
            history = [r for r in history if r.payload.event == event]

        return history[-limit:]


# Global engine instance
_notification_engine: Optional[NotificationEngine] = None


def get_notification_engine() -> NotificationEngine:
    """Get the global notification engine instance."""
    global _notification_engine
    if _notification_engine is None:
        _notification_engine = NotificationEngine()
    return _notification_engine


def send_notification(
    event: NotificationEvent,
    patient_id: int,
    hospital_id: int,
    title: str,
    message: str,
    metadata: Optional[dict] = None,
    channels: Optional[list[NotificationChannel]] = None,
) -> list[NotificationResult]:
    """
    Convenience function to send a notification.

    Args:
        event: The triggering event
        patient_id: Target patient
        hospital_id: Hospital context
        title: Notification title
        message: Notification message
        metadata: Additional context data
        channels: Channels to use (defaults to IN_APP)

    Returns:
        List of delivery results per channel.
    """
    payload = NotificationPayload(
        event=event,
        patient_id=patient_id,
        hospital_id=hospital_id,
        title=title,
        message=message,
        metadata=metadata or {},
        channels=channels or [NotificationChannel.IN_APP],
    )

    engine = get_notification_engine()
    return engine.send(payload)