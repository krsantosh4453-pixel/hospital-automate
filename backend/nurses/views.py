from rest_framework import viewsets
from .models import Nurse
from .serializers import NurseSerializer


class NurseViewSet(viewsets.ModelViewSet):
    queryset = Nurse.objects.all()
    serializer_class = NurseSerializer