from django.db import models


class Doctor(models.Model):
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
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["hospital", "specialization"]),
            models.Index(fields=["hospital", "department"]),
        ]