import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from appointments.models import Appointment

from .models import Visit, QueueToken, DoctorSchedule
from .serializers import (
    VisitSerializer,
    QueueTokenSerializer,
    DoctorScheduleSerializer,
)
from .services import issue_queue_token_for_appointment
from .services.prediction import QueuePredictionService
from notifications.services import (
    get_notification_engine,
    NotificationEvent,
    NotificationChannel,
    NotificationPayload,
)
from users.care_scope import doctor_hospital_ids, limit_queue_to_department
from users.permissions import get_user_hospital_ids
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsReceptionist, IsDoctor, IsNurse, IsPatientReadOnly


logger = logging.getLogger(__name__)


class VisitViewSet(HospitalScopedViewSet):
    queryset = Visit.objects.select_related("patient", "doctor", "hospital")
    serializer_class = VisitSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsNurse]

    def get_queryset(self):
        queryset = super().get_queryset()

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
            self._notification_engine.send(NotificationPayload(
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

        if created:
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
        token = self.get_object()
        old_status = token.status

        if allowed_from and old_status not in allowed_from:
            return Response(
                {"detail": f"Invalid transition from {old_status} to {new_status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token.status = new_status
        token.save()

        self._recalculate_estimates(token.hospital_id, token.doctor_id, token.token_date)

        if send_notification:
            self._send_status_change_notification(token, old_status, new_status)

        return Response(self.get_serializer(token).data)

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
        token.status = QueueToken.Status.WAITING
        token.save()
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

        If another token is currently "In Consultation" it is completed
        before the next waiting token is called. The next token is chosen by
        queue order (token_date, token_number).
        """
        hospital_id = request.query_params.get("hospital") or request.data.get(
            "hospital"
        )

        if not hospital_id:
            return Response(
                {"hospital": "A hospital id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from users.permissions import user_has_hospital_access
        if not user_has_hospital_access(request.user, int(hospital_id)):
            return Response(
                {"detail": "Access denied to this hospital."},
                status=status.HTTP_403_FORBIDDEN,
            )

        base = QueueToken.objects.filter(hospital_id=hospital_id)
        # A Doctor calls and completes only their own patients' tokens; staff
        # with a department only that department's.
        if doctor_hospital_ids(request.user, [int(hospital_id)]):
            base = base.filter(doctor__user=request.user)
        base = limit_queue_to_department(base, request.user, [int(hospital_id)])

        base.filter(status__iexact="In Consultation").update(
            status="Completed"
        )

        next_token = (
            base.filter(status__in=[QueueToken.Status.WAITING, QueueToken.Status.CALLED])
            .order_by("token_date", "token_number")
            .first()
        )

        if next_token is None:
            return Response(
                {"detail": "No waiting patients in the queue."},
                status=status.HTTP_404_NOT_FOUND,
            )

        next_token.status = QueueToken.Status.CALLED
        next_token.save()

        self._recalculate_estimates(next_token.hospital_id, next_token.doctor_id, next_token.token_date)

        self._send_status_change_notification(next_token, QueueToken.Status.WAITING, QueueToken.Status.CALLED)

        return Response(self.get_serializer(next_token).data)

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

        from django.utils import timezone
        token_date = token_date or timezone.localdate()

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

        return queryset