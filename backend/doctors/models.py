from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Decision G (2026-11-09): one patient per appointment slot unless a hospital
# raises a doctor's capacity for group or shared consultations.
DEFAULT_SLOT_CAPACITY = 1
MAX_SLOT_CAPACITY = 20


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
    # Medical council registration number: printed on prescriptions and the
    # Schedule H1 register (P1-10).
    registration_number = models.CharField(max_length=50, blank=True, default="")
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
    # Patients one appointment slot may hold (appointments/slots.py).
    slot_capacity = models.PositiveSmallIntegerField(
        default=DEFAULT_SLOT_CAPACITY,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_SLOT_CAPACITY)],
        help_text=f"Patients per appointment slot (1–{MAX_SLOT_CAPACITY}). Keep 1 unless the hospital runs group consultations.",
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
            models.CheckConstraint(
                condition=models.Q(slot_capacity__gte=1, slot_capacity__lte=MAX_SLOT_CAPACITY),
                name="doctor_slot_capacity_in_range",
            ),
        ]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["hospital", "specialization"]),
            models.Index(fields=["hospital", "department"]),
        ]