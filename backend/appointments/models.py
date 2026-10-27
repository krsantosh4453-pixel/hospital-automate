from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        # Scheduled until a queue token is issued; the server then keeps it in
        # step with the token (encounters/services/appointment_status.py).
        SCHEDULED = "Scheduled", "Scheduled"
        CHECKED_IN = "Checked In", "Checked In"
        IN_CONSULTATION = "In Consultation", "In Consultation"
        COMPLETED = "Completed", "Completed"
        CANCELLED = "Cancelled", "Cancelled"
        NO_SHOW = "No Show", "No Show"

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True,
        db_index=True
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="appointments",
        db_index=True
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="appointments",
        db_index=True
    )

    appointment_date = models.DateField(db_index=True)
    appointment_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True
    )

    reason = models.TextField(blank=True)

    # Appointment-level contact details captured by the booking form.
    # Optional (blank=True) so legacy rows stay valid and unrelated
    # modules are unaffected.
    village = models.CharField(max_length=150, blank=True)
    contact = models.CharField(max_length=15, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.patient.name} - {self.doctor.name}"

    class Meta:
        ordering = ["-appointment_date", "-appointment_time"]
        indexes = [
            models.Index(fields=["hospital", "appointment_date"]),
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["doctor", "appointment_date"]),
            models.Index(fields=["patient", "appointment_date"]),
            models.Index(fields=["hospital", "doctor", "appointment_date"]),
        ]