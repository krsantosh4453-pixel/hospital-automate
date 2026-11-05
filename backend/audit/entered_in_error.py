"""
Clinical records are never erased. "Removing" one marks it entered in error:
it disappears from every list and lookup, but the row stays, with who marked
it, when and why. The audit log keeps a copy of its values at that moment.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

MIN_REASON_LENGTH = 5


class CurrentManager(models.Manager):
    """Rows not marked entered in error. The default manager, so lists,
    lookups, related managers and validation all skip removed rows."""

    def get_queryset(self):
        return super().get_queryset().filter(entered_in_error_at__isnull=True)


class EnteredInError(models.Model):
    entered_in_error_at = models.DateTimeField(null=True, blank=True, db_index=True)
    entered_in_error_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    entered_in_error_reason = models.TextField(blank=True)

    objects = CurrentManager()
    # Every row, removed ones included: for audit, reports of removals and clean-up scripts.
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def mark_entered_in_error(self, user, reason):
        self.entered_in_error_at = timezone.now()
        self.entered_in_error_by = user if getattr(user, "is_authenticated", False) else None
        self.entered_in_error_reason = reason
        self.save(update_fields=["entered_in_error_at", "entered_in_error_by", "entered_in_error_reason"])


def is_entered_in_error_model(model):
    return issubclass(model, EnteredInError)


def snapshot(instance):
    """Field values of ``instance`` (foreign keys as ids), for the audit log."""
    values = {}
    for field in instance._meta.concrete_fields:
        values[field.attname] = getattr(instance, field.attname)
    return values


def removal_reason(request):
    """The reason sent with a removal; refuses one that is missing or too short."""
    from rest_framework.exceptions import ValidationError

    data = request.data if hasattr(request.data, "get") else {}
    reason = str(data.get("reason") or "").strip()
    if len(reason) < MIN_REASON_LENGTH:
        raise ValidationError(
            {"reason": f"Say why this record was entered in error (at least {MIN_REASON_LENGTH} characters)."}
        )
    return reason
