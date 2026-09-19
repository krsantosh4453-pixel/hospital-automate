from django.db import models


class Notification(models.Model):
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


class Consent(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="consents"
    )
    purpose = models.CharField(max_length=200)
    granted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class OTPVerification(models.Model):
    phone = models.CharField(max_length=15)
    otp = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
