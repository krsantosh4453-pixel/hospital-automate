"""Keep an appointment's and a visit's status in step with their queue token."""

from django.db import transaction

from appointments.models import Appointment
from appointments.slots import SlotFull, take_place
from encounters.models import QueueToken, Visit

Token = QueueToken.Status
Status = Appointment.Status

# Token status -> appointment status. Skipped keeps the appointment as it is,
# because a skipped token can be put back in the queue.
TOKEN_TO_APPOINTMENT = {
    Token.WAITING: Status.CHECKED_IN,
    Token.CALLED: Status.CHECKED_IN,
    Token.ACKNOWLEDGED: Status.CHECKED_IN,
    Token.READY: Status.CHECKED_IN,
    Token.IN_CONSULTATION: Status.IN_CONSULTATION,
    Token.COMPLETED: Status.COMPLETED,
    Token.NO_SHOW: Status.NO_SHOW,
    Token.CANCELLED: Status.CANCELLED,
}

# Token status -> visit status (the one the Consultation screen shows). Earlier
# token steps leave the visit "Waiting".
VISIT_CANCELLED = "Cancelled"
TOKEN_TO_VISIT = {
    Token.IN_CONSULTATION: "In Consultation",
    Token.COMPLETED: "Completed",
    Token.CANCELLED: VISIT_CANCELLED,
}


def sync_appointment_status(token):
    """Set the token's appointment and visit to the matching status (cancelled ones stay cancelled)."""
    visit_target = TOKEN_TO_VISIT.get(token.status)
    if visit_target and token.visit_id:
        (
            Visit.objects.filter(pk=token.visit_id)
            .exclude(status__in=[VISIT_CANCELLED, visit_target])
            .update(status=visit_target)
        )
    target = TOKEN_TO_APPOINTMENT.get(token.status)
    if target is None or token.appointment_id is None:
        return
    if target in Appointment.ACTIVE_STATUSES:
        _set_active_status(token.appointment_id, target)
        return
    (
        Appointment.objects.filter(pk=token.appointment_id)
        .exclude(status__in=[Status.CANCELLED, target])
        .update(status=target)
    )


def _set_active_status(appointment_id, target):
    """
    An active booking holds a place in its doctor's slot (Decision G). A No Show
    or Completed booking whose token is put back in the queue takes a free place
    again; if the slot has filled meanwhile it keeps its status, so the slot is
    never overbooked, and the token is still served from the queue.
    """
    with transaction.atomic():
        appointment = (
            Appointment.objects.filter(pk=appointment_id)
            .exclude(status__in=[Status.CANCELLED, target])
            .first()
        )
        if appointment is None:
            return
        if appointment.status in Appointment.ACTIVE_STATUSES:
            Appointment.objects.filter(pk=appointment.pk).update(status=target)
            return
        try:
            place = take_place(appointment.doctor_id, appointment.appointment_date, appointment.appointment_time,
                               exclude_pk=appointment.pk)
        except SlotFull:
            return
        Appointment.objects.filter(pk=appointment.pk).update(status=target, slot_seat=place)
