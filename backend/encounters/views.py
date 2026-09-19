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


class VisitViewSet(viewsets.ModelViewSet):
    serializer_class = VisitSerializer

    def get_queryset(self):
        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            return Visit.objects.filter(
                hospital_id=hospital_id
            )

        return Visit.objects.all()


class QueueTokenViewSet(viewsets.ModelViewSet):
    serializer_class = QueueTokenSerializer

    def get_queryset(self):
        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            return QueueToken.objects.filter(
                hospital_id=hospital_id
            )

        return QueueToken.objects.all()

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
            appointment = Appointment.objects.get(pk=appointment_id)
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

        serializer = self.get_serializer(token)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _change_status(self, request, new_status):
        token = self.get_object()
        token.status = new_status
        token.save(update_fields=["status"])
        return Response(self.get_serializer(token).data)

    @action(detail=True, methods=["post"], url_path="call")
    def call(self, request, pk=None):
        """Mark a single token as being called (In Consultation)."""
        return self._change_status(request, "In Consultation")

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Mark a token as completed."""
        return self._change_status(request, "Completed")

    @action(detail=True, methods=["post"], url_path="skip")
    def skip(self, request, pk=None):
        """Mark a token as skipped."""
        return self._change_status(request, "Skipped")

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

        base = QueueToken.objects.filter(hospital_id=hospital_id)

        # Complete any token currently being served (preserves the existing
        # Call Next behaviour of moving the current patient out first).
        base.filter(status__iexact="In Consultation").update(
            status="Completed"
        )

        next_token = (
            base.filter(status__iexact="Waiting")
            .order_by("token_date", "token_number")
            .first()
        )

        if next_token is None:
            return Response(
                {"detail": "No waiting patients in the queue."},
                status=status.HTTP_404_NOT_FOUND,
            )

        next_token.status = "In Consultation"
        next_token.save(update_fields=["status"])

        return Response(self.get_serializer(next_token).data)


class DoctorScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorScheduleSerializer

    def get_queryset(self):
        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            return DoctorSchedule.objects.filter(
                doctor__hospital_id=hospital_id
            )

        return DoctorSchedule.objects.all()
