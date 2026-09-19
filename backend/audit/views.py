from rest_framework import viewsets

from .models import AuditLog, AIInteraction
from .serializers import (
    AuditLogSerializer,
    AIInteractionSerializer,
)


class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer


class AIInteractionViewSet(viewsets.ModelViewSet):
    queryset = AIInteraction.objects.all()
    serializer_class = AIInteractionSerializer
