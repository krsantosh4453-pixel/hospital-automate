from rest_framework import viewsets

from .models import Appointment
from .serializers import AppointmentSerializer
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsReceptionist, IsDoctor, IsPatientReadOnly


class AppointmentViewSet(HospitalScopedViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsPatientReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        return queryset