"""Keep an appointment's and a visit's status in step with their queue token."""

from appointments.models import Appointment
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
    (
        Appointment.objects.filter(pk=token.appointment_id)
        .exclude(status__in=[Status.CANCELLED, target])
        .update(status=target)
    )
