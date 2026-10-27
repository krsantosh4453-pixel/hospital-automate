from rest_framework.permissions import IsAuthenticated

from .models import Doctor
from .serializers import DoctorSerializer
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsHospitalMember, IsStaffUser

_WRITE_ACTIONS = {"create", "update", "partial_update", "destroy"}


class DoctorViewSet(HospitalScopedViewSet):
    """Every staff member of a hospital can see its doctors (reception books
    appointments against them); only its Admin or Manager edits profiles."""

    queryset = Doctor.objects.select_related("hospital")
    serializer_class = DoctorSerializer

    def get_permissions(self):
        base = [IsAuthenticated(), IsStaffUser(), IsHospitalMember()]
        if getattr(self, "action", None) in _WRITE_ACTIONS:
            return base + [(IsAdmin | IsHospitalManager)()]
        return base

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