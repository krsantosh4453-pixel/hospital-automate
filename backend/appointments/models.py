from django.db import models


class Appointment(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        default="Scheduled"
    )

    reason = models.TextField(blank=True)

    # Appointment-level contact details captured by the booking form.
    # Optional (blank=True) so legacy rows stay valid and unrelated
    # modules are unaffected.
    village = models.CharField(max_length=150, blank=True)
    contact = models.CharField(max_length=15, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.doctor.name}"

    class Meta:
        ordering = ["-appointment_date", "-appointment_time"]