from datetime import datetime

from config.hospital_time import hospital_date_range
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from users.viewsets import ReadOnlyHospitalScopedViewSet
from users.permissions import IsAdmin, IsDoctor
from .models import AuditLog, AIInteraction
from .serializers import (
    AuditLogSerializer,
    AIInteractionSerializer,
)


class AuditLogViewSet(ReadOnlyHospitalScopedViewSet):
    """Hospital audit history is admin-read and cannot be edited over the API."""

    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        """Newest first; filter by ?action=, ?model=, ?user= (username) and ?from= / ?to= dates."""
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("action"):
            queryset = queryset.filter(action__icontains=params["action"].strip())
        if params.get("model"):
            queryset = queryset.filter(model_name__icontains=params["model"].strip())
        if params.get("user"):
            queryset = queryset.filter(user__username__icontains=params["user"].strip())
        # Days are the hospital's (IST), not UTC (P1-3).
        first = _parse_date(params["from"], "from") if params.get("from") else None
        last = _parse_date(params["to"], "to") if params.get("to") else None
        queryset = queryset.filter(hospital_date_range("created_at", first, last))
        return queryset.order_by("-created_at", "-id")


def _parse_date(value, name):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({name: "Use the date format YYYY-MM-DD."})


class AIInteractionViewSet(ReadOnlyHospitalScopedViewSet):
    """
    AI interaction history can be read by doctors and admins.
    Records are created by backend workflows, not by API clients.
    """

    queryset = AIInteraction.objects.all()
    serializer_class = AIInteractionSerializer
    permission_classes = [IsAdmin | IsDoctor]
    http_method_names = ["get", "head", "options"]