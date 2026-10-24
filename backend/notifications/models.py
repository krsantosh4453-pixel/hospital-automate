from django.db import models


class Notification(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, default="General")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class NotificationDelivery(models.Model):
    """
    One attempt to deliver a notification on one channel. Kept for audit:
    sent, failed (with the provider error) or skipped (e.g. no consent).
    """

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"

    hospital = models.ForeignKey(
        "hospital.Hospital", on_delete=models.CASCADE, null=True, blank=True,
        related_name="notification_deliveries", db_index=True,
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="notification_deliveries",
    )
    notification = models.ForeignKey(
        Notification, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries",
    )
    event = models.CharField(max_length=50, db_index=True)
    channel = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices)
    error = models.CharField(max_length=255, blank=True)
    provider_message_id = models.CharField(max_length=100, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-attempted_at"]
        indexes = [models.Index(fields=["hospital", "attempted_at"]), models.Index(fields=["patient", "attempted_at"])]


class Consent(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="consents"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communication_consents",
        db_index=True,
    )
    purpose = models.CharField(max_length=200)
    granted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class OTPVerification(models.Model):
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    channel = models.CharField(max_length=10, default="sms")
    purpose = models.CharField(max_length=20, default="login")
    otp = models.CharField(max_length=10, blank=True)
    otp_hash = models.CharField(max_length=64, blank=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
