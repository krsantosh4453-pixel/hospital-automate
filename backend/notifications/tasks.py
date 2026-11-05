"""Periodic notification maintenance (scheduled from CELERY_BEAT_SCHEDULE)."""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone


@shared_task
def cleanup_expired_otp():
    """Remove OTP rows that expired more than a day ago."""
    from notifications.models import OTPVerification

    cutoff = timezone.now() - timedelta(days=1)
    deleted, _ = OTPVerification.objects.filter(expires_at__lt=cutoff).delete()
    return deleted


# Transient failures are retried with exponential backoff: 1, 2, 4, 8, 16 min.
NOTIFICATION_MAX_RETRIES = 5
NOTIFICATION_RETRY_BASE_SECONDS = 60


@shared_task(bind=True, max_retries=NOTIFICATION_MAX_RETRIES, acks_late=True, ignore_result=True)
def send_notification_channel(self, payload_data, channel_value):
    """
    Deliver one queued notification on one external channel. Every attempt is
    recorded as a NotificationDelivery row; only failures the provider marks
    retryable are tried again.
    """
    import logging

    from notifications.services import NotificationChannel, NotificationPayload, get_notification_engine

    from notifications.services.voice_fallback import queue_voice_fallback

    payload = NotificationPayload.from_dict(payload_data)
    engine = get_notification_engine()
    result = engine.send_channel(payload, NotificationChannel(channel_value))
    if result.success:
        return True
    if result.retryable and self.request.retries < self.max_retries:
        raise self.retry(countdown=NOTIFICATION_RETRY_BASE_SECONDS * 2 ** self.request.retries)
    if result.retryable:
        # Ids only: the message may contain clinical details.
        logging.getLogger(__name__).error(
            "Giving up on %s notification for patient %s after %s attempts",
            channel_value, payload.patient_id, self.request.retries + 1,
        )
    # K8: the text message finally failed, so try a voice call.
    queue_voice_fallback(engine, payload, [result])
    return False


@shared_task(bind=True, max_retries=None)
def place_voice_call(self, fallback_id):
    """Dial a queued VoiceCallFallback; retried while attempts remain."""
    from notifications.services.voice_fallback import RETRY_DELAY_SECONDS, place_queued_call

    if place_queued_call(fallback_id):
        raise self.retry(countdown=RETRY_DELAY_SECONDS)
