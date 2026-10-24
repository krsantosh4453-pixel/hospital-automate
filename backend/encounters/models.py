from django.db import models
from django.utils import timezone


class Visit(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="visits",
        db_index=True
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visits",
        db_index=True
    )

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="visits",
        db_index=True
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
        default="Waiting",
        db_index=True
    )

    visit_date = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.visit_type}"

    class Meta:
        indexes = [
            models.Index(fields=["hospital", "visit_date"]),
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["patient", "visit_date"]),
            models.Index(fields=["doctor", "visit_date"]),
        ]


class QueueToken(models.Model):
    class Status(models.TextChoices):
        WAITING = "Waiting", "Waiting"
        CALLED = "Called", "Called"
        ACKNOWLEDGED = "Acknowledged", "Acknowledged"
        READY = "Ready", "Ready"
        IN_CONSULTATION = "In Consultation", "In Consultation"
        COMPLETED = "Completed", "Completed"
        SKIPPED = "Skipped", "Skipped"
        CANCELLED = "Cancelled", "Cancelled"
        NO_SHOW = "No Show", "No Show"

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="queue_tokens",
        db_index=True
    )

    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        related_name="queue_tokens",
        null=True,
        blank=True,
        db_index=True
    )

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="queue_tokens",
        db_index=True
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="queue_tokens",
        db_index=True
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="queue_tokens",
        db_index=True
    )

    token_number = models.PositiveIntegerField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.WAITING,
        db_index=True
    )

    estimated_wait_minutes = models.PositiveIntegerField(
        default=0
    )

    queue_position = models.PositiveIntegerField(
        default=0
    )

    estimated_start_time = models.DateTimeField(
        null=True,
        blank=True
    )

    last_updated = models.DateTimeField(
        auto_now=True
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True
    )

    ready_at = models.DateTimeField(
        null=True,
        blank=True
    )

    called_at = models.DateTimeField(
        null=True,
        blank=True
    )

    consultation_started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    token_date = models.DateField(
        default=timezone.localdate,
        db_index=True
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
        indexes = [
            models.Index(fields=["hospital", "token_date", "status"]),
            models.Index(fields=["doctor", "token_date", "status"]),
            models.Index(fields=["patient", "token_date"]),
            models.Index(fields=["hospital", "status", "queue_position"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.pk:
            old = QueueToken.objects.get(pk=self.pk)
            if not self._is_valid_transition(old.status, self.status):
                raise ValidationError({
                    "status": f"Invalid transition from {old.status} to {self.status}"
                })

    def _is_valid_transition(self, from_status, to_status):
        valid_transitions = {
            self.Status.WAITING: [self.Status.CALLED, self.Status.SKIPPED, self.Status.CANCELLED, self.Status.NO_SHOW],
            self.Status.CALLED: [self.Status.ACKNOWLEDGED, self.Status.READY, self.Status.IN_CONSULTATION, self.Status.SKIPPED, self.Status.NO_SHOW, self.Status.WAITING],
            self.Status.ACKNOWLEDGED: [self.Status.READY, self.Status.IN_CONSULTATION, self.Status.NO_SHOW, self.Status.CALLED],
            self.Status.READY: [self.Status.IN_CONSULTATION, self.Status.NO_SHOW, self.Status.CALLED],
            self.Status.IN_CONSULTATION: [self.Status.COMPLETED, self.Status.SKIPPED],
            self.Status.COMPLETED: [],
            self.Status.SKIPPED: [self.Status.WAITING],
            self.Status.CANCELLED: [],
            self.Status.NO_SHOW: [self.Status.WAITING],
        }
        return to_status in valid_transitions.get(from_status, [])

    def save(self, *args, **kwargs):
        from django.utils import timezone
        now = timezone.now()
        if self.pk:
            old = QueueToken.objects.get(pk=self.pk)
            if old.status != self.status:
                if self.status == self.Status.CALLED and not self.called_at:
                    self.called_at = now
                elif self.status == self.Status.ACKNOWLEDGED and not self.acknowledged_at:
                    self.acknowledged_at = now
                elif self.status == self.Status.READY and not self.ready_at:
                    self.ready_at = now
                elif self.status == self.Status.IN_CONSULTATION and not self.consultation_started_at:
                    self.consultation_started_at = now
                elif self.status == self.Status.COMPLETED and not self.completed_at:
                    self.completed_at = now
        super().save(*args, **kwargs)


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