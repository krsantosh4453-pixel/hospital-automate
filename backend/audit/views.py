from rest_framework import viewsets
from users.viewsets import ReadOnlyHospitalScopedViewSet
from users.permissions import IsAdmin, IsDoctor
from .models import AuditLog, AIInteraction
from .serializers import (
    AuditLogSerializer,
    AIInteractionSerializer,
)


class AuditLogViewSet(ReadOnlyHospitalScopedViewSet):
    """Hospital audit history is admin-read and cannot be edited over the API."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "head", "options"]


class AIInteractionViewSet(ReadOnlyHospitalScopedViewSet):
    """
    AI interaction history can be read by doctors and admins.
    Records are created by backend workflows, not by API clients.
    """

    queryset = AIInteraction.objects.all()
    serializer_class = AIInteractionSerializer
    permission_classes = [IsAdmin | IsDoctor]
    http_method_names = ["get", "head", "options"]