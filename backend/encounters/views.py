import logging

from django.db import OperationalError, transaction
from django.db.models import OuterRef, Subquery
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from appointments.models import Appointment
from audit.services import record_audit
from appointments.slots import lock_doctor

from .models import Visit, QueueToken, DoctorSchedule
from .serializers import (
    VisitSerializer,
    QueueTokenSerializer,
    DoctorScheduleSerializer,
)
from .services import issue_queue_token_for_appointment
from .services import visit_lifecycle
from .services.appointment_status import sync_appointment_status
from .services.prediction import QueuePredictionService
from .services.visit_lifecycle import VisitTransitionError, change_visit_status, recalculate_queue_of
from doctors.models import Doctor
from notifications.services import (
    get_notification_engine,
    NotificationEvent,
    NotificationChannel,
    NotificationPayload,
)
from users.care_scope import doctor_hospital_ids, limit_queue_to_department
from users.permissions import get_user_hospital_ids, get_user_roles
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsLabStaff, IsReceptionist, IsDoctor, IsNurse, IsPatientReadOnly, read_only
from config.hospital_time import hospital_today


logger = logging.getLogger(__name__)

# Call Next takes the first of these in queue order (a Called token is called again).
CALLABLE_STATUSES = [QueueToken.Status.WAITING, QueueToken.Status.CALLED]
# Called and not yet in consultation (BUG-011: at most one per doctor).
CALLED_TOKEN_STATUSES = [QueueToken.Status.CALLED, QueueToken.Status.ACKNOWLEDGED, QueueToken.Status.READY]
QUEUE_CHANGE_IN_PROGRESS = "Another queue change was being saved at the same moment. Check the queue, then try again."


class LabStaffVisitLookup(read_only(IsLabStaff)):
    """
    P2-1 (policy decision 2026-11-25): Lab Staff list one patient's visits,
    read-only, to link a lab order to its visit. No browsing of every visit,
    no detail, no writes; the list leaves out clinical text (LAB_LOOKUP_FIELDS).
    """

    def has_permission(self, request, view):
        return (getattr(view, "action", None) == "list" and bool(request.query_params.get("patient"))
                and super().has_permission(request, view))

    def has_object_permission(self, request, view, obj):
        return False


# What Lab Staff see of a visit: enough to pick it, nothing clinical.
LAB_LOOKUP_FIELDS = ("id", "patient", "hospital", "doctor", "doctor_name", "visit_type", "visit_date", "status")
VISIT_ROLES = (IsAdmin, IsHospitalManager, IsReceptionist, IsDoctor, IsNurse)


