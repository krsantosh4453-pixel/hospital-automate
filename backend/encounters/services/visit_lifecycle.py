"""
One place that moves a visit through its consultation, together with its queue token.

BUG-02 (Android E2E 2026-11-19): the Consultation screens (web and mobile)
PATCHed ``Visit.status`` directly, which never touched the queue token or the
appointment. A completed, admitted and discharged patient kept a "Waiting"
token: still in the doctor's and nurse's queues, and the patient app kept
saying "position #2, stay nearby".

Every visit status change now goes through :func:`change_visit_status`, which
moves the visit's open token by the same rules as the queue actions, and
``sync_appointment_status`` keeps the appointment in step:

* Waiting -> In Consultation: the token must already be Called, Acknowledged
  or Ready. A Waiting token is never called automatically (calling is the
  queue's own action), so this is refused until the patient has been called.
* In Consultation -> Completed: the token is completed.
* Waiting -> Cancelled: the token is cancelled.

Asking for the status the visit already has changes nothing (a double click
or a retried request). Every other change is refused: a completed or
cancelled visit is never reopened.
"""

from django.db import models, transaction

from appointments.slots import lock_doctor
from encounters.models import QueueToken, Visit
from encounters.services.appointment_status import sync_appointment_status

Token = QueueToken.Status

WAITING = "Waiting"
IN_CONSULTATION = "In Consultation"
COMPLETED = "Completed"
CANCELLED = "Cancelled"
VISIT_STATUSES = (WAITING, IN_CONSULTATION, COMPLETED, CANCELLED)

# Visit status -> the statuses it may move to.
NEXT_STATUSES = {
    WAITING: (IN_CONSULTATION, CANCELLED),
    IN_CONSULTATION: (COMPLETED,),
    COMPLETED: (),
    CANCELLED: (),
}

# A token still in the queue or with the doctor.
OPEN_TOKEN_STATUSES = (Token.WAITING, Token.CALLED, Token.ACKNOWLEDGED, Token.READY, Token.IN_CONSULTATION)
# A token whose patient has been called and may now be seen.
CALLED_STATUSES = (Token.CALLED, Token.ACKNOWLEDGED, Token.READY)
# A token not yet with the doctor, so it can be cancelled.
CANCELLABLE_STATUSES = (Token.WAITING, Token.CALLED, Token.ACKNOWLEDGED, Token.READY)


class VisitTransitionError(Exception):
    """A refused visit status change. ``flag`` names the reason for the apps."""

    def __init__(self, message, flag):
        super().__init__(message)
        self.message = message
        self.flag = flag

    def as_body(self):
        return {"detail": self.message, self.flag: True}


def change_visit_status(visit_pk, target, after_commit=None):
    """
    Move a visit to ``target`` with its open queue token, in one transaction.

    Locks the doctor rows first (the order Call Next and the token actions
    use), then the visit, then its token, and re-reads both under the lock.
    Returns ``(visit, changed)``; raises :class:`VisitTransitionError`.
    ``after_commit(token)`` runs once the change is committed, for a moved token.
    """
    if target not in VISIT_STATUSES:
        raise VisitTransitionError(f"Unknown visit status {target!r}.", "invalid_status")
    with transaction.atomic():
        visit = Visit.objects.get(pk=visit_pk)
        for doctor_id in _doctor_ids(visit):
            lock_doctor(doctor_id)
        visit = Visit.objects.select_for_update().get(pk=visit_pk)
        if visit.status == target:
            return visit, False
        if target not in NEXT_STATUSES.get(visit.status, ()):
            raise VisitTransitionError(
                f"A visit that is {visit.status} cannot be changed to {target}.",
                "invalid_transition",
            )
        token = (
            QueueToken.objects.select_for_update()
            .filter(visit_id=visit.pk, status__in=OPEN_TOKEN_STATUSES)
            .order_by("-pk")
            .first()
        )
        if token is not None:
            _move_token(token, target)
            sync_appointment_status(token)
            if after_commit is not None:
                transaction.on_commit(lambda: after_commit(token))
        Visit.objects.filter(pk=visit.pk).update(status=target)
        if target == COMPLETED:
            # BUG-07: the consultation fee is charged in the same transaction.
            from billing.charges import capture_consultation

            capture_consultation(visit.pk)
        visit.refresh_from_db()
        return visit, True


def _doctor_ids(visit):
    """The doctors whose queues this visit's change touches, in lock order."""
    ids = set(
        QueueToken.objects.filter(visit_id=visit.pk, status__in=OPEN_TOKEN_STATUSES)
        .values_list("doctor_id", flat=True)
    )
    if visit.doctor_id:
        ids.add(visit.doctor_id)
    return sorted(ids)


def _move_token(token, target):
    if target == IN_CONSULTATION:
        if token.status == Token.WAITING:
            raise VisitTransitionError(
                f"Token #{token.token_number} has not been called yet. Call the patient from the queue first.",
                "patient_not_called",
            )
        if token.status in CALLED_STATUSES:
            serving = (
                QueueToken.objects.filter(
                    hospital_id=token.hospital_id, doctor_id=token.doctor_id, status=Token.IN_CONSULTATION,
                )
                .exclude(pk=token.pk)
                .order_by("token_date", "token_number")
                .first()
            )
            if serving is not None:
                raise VisitTransitionError(
                    f"Token #{serving.token_number} is still in consultation with this doctor. "
                    "Complete it before starting another.",
                    "doctor_busy",
                )
            _save_status(token, Token.IN_CONSULTATION)
        return
    if target == COMPLETED:
        # The visit is In Consultation. Its token normally is too; a token
        # left behind by the old direct PATCH is closed all the same.
        _save_status(token, Token.COMPLETED)
        return
    if target == CANCELLED:
        if token.status not in CANCELLABLE_STATUSES:
            raise VisitTransitionError(
                "The patient is with the doctor. Complete the consultation instead.",
                "invalid_transition",
            )
        _save_status(token, Token.CANCELLED)


