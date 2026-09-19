from django.db import models
from django.utils import timezone


class Visit(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="visits"
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visits"
    )

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="visits"
    )

    visit_type = models.CharField(
        max_length=50,
        default="OPD"
    )

    chief_complaint = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=30,
        default="Waiting"
    )

    visit_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.visit_type}"


class QueueToken(models.Model):
    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="queue_tokens"
    )

    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        related_name="queue_tokens",
        null=True,
        blank=True
    )

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="queue_tokens"
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="queue_tokens"
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="queue_tokens"
    )

    token_number = models.PositiveIntegerField()

    status = models.CharField(
        max_length=30,
        default="Waiting"
    )

    estimated_wait_minutes = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Calendar day this token belongs to. Combined with the hospital it
    # scopes the token-number sequence (one sequence per hospital per day)
    # and lets the database enforce uniqueness.
    token_date = models.DateField(
        default=timezone.localdate
    )

    def __str__(self):
        return f"Token #{self.token_number}"

    class Meta:
        ordering = ["token_date", "token_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "token_date", "token_number"],
                name="unique_queue_token_per_hospital_day",
            )
        ]


class DoctorSchedule(models.Model):
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="schedules"
    )

    day = models.CharField(
        max_length=20
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_available = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.doctor.name} - {self.day}"