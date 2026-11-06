"""
Support services of a hospital (J5, J6, I6). Each record belongs to one
hospital; status changes go through hospital_services/workflows.py, which
checks the order of steps and locks the row whose state it checks.
"""

from django.conf import settings
from django.db import models

USER = settings.AUTH_USER_MODEL


def _by(name):
    return models.ForeignKey(USER, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")


class OperatingTheatre(models.Model):
    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="theatres")
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["hospital", "name"], name="unique_theatre_name")]

    def __str__(self):
        return self.name


class OTBooking(models.Model):
    SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED = "Scheduled", "In progress", "Completed", "Cancelled"
    STATUS_CHOICES = [(s, s) for s in (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="ot_bookings")
    theatre = models.ForeignKey(OperatingTheatre, on_delete=models.PROTECT, related_name="bookings")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="ot_bookings")
    surgeon = models.ForeignKey("doctors.Doctor", on_delete=models.PROTECT, related_name="ot_bookings")
    procedure_name = models.CharField(max_length=200)
    anaesthesia = models.CharField(max_length=40, blank=True)
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=SCHEDULED, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)
    created_by = _by("created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_start"]
        constraints = [models.CheckConstraint(condition=models.Q(scheduled_end__gt=models.F("scheduled_start")),
                                              name="ot_booking_ends_after_start")]


class Ambulance(models.Model):
    AVAILABLE, ON_TRIP, MAINTENANCE = "Available", "On trip", "Maintenance"
    STATUS_CHOICES = [(s, s) for s in (AVAILABLE, ON_TRIP, MAINTENANCE)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="ambulances")
    vehicle_number = models.CharField(max_length=20)
    kind = models.CharField(max_length=10, choices=[("BLS", "Basic life support"), ("ALS", "Advanced life support")],
                            default="BLS")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=AVAILABLE)

    class Meta:
        ordering = ["vehicle_number"]
        constraints = [models.UniqueConstraint(fields=["hospital", "vehicle_number"], name="unique_ambulance_number")]

    def __str__(self):
        return self.vehicle_number


class AmbulanceTrip(models.Model):
    REQUESTED, DISPATCHED, COMPLETED, CANCELLED = "Requested", "Dispatched", "Completed", "Cancelled"
    STATUS_CHOICES = [(s, s) for s in (REQUESTED, DISPATCHED, COMPLETED, CANCELLED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="ambulance_trips")
    ambulance = models.ForeignKey(Ambulance, on_delete=models.PROTECT, null=True, blank=True, related_name="trips")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, null=True, blank=True,
                                related_name="ambulance_trips")
    caller_name = models.CharField(max_length=150)
    caller_phone = models.CharField(max_length=20)
    pickup = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    crew = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=REQUESTED, db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = _by("created_by")

    class Meta:
        ordering = ["-requested_at"]


class MortuaryRecord(models.Model):
    IN_CUSTODY, RELEASED = "In custody", "Released"
    STATUS_CHOICES = [(s, s) for s in (IN_CUSTODY, RELEASED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="mortuary_records")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, null=True, blank=True,
                                related_name="mortuary_records")
    deceased_name = models.CharField(max_length=150)
    time_of_death = models.DateTimeField()
    # As certified by the doctor; never inferred by the software.
    certified_cause = models.CharField(max_length=255, blank=True)
    storage_unit = models.CharField(max_length=40)
    police_case = models.BooleanField(default=False)
    police_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=IN_CUSTODY, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    received_by = _by("received_by")
    released_at = models.DateTimeField(null=True, blank=True)
    released_to_name = models.CharField(max_length=150, blank=True)
    released_to_relation = models.CharField(max_length=60, blank=True)
    released_to_id_last4 = models.CharField(max_length=4, blank=True)
    release_authorised_by = _by("release_authorised_by")

    class Meta:
        ordering = ["-received_at"]


