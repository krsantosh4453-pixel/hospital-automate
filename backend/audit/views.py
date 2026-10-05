from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsAdmin, IsDoctor
from .models import AuditLog, AIInteraction
from .serializers import (
    AuditLogSerializer,
    AIInteractionSerializer,
)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Hospital audit history is admin-read and cannot be edited over the API."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ["get", "head", "options"]


class AIInteractionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    AI interaction history can be read by doctors and admins.
    Records are created by backend workflows, not by API clients.
    """

    queryset = AIInteraction.objects.all()
    serializer_class = AIInteractionSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsDoctor]
    http_method_names = ["get", "head", "options"]
