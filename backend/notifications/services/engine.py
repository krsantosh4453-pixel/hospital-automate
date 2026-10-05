"""
Notification Engine

Orchestrates notification delivery across multiple providers.
Handles consent checking, channel selection, and delivery tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import logging

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
        self._delivery_history: list[DeliveryRecord] = []

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

    def check_consent(self, patient_id: int, event: NotificationEvent, channel: NotificationChannel) -> bool:
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
        purpose = f"{event.value}_{channel.value}"
        consent = Consent.objects.filter(
            patient_id=patient_id,
            purpose=purpose,
            granted=True
        ).first()

        if consent:
            return True

        # Check for general channel consent
        general_consent = Consent.objects.filter(
            patient_id=patient_id,
            purpose=f"notifications_{channel.value}",
            granted=True
        ).first()

        return general_consent is not None

    def send(self, payload: NotificationPayload) -> list[NotificationResult]:
        """
        Send a notification via the specified channels.

        Args:
            payload: Notification payload with event, patient, and channels.

        Returns:
            List of NotificationResult for each channel attempted.
        """
        results = []

        for channel in payload.channels:
            # Check consent
            if not self.check_consent(payload.patient_id, payload.event, channel):
                logger.info(
                    f"Consent not granted for patient {payload.patient_id}, "
                    f"event {payload.event.value}, channel {channel.value}"
                )
                results.append(NotificationResult(
                    channel=channel,
                    success=False,
                    error="Consent not granted",
                ))
                continue

            provider = self._providers.get(channel)
            if not provider:
                logger.warning(f"No provider registered for channel: {channel.value}")
                results.append(NotificationResult(
                    channel=channel,
                    success=False,
                    error="No provider available",
                ))
                continue

            if not provider.is_configured():
                logger.warning(f"Provider {channel.value} not configured")
                results.append(NotificationResult(
                    channel=channel,
                    success=False,
                    error="Provider not configured",
                ))
                continue

            try:
                result = provider.send(payload)
                results.append(result)

                if result.success:
                    logger.info(f"Notification sent via {channel.value} to patient {payload.patient_id}")
                else:
                    logger.warning(f"Notification failed via {channel.value}: {result.error}")

            except Exception as e:
                logger.error(f"Notification error via {channel.value}: {e}")
                results.append(NotificationResult(
                    channel=channel,
                    success=False,
                    error=str(e),
                ))

        # Record delivery attempt
        record = DeliveryRecord(payload=payload, results=results)
        self._delivery_history.append(record)

        return results

    def send_async(self, payload: NotificationPayload):
        """
        Send notification asynchronously (placeholder for Celery/task queue integration).

        In production, this would enqueue a task to a message broker.
        """
        # TODO: Implement with Celery or similar
        # from notifications.tasks import send_notification_task
        # send_notification_task.delay(payload.__dict__)
        logger.info(f"Async notification queued for patient {payload.patient_id}")
        return self.send(payload)

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