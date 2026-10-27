"""Keep an appointment's status in step with its queue token."""

from appointments.models import Appointment
from encounters.models import QueueToken

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


def sync_appointment_status(token):
    """Set the token's appointment to the matching status (cancelled ones stay cancelled)."""
    target = TOKEN_TO_APPOINTMENT.get(token.status)
    if target is None or token.appointment_id is None:
        return
    (
        Appointment.objects.filter(pk=token.appointment_id)
        .exclude(status__in=[Status.CANCELLED, target])
        .update(status=target)
    )