def recalculate_queue_of(token):
    """Positions and wait estimates of the rest of a token's queue (pass as ``after_commit``)."""
    from encounters.services.prediction import QueuePredictionService

    QueuePredictionService().recalculate_all_waiting(token.hospital_id, token.doctor_id, token.token_date)


def _save_status(token, status):
    token.status = status
    token.save()  # QueueToken.save stamps consultation_started_at / completed_at.


def close_open_tokens(patient_id, hospital_id, up_to_date, after_commit=None):
    """
    Close a patient's open tokens at a hospital dated ``up_to_date`` or earlier.

    For discharge: a patient leaving the hospital is no longer in any of
    its outpatient queues. A token with the doctor is completed (with its
    visit); one still waiting is cancelled. Later tokens (a follow-up booked
    for another day) are kept. Call inside the caller's transaction.
    Returns the closed tokens.
    """
    closed = []
    tokens = list(
        QueueToken.objects.filter(
            patient_id=patient_id, hospital_id=hospital_id,
            status__in=OPEN_TOKEN_STATUSES, token_date__lte=up_to_date,
        ).values_list("pk", "doctor_id")
    )
    for doctor_id in sorted({doctor_id for _, doctor_id in tokens}):
        lock_doctor(doctor_id)
    for pk, _ in tokens:
        token = QueueToken.objects.select_for_update().get(pk=pk)
        if token.status not in OPEN_TOKEN_STATUSES:
            continue
        if token.status == Token.IN_CONSULTATION:
            _save_status(token, Token.COMPLETED)
        else:
            _save_status(token, Token.CANCELLED)
        sync_appointment_status(token)
        closed.append(token)
        if after_commit is not None:
            transaction.on_commit(lambda token=token: after_commit(token))
    return closed


def stale_tokens(hospital_id=None, first_of_visit=True):
    """
    Open tokens whose visit is already Completed or Cancelled (left by the old direct PATCH).

    ``first_of_visit=True``: only the token the visit was made for, which the
    visit's own outcome closes. A later token on the same visit belongs to
    another appointment that token issuing wrongly put on an old visit; its
    patient may still be waiting, so those (``first_of_visit=False``) are only
    reported, for the desk to cancel or reissue.
    """
    from django.db.models import OuterRef, Subquery

    first_token = QueueToken.objects.filter(visit_id=OuterRef("visit_id")).order_by("pk").values("pk")[:1]
    tokens = (
        QueueToken.objects.filter(status__in=OPEN_TOKEN_STATUSES, visit__status__in=(COMPLETED, CANCELLED))
        .annotate(first_pk=Subquery(first_token))
        .order_by("pk")
    )
    if hospital_id is not None:
        tokens = tokens.filter(hospital_id=hospital_id)
    if first_of_visit:
        return tokens.filter(pk=models.F("first_pk"))
    return tokens.exclude(pk=models.F("first_pk"))


def close_token_of_closed_visit(token_pk):
    """
    Close one stale token to match its visit (inside the caller's transaction).

    Re-read under the doctor and token locks; returns the token, or None when it
    was no longer stale.
    """
    token = QueueToken.objects.filter(pk=token_pk).select_related("visit").first()
    if token is None:
        return None
    lock_doctor(token.doctor_id)
    token = QueueToken.objects.select_for_update().select_related("visit").get(pk=token_pk)
    if token.status not in OPEN_TOKEN_STATUSES or token.visit.status not in (COMPLETED, CANCELLED):
        return None
    _save_status(token, Token.COMPLETED if token.visit.status == COMPLETED else Token.CANCELLED)
    sync_appointment_status(token)
    transaction.on_commit(lambda: recalculate_queue_of(token))
    return token


def cancel_tokens_of_appointment(appointment_id, after_commit=None):
    """
    Cancel the open token of a cancelled appointment (inside the caller's transaction).

    Refused while the patient is with the doctor: that consultation is
    completed, not cancelled.
    """
    tokens = list(
        QueueToken.objects.filter(appointment_id=appointment_id, status__in=OPEN_TOKEN_STATUSES)
        .values_list("pk", "doctor_id")
    )
    for doctor_id in sorted({doctor_id for _, doctor_id in tokens}):
        lock_doctor(doctor_id)
    for pk, _ in tokens:
        token = QueueToken.objects.select_for_update().get(pk=pk)
        if token.status == Token.IN_CONSULTATION:
            raise VisitTransitionError(
                "The patient is with the doctor. Complete the consultation instead of cancelling.",
                "patient_in_consultation",
            )
        if token.status in CANCELLABLE_STATUSES:
            _save_status(token, Token.CANCELLED)
            sync_appointment_status(token)
            if after_commit is not None:
                transaction.on_commit(lambda token=token: after_commit(token))
