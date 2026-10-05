from rest_framework import viewsets

from .models import Notification, Consent, OTPVerification
from .serializers import (
    NotificationSerializer,
    ConsentSerializer,
    OTPVerificationSerializer,
)
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsReceptionist, IsDoctor, IsNurse


class NotificationViewSet(HospitalScopedViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsNurse]

    def get_queryset(self):
        qs = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        return qs


class ConsentViewSet(HospitalScopedViewSet):
    serializer_class = ConsentSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsNurse]

    def get_queryset(self):
        qs = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        return qs


class OTPVerificationViewSet(HospitalScopedViewSet):
    serializer_class = OTPVerificationSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        return qs
