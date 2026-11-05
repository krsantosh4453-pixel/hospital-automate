"""
Status changes for hospital services. Each function locks the row whose
state it checks, so two people cannot dispatch one ambulance, double-book a
theatre, release a body twice or issue the same sterile set twice.
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Ambulance,
    AmbulanceTrip,
    LaundryBatch,
    LeaveRequest,
    MortuaryRecord,
    OperatingTheatre,
    OTBooking,
    PatientFeedback,
    SterilizationCycle,
)


def _fail(field, message):
    raise serializers.ValidationError({field: message})


def _locked(model, obj):
    return model.objects.select_for_update().get(pk=obj.pk)


def _user(user):
    return user if getattr(user, "is_authenticated", False) else None


# Operation theatre (J5)

def check_theatre_free(theatre, start, end, exclude=None):
    """Refuse a booking that overlaps another live booking of the same theatre. Caller holds the theatre lock."""
    clash = OTBooking.objects.filter(theatre=theatre, scheduled_start__lt=end, scheduled_end__gt=start).exclude(
        status__in=(OTBooking.CANCELLED, OTBooking.COMPLETED))
    if exclude is not None:
        clash = clash.exclude(pk=exclude.pk)
    first = clash.order_by("scheduled_start").first()
    if first:
        _fail("scheduled_start", f"{theatre.name} is booked from {timezone.localtime(first.scheduled_start):%d %b %H:%M} "
                                 f"to {timezone.localtime(first.scheduled_end):%H:%M}.")


@transaction.atomic
def book_theatre(serializer, **extra):
    data = serializer.validated_data
    theatre = _locked(OperatingTheatre, data["theatre"])
    if not theatre.is_active:
        _fail("theatre", "This theatre is not in use.")
    check_theatre_free(theatre, data["scheduled_start"], data["scheduled_end"])
    return serializer.save(**extra)


@transaction.atomic
def move_booking(booking, verb, user=None, reason=""):
    booking = _locked(OTBooking, booking)
    now = timezone.now()
    if verb == "start":
        if booking.status != OTBooking.SCHEDULED:
            _fail("status", f"This booking is {booking.status.lower()}.")
        booking.status, booking.started_at = OTBooking.IN_PROGRESS, now
    elif verb == "complete":
        if booking.status != OTBooking.IN_PROGRESS:
            _fail("status", "Only a case in progress can be completed.")
        booking.status, booking.ended_at = OTBooking.COMPLETED, now
    elif verb == "cancel":
        if booking.status != OTBooking.SCHEDULED:
            _fail("status", "Only a scheduled case can be cancelled.")
        if not (reason or "").strip():
            _fail("reason", "A cancellation reason is required.")
        booking.status, booking.cancel_reason = OTBooking.CANCELLED, reason.strip()[:255]
    booking.save()
    return booking


# Ambulance (J5)

@transaction.atomic
def dispatch_trip(trip, ambulance, crew=""):
    trip = _locked(AmbulanceTrip, trip)
    ambulance = _locked(Ambulance, ambulance)
    if trip.status != AmbulanceTrip.REQUESTED:
        _fail("status", f"This trip is {trip.status.lower()}.")
    if ambulance.hospital_id != trip.hospital_id:
        _fail("ambulance", "Ambulance of another hospital.")
    if ambulance.status != Ambulance.AVAILABLE:
        _fail("ambulance", f"{ambulance.vehicle_number} is {ambulance.status.lower()}.")
    ambulance.status = Ambulance.ON_TRIP
    ambulance.save(update_fields=["status"])
    trip.ambulance, trip.crew, trip.status, trip.dispatched_at = ambulance, (crew or "")[:200], AmbulanceTrip.DISPATCHED, timezone.now()
    trip.save()
    return trip


@transaction.atomic
def close_trip(trip, verb):
    trip = _locked(AmbulanceTrip, trip)
    if verb == "complete" and trip.status != AmbulanceTrip.DISPATCHED:
        _fail("status", "Only a dispatched trip can be completed.")
    if verb == "cancel" and trip.status not in (AmbulanceTrip.REQUESTED, AmbulanceTrip.DISPATCHED):
        _fail("status", f"This trip is {trip.status.lower()}.")
    if trip.ambulance_id:
        Ambulance.objects.filter(pk=trip.ambulance_id, status=Ambulance.ON_TRIP).update(status=Ambulance.AVAILABLE)
    trip.status = AmbulanceTrip.COMPLETED if verb == "complete" else AmbulanceTrip.CANCELLED
    trip.completed_at = timezone.now()
    trip.save()
    return trip


# Mortuary (J5)

@transaction.atomic
def release_body(record, user, name, relation, id_last4, police_reference=""):
    record = _locked(MortuaryRecord, record)
    if record.status != MortuaryRecord.IN_CUSTODY:
        _fail("status", "This body has already been released.")
    if not (name or "").strip() or not (relation or "").strip():
        _fail("released_to_name", "Name and relation of the person receiving the body are required.")
    if not (len(str(id_last4 or "")) == 4 and str(id_last4).isdigit()):
        _fail("released_to_id_last4", "Last 4 digits of the receiver's ID are required.")
    reference = (police_reference or record.police_reference or "").strip()
    if record.police_case and not reference:
        _fail("police_reference", "A medico-legal case needs the police clearance reference before release.")
    record.status, record.released_at = MortuaryRecord.RELEASED, timezone.now()
    record.released_to_name, record.released_to_relation = name.strip()[:150], relation.strip()[:60]
    record.released_to_id_last4, record.police_reference = str(id_last4), reference[:100]
    record.release_authorised_by = _user(user)
    record.save()
    return record


# CSSD (I6)

@transaction.atomic
def issue_set(cycle, department):
    cycle = _locked(SterilizationCycle, cycle)
    if cycle.status != SterilizationCycle.STERILE:
        _fail("status", "Only a sterile set waiting on the shelf can be issued.")
    if not cycle.indicator_passed:
        _fail("status", "The sterilization indicator failed; reprocess this set.")
    if cycle.expires_at <= timezone.now():
        _fail("status", "Sterility has expired; reprocess this set.")
    if department.hospital_id != cycle.hospital_id:
        _fail("issued_to", "Department of another hospital.")
    cycle.status, cycle.issued_to, cycle.issued_at = SterilizationCycle.ISSUED, department, timezone.now()
    cycle.save()
    return cycle


@transaction.atomic
def return_set(cycle):
    cycle = _locked(SterilizationCycle, cycle)
    if cycle.status != SterilizationCycle.ISSUED:
        _fail("status", "Only an issued set can come back.")
    cycle.status, cycle.returned_at = SterilizationCycle.RETURNED, timezone.now()
    cycle.save()
    return cycle


def check_new_cycle(sterile_set):
    """A set is reprocessed only when no earlier cycle of it is sterile or out on a ward."""
    if SterilizationCycle.objects.filter(sterile_set=sterile_set, status__in=(
            SterilizationCycle.STERILE, SterilizationCycle.ISSUED)).exists():
        _fail("sterile_set", "This set already has a sterile or issued cycle.")


# Laundry (I6)

@transaction.atomic
def laundry_returned(batch, quantity, note=""):
    batch = _locked(LaundryBatch, batch)
    if batch.status != LaundryBatch.SENT:
        _fail("status", "This batch has already come back.")
    if quantity is None or int(quantity) < 0 or int(quantity) > batch.quantity_sent:
        _fail("quantity_returned", f"Between 0 and {batch.quantity_sent} can come back.")
    batch.quantity_returned, batch.status, batch.returned_at = int(quantity), LaundryBatch.RETURNED, timezone.now()
    if note:
        batch.note = note.strip()[:255]
    batch.save()
    return batch


# Leave (J6)

def check_leave_overlap(staff, hospital_id, start, end):
    if LeaveRequest.objects.filter(staff=staff, hospital_id=hospital_id, start_date__lte=end, end_date__gte=start,
                                   status__in=(LeaveRequest.PENDING, LeaveRequest.APPROVED)).exists():
        _fail("start_date", "You already have leave pending or approved on these dates.")


@transaction.atomic
def decide_leave(request_row, user, approve, note=""):
    row = _locked(LeaveRequest, request_row)
    if row.status != LeaveRequest.PENDING:
        _fail("status", f"This request is {row.status.lower()}.")
    if row.staff_id == getattr(user, "pk", None):
        _fail("status", "Someone else must decide your own leave.")
    if not approve and not (note or "").strip():
        _fail("note", "Say why the leave is refused.")
    row.status = LeaveRequest.APPROVED if approve else LeaveRequest.REJECTED
    row.decided_by, row.decided_at, row.decision_note = _user(user), timezone.now(), (note or "").strip()[:255]
    row.save()
    return row


# Feedback (J6)

@transaction.atomic
def review_feedback(feedback, user, response, close):
    row = _locked(PatientFeedback, feedback)
    if row.status == PatientFeedback.CLOSED:
        _fail("status", "This feedback is closed.")
    if not (response or "").strip():
        _fail("response", "Write the response or action taken.")
    row.response, row.reviewed_by = response.strip(), _user(user)
    row.status = PatientFeedback.CLOSED if close else PatientFeedback.REVIEWED
    row.save()
    return row
