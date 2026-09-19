from django.db import models


class Doctor(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="doctors",
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)

    # Added to match the Doctor Management UI (form fields, the
    # "Experience" table column and the View modal). Kept blank-safe so
    # existing rows and the Appointments auto-create path keep working.
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

    # The Doctor UI uses "Available" / "On Leave"; the default is aligned
    # to that so new doctors count correctly in the stats cards.
    status = models.CharField(
        max_length=20,
        default="Available"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]