class SterileSet(models.Model):
    """A CSSD instrument set (I6), reprocessed through SterilizationCycle rows."""

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="sterile_sets")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["hospital", "code"], name="unique_sterile_set_code")]


class SterilizationCycle(models.Model):
    STERILE, ISSUED, RETURNED = "Sterile", "Issued", "Returned"
    STATUS_CHOICES = [(s, s) for s in (STERILE, ISSUED, RETURNED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="sterilization_cycles")
    sterile_set = models.ForeignKey(SterileSet, on_delete=models.PROTECT, related_name="cycles")
    method = models.CharField(max_length=20, choices=[("Autoclave", "Autoclave"), ("ETO", "Ethylene oxide"),
                                                      ("Plasma", "Plasma")])
    load_number = models.CharField(max_length=40)
    sterilized_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    indicator_passed = models.BooleanField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STERILE, db_index=True)
    issued_to = models.ForeignKey("hospital.Department", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="+")
    issued_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    recorded_by = _by("recorded_by")

    class Meta:
        ordering = ["-sterilized_at"]
        constraints = [models.CheckConstraint(condition=models.Q(expires_at__gt=models.F("sterilized_at")),
                                              name="sterile_expiry_after_cycle")]


class LaundryBatch(models.Model):
    SENT, RETURNED = "Sent", "Returned"

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="laundry_batches")
    department = models.ForeignKey("hospital.Department", on_delete=models.PROTECT, related_name="+")
    item_type = models.CharField(max_length=60)
    quantity_sent = models.PositiveIntegerField()
    quantity_returned = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=[(SENT, SENT), (RETURNED, RETURNED)], default=SENT)
    sent_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    recorded_by = _by("recorded_by")

    class Meta:
        ordering = ["-sent_at"]
        constraints = [models.CheckConstraint(condition=models.Q(quantity_sent__gt=0), name="laundry_sent_positive")]

    @property
    def shortfall(self):
        return None if self.quantity_returned is None else self.quantity_sent - self.quantity_returned


class LeaveRequest(models.Model):
    """Staff leave (J6, HR): approved by an admin or manager other than the requester."""

    PENDING, APPROVED, REJECTED, CANCELLED = "Pending", "Approved", "Rejected", "Cancelled"
    STATUS_CHOICES = [(s, s) for s in (PENDING, APPROVED, REJECTED, CANCELLED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="leave_requests")
    staff = models.ForeignKey(USER, on_delete=models.PROTECT, related_name="leave_requests")
    kind = models.CharField(max_length=20, choices=[("Casual", "Casual"), ("Sick", "Sick"), ("Earned", "Earned"),
                                                    ("Other", "Other")])
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    decided_by = _by("decided_by")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                              name="leave_ends_after_start")]


class PatientFeedback(models.Model):
    NEW, REVIEWED, CLOSED = "New", "Reviewed", "Closed"
    STATUS_CHOICES = [(s, s) for s in (NEW, REVIEWED, CLOSED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="feedback")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, null=True, blank=True,
                                related_name="feedback")
    department = models.ForeignKey("hospital.Department", on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="+")
    rating = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=30, choices=[(c, c) for c in ("Care", "Cleanliness", "Waiting time",
                                                                          "Staff behaviour", "Billing", "Other")])
    comments = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=NEW, db_index=True)
    response = models.TextField(blank=True)
    recorded_by = _by("recorded_by")
    reviewed_by = _by("reviewed_by")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5),
                                              name="feedback_rating_1_to_5")]


class TextTemplate(models.Model):
    """Reusable text (J6): clinical note, discharge advice, letter or message, with {placeholders}."""

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="text_templates")
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=[(k, k) for k in ("Clinical note", "Discharge advice", "Letter",
                                                                      "Message")])
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = _by("created_by")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "name"]
        constraints = [models.UniqueConstraint(fields=["hospital", "name"], name="unique_template_name")]
