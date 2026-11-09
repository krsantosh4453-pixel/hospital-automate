from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import record_audit

from .models import Doctor
from .serializers import DoctorSerializer
from users.viewsets import HospitalScopedViewSet
from users.models import StaffRole
from users.permissions import IsAdmin, IsHospitalManager, IsHospitalMember, IsStaffUser, get_user_roles

_WRITE_ACTIONS = {"create", "update", "partial_update", "destroy", "verify_registration"}


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

    def perform_update(self, serializer):
        before = serializer.instance.registration_number
        super().perform_update(serializer)
        doctor = serializer.instance
        if doctor.registration_number != before and doctor.registration_verified_at is not None:
            # A new number has not been checked yet.
            type(doctor).objects.filter(pk=doctor.pk).update(registration_verified_at=None,
                                                              registration_verified_by=None)
            doctor.refresh_from_db()

    @action(detail=True, methods=["post"], url_path="verify-registration")
    def verify_registration(self, request, pk=None):
        """POST {registration_council}: the hospital Admin confirms the doctor's registration was checked."""
        doctor = self.get_object()
        if StaffRole.ADMIN not in get_user_roles(request.user, doctor.hospital_id):
            raise PermissionDenied("Only this hospital's Admin can verify a doctor's registration.")
        if not doctor.registration_number.strip():
            raise ValidationError({"registration_number": "Record the registration number first."})
        doctor.registration_council = str(request.data.get("registration_council") or doctor.registration_council)[:100]
        doctor.registration_verified_at = timezone.now()
        doctor.registration_verified_by = request.user
        doctor.save(update_fields=["registration_council", "registration_verified_at", "registration_verified_by"])
        record_audit(request, "doctors.registration_verified", doctor, hospital=doctor.hospital_id,
                     details={"registration_number": doctor.registration_number,
                              "council": doctor.registration_council})
        return Response(self.get_serializer(doctor).data)
