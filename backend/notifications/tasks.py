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