class VisitViewSet(HospitalScopedViewSet):
    queryset = Visit.objects.select_related("patient", "doctor", "hospital").order_by("-visit_date", "-id")
    serializer_class = VisitSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsNurse | LabStaffVisitLookup]

    def _lab_lookup_only(self):
        """True when the caller reads only through LabStaffVisitLookup (no full visit role)."""
        return not any(role().has_permission(self.request, self) for role in VISIT_ROLES)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if self._lab_lookup_only():
            rows = response.data.get("results") if isinstance(response.data, dict) else response.data
            trimmed = [{key: row.get(key) for key in LAB_LOOKUP_FIELDS} for row in rows]
            if isinstance(response.data, dict):
                response.data["results"] = trimmed
            else:
                response.data = trimmed
        return response

    def get_queryset(self):
        queryset = super().get_queryset().annotate(latest_token_status=Subquery(
            QueueToken.objects.filter(visit=OuterRef("pk")).order_by("-token_date", "-token_number").values("status")[:1]
        ))

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def update(self, request, *args, **kwargs):
        """
        A status change moves the visit's queue token and appointment with it
        (BUG-02), through ``change_visit_status``. Other fields save as before.
        """
        visit = self.get_object()
        target = request.data.get("status")
        if target is None or target == visit.status:
            return super().update(request, *args, **kwargs)
        refusal = self._refuse_status_change(request, visit, target)
        if refusal is not None:
            return refusal
        others = {key: value for key, value in request.data.items() if key != "status"}
        previous = visit.status
        try:
            with transaction.atomic():
                visit, _ = change_visit_status(visit.pk, target, after_commit=recalculate_queue_of)
                if others:
                    serializer = self.get_serializer(visit, data=others, partial=True)
                    serializer.is_valid(raise_exception=True)
                    self.perform_update(serializer)
        except VisitTransitionError as error:
            code = status.HTTP_400_BAD_REQUEST if error.flag == "invalid_status" else status.HTTP_409_CONFLICT
            return Response(error.as_body(), status=code)
        except OperationalError as error:
            if "database is locked" not in str(error):
                raise
            return Response({"detail": QUEUE_CHANGE_IN_PROGRESS}, status=status.HTTP_409_CONFLICT)
        record_audit(request, "encounters.visit.status_changed", visit,
                     details={"from": previous, "to": target})
        return Response(self.get_serializer(Visit.objects.get(pk=visit.pk)).data)

    def _refuse_status_change(self, request, visit, target):
        """Only the visit's doctor (or an Admin) starts or completes its consultation."""
        if target not in (visit_lifecycle.IN_CONSULTATION, visit_lifecycle.COMPLETED):
            return None
        roles = get_user_roles(request.user, visit.hospital_id)
        if "Admin" in roles:
            return None
        is_doctor = "Doctor" in roles
        own_visit = visit.doctor_id is None or Doctor.objects.filter(pk=visit.doctor_id, user=request.user).exists()
        if is_doctor and own_visit:
            return None
        return Response(
            {"detail": "Only the visit's doctor can start or complete the consultation.", "not_visit_doctor": True},
            status=status.HTTP_403_FORBIDDEN,
        )


