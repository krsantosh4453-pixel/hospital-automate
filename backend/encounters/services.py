from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Visit, QueueToken
from .serializers import QueueTokenSerializer


@transaction.atomic
def issue_queue_token_for_appointment(
    appointment,
    *,
    visit=None,
    visit_type=None,
    chief_complaint=""
):
    """
    Implement the queue token workflow for an appointment:

        Appointment -> (reuse/create) Visit -> QueueToken -> token_number

    Rules:
      * A Visit carries the patient/doctor/hospital context and the Visit is
        a required FK on QueueToken, so it must exist before a token is made.
      * The call is idempotent: if the appointment already has a queue token
        it is returned instead of creating a duplicate.
      * token_number is allocated server-side by QueueTokenSerializer, scoped
        per hospital per day (see serializers.next_token_number).

    Returns a tuple of (queue_token, created: bool).
    """
    if appointment is None:
        raise serializers.ValidationError({
            "appointment": "An appointment is required to issue a token."
        })

    hospital = appointment.hospital
    patient = appointment.patient
    doctor = appointment.doctor

    if hospital is None:
        raise serializers.ValidationError({
            "appointment": "This appointment is not linked to a hospital."
        })

    if patient is None:
        raise serializers.ValidationError({
            "appointment": "This appointment has no patient assigned."
        })

    # QueueToken.doctor is a required FK, so we cannot issue a token for an
    # appointment without a doctor. Report it clearly instead of failing on
    # a database constraint.
    if doctor is None:
        raise serializers.ValidationError({
            "appointment": "Assign a doctor to the appointment before issuing a token."
        })

    # Idempotency: one queue token per appointment.
    existing = QueueToken.objects.filter(appointment=appointment).first()
    if existing is not None:
        return existing, False

    token_date = timezone.localdate()

    # 1) Obtain the Visit ------------------------------------------------
    if visit is None:
        # Prefer an existing, same-day visit for this patient/doctor so we do
        # not create a new visit every time a token is issued.
        visit = (
            Visit.objects
            .filter(
                patient=patient,
                hospital=hospital,
                doctor=doctor,
                visit_date__date=token_date,
            )
            .order_by("-id")
            .first()
        )

    if visit is None:
        visit = Visit.objects.create(
            patient=patient,
            doctor=doctor,
            hospital=hospital,
            visit_type=visit_type or "OPD",
            chief_complaint=chief_complaint or "",
            status="Waiting",
        )

    # 2) Create the QueueToken (token_number allocated in the serializer) --
    serializer = QueueTokenSerializer(data={
        "visit": visit.id,
        "appointment": appointment.id,
        "hospital": hospital.id,
        "patient": patient.id,
        "doctor": doctor.id,
        "status": "Waiting",
        "estimated_wait_minutes": 0,
        "token_date": str(token_date),
    })
    serializer.is_valid(raise_exception=True)
    token = serializer.save()

    return token, True
