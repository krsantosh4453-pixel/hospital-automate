from django.conf import settings
from django.db import models


class Doctor(models.Model):
    # The staff login of this doctor. Needed to record who approved
    # clinical documentation (e.g. AI drafts); null for unlinked profiles.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctor_profiles",
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="doctors",
        null=True,
        blank=True,
        db_index=True
    )

    name = models.CharField(max_length=100, db_index=True)
    specialization = models.CharField(max_length=100, db_index=True)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=15)
    department = models.ForeignKey(
        "hospital.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctors",
        db_index=True
    )
    experience = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )
    availability = models.CharField(
        max_length=120,
        blank=True,
        default=""
    )
    status = models.CharField(
        max_length=20,
        default="Available",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "hospital"],
                condition=models.Q(user__isnull=False),
                name="doctor_unique_user_per_hospital",
            ),
        ]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["hospital", "specialization"]),
            models.Index(fields=["hospital", "department"]),
        ]