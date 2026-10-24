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
