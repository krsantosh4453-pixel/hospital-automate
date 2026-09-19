from rest_framework import viewsets

from .models import EmergencyVisit
from .serializers import EmergencyVisitSerializer


class EmergencyVisitViewSet(viewsets.ModelViewSet):
    queryset = EmergencyVisit.objects.all()
    serializer_class = EmergencyVisitSerializer
