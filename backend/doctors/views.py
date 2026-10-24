from rest_framework import viewsets

from .models import Doctor
from .serializers import DoctorSerializer
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsDoctor


class DoctorViewSet(HospitalScopedViewSet):
    queryset = Doctor.objects.select_related("hospital")
    serializer_class = DoctorSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        specialization = self.request.query_params.get("specialization")
        if specialization:
            queryset = queryset.filter(specialization=specialization)

        return queryset