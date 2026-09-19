from django.db import models
from django.contrib.auth.models import User


class GoogleAccount(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="google_account"
    )

    patient = models.OneToOneField(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="google_account"
    )

    google_id = models.CharField(
        max_length=255,
        unique=True
    )

    email = models.EmailField()

    name = models.CharField(
        max_length=150,
        blank=True
    )

    picture = models.URLField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.email