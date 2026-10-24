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
    action = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.action} - {self.model_name}"

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["model_name", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]


class AIInteraction(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_interactions",
        db_index=True
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