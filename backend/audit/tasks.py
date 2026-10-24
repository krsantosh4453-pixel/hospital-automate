"""Periodic audit maintenance (scheduled from CELERY_BEAT_SCHEDULE)."""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone


@shared_task
def cleanup_old_audit_logs():
    """
    Delete audit rows older than AUDIT_LOG_RETENTION_DAYS. Retention defaults
    to 0 (keep forever); clinical audit trails usually have legal retention
    periods, so a hospital must choose this value deliberately.
    """
    from audit.models import AuditLog

    days = int(getattr(settings, "AUDIT_LOG_RETENTION_DAYS", 0) or 0)
    if days <= 0:
        return 0
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
