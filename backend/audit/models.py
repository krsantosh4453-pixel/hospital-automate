from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
    )
    action = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.action} - {self.model_name}"

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["model_name", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["hospital", "created_at"]),
        ]
        ordering = ["-created_at"]


class AIInteraction(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_interactions",
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_interactions",
        db_index=True,
    )
    input_text = models.TextField()
    ai_output = models.TextField()
    status = models.CharField(max_length=30, default="Draft", db_index=True)
    reviewed_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        ordering = ["-created_at"]

class BreakGlassQuerySet(models.QuerySet):
    def active(self):
        from django.utils import timezone

        return self.filter(ended_at__isnull=True, expires_at__gt=timezone.now())


class BreakGlassAccess(models.Model):
    """
    Emergency access by a Doctor or Nurse to a patient outside their care.
    It needs a written reason, lapses on its own, is fully audited and waits
    for review by an admin or hospital manager.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="break_glass_grants")
    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="break_glass_grants")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="break_glass_grants")
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="break_glass_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    objects = BreakGlassQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "patient", "expires_at"]),
            models.Index(fields=["hospital", "created_at"]),
        ]

    def __str__(self):
        return f"Break-glass {self.user_id} -> patient {self.patient_id}"
