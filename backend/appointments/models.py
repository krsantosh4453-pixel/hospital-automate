from django.db import models

from doctors.models import MAX_SLOT_CAPACITY


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
    # Idempotency-Key of the patient's own booking request (blank for staff bookings).
    idempotency_key = models.CharField(max_length=80, blank=True, default="")
    # Place this booking holds in its doctor's slot, 1..doctor.slot_capacity
    # (assigned by appointments/slots.py); only active bookings hold a place.
    slot_seat = models.PositiveSmallIntegerField(default=1)

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
        constraints = [
            # P1-04: one active booking per patient, doctor and slot; a cancelled
            # one can be rebooked. Other patients share the slot only up to the
            # doctor's slot_capacity (constraint below).
            models.UniqueConstraint(
                fields=["patient", "doctor", "appointment_date", "appointment_time"],
                condition=models.Q(status__in=["Scheduled", "Checked In", "In Consultation"]),
                name="appointment_unique_active_slot",
            ),
            # Decision G: no two active bookings share a place in one doctor slot. With the
            # default capacity of 1 every booking takes place 1, so the database alone
            # keeps a slot to one patient whatever code writes the row.
            models.UniqueConstraint(
                fields=["doctor", "appointment_date", "appointment_time", "slot_seat"],
                condition=models.Q(status__in=["Scheduled", "Checked In", "In Consultation"]),
                name="appointment_unique_active_slot_seat",
            ),
            models.CheckConstraint(
                condition=models.Q(slot_seat__gte=1, slot_seat__lte=MAX_SLOT_CAPACITY),
                name="appointment_slot_seat_in_range",
            ),
            # A retried booking request returns its first booking instead of making another.
            models.UniqueConstraint(
                fields=["patient", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="appointment_unique_idempotency_key",
            ),
        ]

    # Statuses that hold a slot (kept equal to the constraint above).
    ACTIVE_STATUSES = ("Scheduled", "Checked In", "In Consultation")


def clashing_booking(patient, doctor, appointment_date, appointment_time, exclude_pk=None):
    """The patient's active booking with this doctor in this slot, if any."""
    clash = Appointment.objects.filter(
        patient=patient, doctor=doctor, appointment_date=appointment_date, appointment_time=appointment_time,
        status__in=Appointment.ACTIVE_STATUSES,
    )
    if exclude_pk is not None:
        clash = clash.exclude(pk=exclude_pk)
    return clash.first()