class QueueTokenViewSet(HospitalScopedViewSet):
    queryset = QueueToken.objects.select_related(
        "visit", "appointment", "hospital", "patient", "doctor"
    ).prefetch_related("visit__patient", "visit__doctor")
    serializer_class = QueueTokenSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsNurse | IsPatientReadOnly]

    _prediction_service = QueuePredictionService()
    _notification_engine = get_notification_engine()

    def get_queryset(self):
        queryset = super().get_queryset()
        # Front-desk staff with a department see that department's queue.
        queryset = limit_queue_to_department(queryset, self.request.user, get_user_hospital_ids(self.request.user))

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        # Additional filters
        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        token_date = self.request.query_params.get("token_date")
        if token_date:
            queryset = queryset.filter(token_date=token_date)

        return queryset

    def _recalculate_estimates(self, hospital_id: int, doctor_id: int, token_date=None):
        """Recalculate wait-time estimates for all waiting tokens for a doctor."""
        self._prediction_service.recalculate_all_waiting(hospital_id, doctor_id, token_date)

    def _send_queue_notification(
        self,
        token: QueueToken,
        event: NotificationEvent,
        title: str,
        message: str,
        extra_channels: list[NotificationChannel] = None,
        metadata: dict = None,
    ):
        """Send notification for a queue event."""
        channels = [NotificationChannel.IN_APP]
        if extra_channels:
            channels.extend(extra_channels)

        # A notification problem must never undo or fail the queue change.
        try:
            self._notification_engine.send_async(NotificationPayload(
                event=event,
                patient_id=token.patient_id,
                hospital_id=token.hospital_id,
                title=title,
                message=message,
                metadata={
                    "token_id": token.id,
                    "token_number": token.token_number,
                    "doctor_id": token.doctor_id,
                    "queue_position": token.queue_position,
                    "estimated_wait_minutes": token.estimated_wait_minutes,
                    **(metadata or {}),
                },
                channels=channels,
            ))
        except Exception:
            logger.exception("Queue notification failed for token %s", token.pk)

    @action(detail=False, methods=["post"], url_path="issue")
    def issue(self, request):
        """
        Issue (or return an existing) queue token for an appointment.

        POST /api/encounters/queue-tokens/issue/
        Body: { "appointment": <id>, "visit_type": "OPD", "chief_complaint": "" }

        Runs the Appointment -> Visit -> QueueToken workflow in one call.
        """
        appointment_id = request.data.get("appointment")

        if not appointment_id:
            return Response(
                {"appointment": "An appointment id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            appointment = Appointment.objects.filter(
                hospital_id__in=self.get_acting_hospital_ids()
            ).get(pk=appointment_id)
        except (Appointment.DoesNotExist, ValueError, TypeError):
            return Response(
                {"appointment": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        token, created = issue_queue_token_for_appointment(
            appointment,
            visit_type=request.data.get("visit_type"),
            chief_complaint=request.data.get("chief_complaint", ""),
        )

        self._prediction_service.update_token_estimate(token)
        self._recalculate_estimates(token.hospital_id, token.doctor_id, token.token_date)
        sync_appointment_status(token)

        if created:
            record_audit(request, "encounters.queue_token.issued", token,
                         details={"token": token.token_number, "appointment": token.appointment_id})
            self._send_queue_notification(
                token,
                NotificationEvent.QUEUE_TOKEN_CREATED,
                "Queue Token Generated",
                f"Your token #{token.token_number} has been generated. "
                f"Estimated wait: {token.estimated_wait_minutes} minutes.",
                extra_channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
            )

        serializer = self.get_serializer(token)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _change_status(self, request, new_status, allowed_from=None, send_notification=True):
        # Hospital and care scope first: a token the caller may not see is a 404
        # before any lock is taken.
        token = self.get_object()
        return self._in_one_transaction(lambda: self._change_status_locked(
            token.pk, token.doctor_id, new_status, allowed_from, send_notification,
        ))

    def _change_status_locked(self, token_pk, doctor_id, new_status, allowed_from, send_notification):
        """A token's status change; the caller wraps it in one transaction."""
        # Same lock order as Call Next: the doctor row, then the token row. The
        # checks below use the token as it is now, not as it was read before.
        lock_doctor(doctor_id)
        token = QueueToken.objects.select_for_update().get(pk=token_pk)
        old_status = token.status

        if allowed_from and old_status not in allowed_from:
            return Response(
                {"detail": f"Invalid transition from {old_status} to {new_status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == QueueToken.Status.CALLED:
            refusal = self._already_called(token)
            if refusal is not None:
                return refusal

        # One open consultation per doctor, the rule Call Next already keeps.
        if new_status == QueueToken.Status.IN_CONSULTATION:
            serving = self._open_consultation(token.hospital_id, token.doctor_id, exclude_pk=token.pk)
            if serving is not None:
                return Response(
                    {"detail": f"Token #{serving.token_number} is still in consultation with this doctor. "
                               "Complete it before starting another."},
                    status=status.HTTP_409_CONFLICT,
                )

        token.status = new_status
        token.save()
        sync_appointment_status(token)

        self._recalculate_estimates(token.hospital_id, token.doctor_id, token.token_date)

        if send_notification:
            # Sent only once the change is committed: a rollback never messages the patient.
            transaction.on_commit(lambda: self._send_status_change_notification(token, old_status, new_status))

        record_audit(self.request, "encounters.queue_token.status_changed", token,
                     details={"from": old_status, "to": new_status})
        return Response(self.get_serializer(token).data)

    def _already_called(self, token):
        """
        BUG-011: one called patient per doctor and day. A 409 while another
        token of that doctor is Called, Acknowledged or Ready; None when free.
        Read under the doctor lock the caller holds.
        """
        if token.doctor_id is None:
            return None
        held = (QueueToken.objects
                .filter(hospital_id=token.hospital_id, doctor_id=token.doctor_id, token_date=token.token_date,
                        status__in=CALLED_TOKEN_STATUSES)
                .exclude(pk=token.pk).order_by("token_number").first())
        if held is None:
            return None
        return Response(
            {"detail": f"Token #{held.token_number} has already been called for this doctor. Start that "
                       "consultation, or mark it skipped or no-show, before calling another patient."},
            status=status.HTTP_409_CONFLICT,
        )

    def _open_consultation(self, hospital_id, doctor_id, exclude_pk=None):
        """The doctor's token now In Consultation, if any. Read it under the doctor lock."""
        serving = QueueToken.objects.filter(
            hospital_id=hospital_id, doctor_id=doctor_id, status=QueueToken.Status.IN_CONSULTATION,
        )
        if exclude_pk is not None:
            serving = serving.exclude(pk=exclude_pk)
        return serving.order_by("token_date", "token_number").first()

    def _in_one_transaction(self, work):
        """Run ``work`` in one transaction and return its response."""
        try:
            with transaction.atomic():
                return work()
        except OperationalError as error:
            if "database is locked" not in str(error):
                raise
            # SQLite only: it has no row locks and refuses a second writer at the
            # same moment. This request was rolled back whole, so nothing changed.
            return Response({"detail": QUEUE_CHANGE_IN_PROGRESS}, status=status.HTTP_409_CONFLICT)

    def _send_status_change_notification(self, token: QueueToken, old_status: str, new_status: str):
        """Send appropriate notification based on status transition."""
        doctor_name = token.doctor.name if token.doctor else "the doctor"
        event_map = {
            QueueToken.Status.CALLED: (
                NotificationEvent.PATIENT_CALLED,
                "You Are Being Called",
                f"Token #{token.token_number}: Please proceed to {doctor_name}'s consultation room.",
                [NotificationChannel.SMS, NotificationChannel.WHATSAPP, NotificationChannel.VOICE],
            ),
            QueueToken.Status.ACKNOWLEDGED: (
                NotificationEvent.PATIENT_ACK_REQUIRED,
                "Acknowledgment Received",
                f"Token #{token.token_number}: Your acknowledgment has been received. Please wait for the doctor.",
                [],
            ),
            QueueToken.Status.READY: (
                NotificationEvent.PATIENT_READY,
                "Patient Ready",
                f"Token #{token.token_number}: Patient is ready for consultation.",
                [],
            ),
            QueueToken.Status.IN_CONSULTATION: (
                NotificationEvent.CONSULTATION_STARTED,
                "Consultation Started",
                f"Token #{token.token_number}: Consultation with {doctor_name} has started.",
                [],
            ),
            QueueToken.Status.COMPLETED: (
                NotificationEvent.CONSULTATION_COMPLETED,
                "Consultation Completed",
                f"Token #{token.token_number}: Your consultation with {doctor_name} is complete.",
                [NotificationChannel.SMS],
            ),
            QueueToken.Status.SKIPPED: (
                NotificationEvent.APPOINTMENT_DELAYED,
                "Token Skipped",
                f"Token #{token.token_number} was skipped. Please contact the reception.",
                [NotificationChannel.SMS],
            ),
            QueueToken.Status.NO_SHOW: (
                NotificationEvent.APPOINTMENT_CANCELLED,
                "No Show Recorded",
                f"Token #{token.token_number} was marked as no-show. Please rebook if needed.",
                [NotificationChannel.SMS],
            ),
            QueueToken.Status.CANCELLED: (
                NotificationEvent.APPOINTMENT_CANCELLED,
                "Appointment Cancelled",
                f"Token #{token.token_number} has been cancelled.",
                [NotificationChannel.SMS],
            ),
        }

        if new_status in event_map:
            event, title, message, extra_channels = event_map[new_status]
            self._send_queue_notification(token, event, title, message, extra_channels)

    @action(detail=True, methods=["post"], url_path="call")
    def call(self, request, pk=None):
        """Mark a waiting token as CALLED."""
        return self._change_status(
            request,
            QueueToken.Status.CALLED,
            allowed_from=[QueueToken.Status.WAITING],
        )

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        """Patient acknowledges the call (moves to ACKNOWLEDGED)."""
        return self._change_status(
            request,
            QueueToken.Status.ACKNOWLEDGED,
            allowed_from=[QueueToken.Status.CALLED],
        )

    @action(detail=True, methods=["post"], url_path="ready")
    def ready(self, request, pk=None):
        """Patient is ready for consultation (moves to READY)."""
        return self._change_status(
            request,
            QueueToken.Status.READY,
            allowed_from=[QueueToken.Status.ACKNOWLEDGED, QueueToken.Status.CALLED],
        )

    @action(detail=True, methods=["post"], url_path="start-consultation")
    def start_consultation(self, request, pk=None):
        """Doctor starts consultation (moves to IN_CONSULTATION)."""
        return self._change_status(
            request,
            QueueToken.Status.IN_CONSULTATION,
            allowed_from=[QueueToken.Status.READY, QueueToken.Status.CALLED, QueueToken.Status.ACKNOWLEDGED],
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Mark a token as completed."""
        return self._change_status(
            request,
            QueueToken.Status.COMPLETED,
            allowed_from=[QueueToken.Status.IN_CONSULTATION],
        )

    @action(detail=True, methods=["post"], url_path="skip")
    def skip(self, request, pk=None):
        """Mark a token as skipped."""
        return self._change_status(
            request,
            QueueToken.Status.SKIPPED,
            allowed_from=[QueueToken.Status.WAITING, QueueToken.Status.CALLED, QueueToken.Status.ACKNOWLEDGED, QueueToken.Status.READY, QueueToken.Status.IN_CONSULTATION],
        )

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None):
        """Mark a token as no-show."""
        return self._change_status(
            request,
            QueueToken.Status.NO_SHOW,
            allowed_from=[QueueToken.Status.WAITING, QueueToken.Status.CALLED, QueueToken.Status.ACKNOWLEDGED, QueueToken.Status.READY],
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel a token."""
        return self._change_status(
            request,
            QueueToken.Status.CANCELLED,
            allowed_from=[QueueToken.Status.WAITING, QueueToken.Status.CALLED, QueueToken.Status.ACKNOWLEDGED, QueueToken.Status.READY],
        )

    @action(detail=True, methods=["post"], url_path="requeue")
    def requeue(self, request, pk=None):
        """Re-queue a skipped or no-show token back to WAITING."""
        token = self.get_object()
        if token.status not in [QueueToken.Status.SKIPPED, QueueToken.Status.NO_SHOW]:
            return Response(
                {"detail": f"Can only requeue Skipped or No Show tokens, not {token.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        previous = token.status
        token.status = QueueToken.Status.WAITING
        token.save()
        record_audit(request, "encounters.queue_token.status_changed", token,
                     details={"from": previous, "to": QueueToken.Status.WAITING})
        self._recalculate_estimates(token.hospital_id, token.doctor_id, token.token_date)

        self._send_queue_notification(
            token,
            NotificationEvent.QUEUE_TOKEN_CREATED,
            "Re-queued",
            f"Token #{token.token_number} has been re-queued. New estimated wait: {token.estimated_wait_minutes} minutes.",
            extra_channels=[NotificationChannel.SMS],
        )

        return Response(self.get_serializer(token).data)

    @action(detail=False, methods=["post"], url_path="call-next")
    def call_next(self, request):
        """
        Call the next waiting token for a hospital.

        POST /api/encounters/queue-tokens/call-next/?hospital=<id>

        The next token is chosen by queue order (token_date, token_number).
        It never completes a consultation: while the next patient's doctor
        still has a token "In Consultation", nothing changes and the answer
        is 409; the doctor completes that one first (decision 2026-11-14).

        Two clicks at once call one patient once: the second is answered 409.
        On PostgreSQL the doctor's row lock makes it wait and then see what the
        first did; SQLite has no row locks and refuses the second writer
        outright ("database is locked"), which is answered the same way.
        """
        hospital_id = request.query_params.get("hospital") or request.data.get(
            "hospital"
        )

        if not hospital_id:
            return Response(
                {"hospital": "A hospital id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not str(hospital_id).isascii() or not str(hospital_id).isdecimal():
            return Response(
                {"hospital": "Use a hospital id (a number)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        hospital_id = int(hospital_id)

        from users.permissions import user_has_hospital_access
        if not user_has_hospital_access(request.user, hospital_id):
            return Response(
                {"detail": "Access denied to this hospital."},
                status=status.HTTP_403_FORBIDDEN,
            )

        base = QueueToken.objects.filter(hospital_id=hospital_id)
        # A Doctor calls only their own patients' tokens; staff with a
        # department only that department's.
        if doctor_hospital_ids(request.user, [hospital_id]):
            base = base.filter(doctor__user=request.user)
        base = limit_queue_to_department(base, request.user, [hospital_id])

        return self._in_one_transaction(lambda: self._call_next_in_transaction(base, hospital_id))

    def _call_next_in_transaction(self, base, hospital_id):
        """Call Next's reads and writes; the caller wraps them in one transaction."""
        candidate = base.filter(status__in=CALLABLE_STATUSES).order_by("token_date", "token_number").first()
        if candidate is None:
            return Response(
                {"detail": "No waiting patients in the queue."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # One Call Next per doctor at a time (PostgreSQL row lock, the same one
        # bookings take). A request that waited here re-reads the token and
        # finds it already called by the one before it.
        lock_doctor(candidate.doctor_id)
        token = QueueToken.objects.select_for_update().get(pk=candidate.pk)
        if token.status != candidate.status:
            return Response(
                {"detail": f"Token #{token.token_number} was just called by another request. "
                           "The queue has changed; check it before calling again."},
                status=status.HTTP_409_CONFLICT,
            )

        # Scoped to that doctor, not to the caller: the front desk is not held
        # up by another doctor's consultation, and nobody's is ever closed here.
        serving = self._open_consultation(hospital_id, token.doctor_id)
        if serving is not None:
            return Response(
                {"detail": f"Token #{serving.token_number} is still in consultation. "
                           "Complete it before calling the next patient."},
                status=status.HTTP_409_CONFLICT,
            )

        if token.status == QueueToken.Status.WAITING:
            refusal = self._already_called(token)
            if refusal is not None:
                return refusal

        previous = token.status
        token.status = QueueToken.Status.CALLED
        token.save()

        self._recalculate_estimates(token.hospital_id, token.doctor_id, token.token_date)

        # Sent only once the call is committed: a rollback never messages the patient.
        transaction.on_commit(
            lambda: self._send_status_change_notification(token, previous, QueueToken.Status.CALLED)
        )

        record_audit(self.request, "encounters.queue_token.status_changed", token,
                     details={"from": previous, "to": QueueToken.Status.CALLED, "via": "call_next"})
        return Response(self.get_serializer(token).data)

    @action(detail=False, methods=["get"], url_path="estimates")
    def estimates(self, request):
        """
        Get wait-time estimates for all waiting tokens for a doctor.

        GET /api/encounters/queue-tokens/estimates/?hospital=<id>&doctor=<id>&date=<YYYY-MM-DD>
        """
        hospital_id = request.query_params.get("hospital")
        doctor_id = request.query_params.get("doctor")
        token_date = request.query_params.get("date")

        if not hospital_id or not doctor_id:
            return Response(
                {"detail": "hospital and doctor query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_date = token_date or hospital_today()

        waiting_statuses = [
            QueueToken.Status.WAITING,
            QueueToken.Status.CALLED,
            QueueToken.Status.ACKNOWLEDGED,
            QueueToken.Status.READY,
        ]

        tokens = QueueToken.objects.filter(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            token_date=token_date,
            status__in=waiting_statuses,
        ).order_by("token_number")

        estimates = []
        for token in tokens:
            estimate = self._prediction_service.estimate_for_token(token)
            estimates.append({
                "token_id": token.id,
                "token_number": token.token_number,
                "patient_name": token.patient_name,
                "queue_position": estimate.queue_position,
                "estimated_wait_minutes": estimate.estimated_wait_minutes,
                "estimated_start_time": estimate.estimated_start_time,
                "confidence": estimate.confidence,
                "method": estimate.method,
            })

        return Response({
            "hospital": hospital_id,
            "doctor": doctor_id,
            "date": token_date,
            "estimates": estimates,
        })


class DoctorScheduleViewSet(HospitalScopedViewSet):
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(doctor__hospital_id=hospital_id)

        return queryset.order_by("doctor_id", "day", "start_time", "id")