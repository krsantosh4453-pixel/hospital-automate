from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from audit.services import record_audit
from users.permissions import (
    IsStaffUser,
    IsAdmin,
    IsHospitalManager,
    IsHospitalMember,
    get_user_hospital_ids,
    get_user_roles,
)
from users.viewsets import HospitalScopedViewSet
from users.models import StaffRole
from .models import Hospital, Department, Ward, Room, Bed
from .serializers import (
    HospitalSerializer,
    DepartmentSerializer,
    WardSerializer,
    RoomSerializer,
    BedSerializer,
)

_WRITE_ACTIONS = {"create", "update", "partial_update", "destroy"}


class HospitalViewSet(viewsets.ModelViewSet):
    """
    Staff see the hospitals they belong to. Creating or deleting a hospital
    is a platform (superuser) action; a hospital's Admin or Manager may edit
    its configuration.
    """

    serializer_class = HospitalSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Hospital.objects.all().order_by("name")
        return Hospital.objects.filter(id__in=get_user_hospital_ids(self.request.user)).order_by("name")

    def _require_platform_admin(self):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only a platform administrator can do this.")

    def perform_create(self, serializer):
        self._require_platform_admin()
        hospital = serializer.save()
        record_audit(self.request, "hospital.create", hospital, hospital=hospital)

    def perform_update(self, serializer):
        hospital = serializer.instance
        roles = get_user_roles(self.request.user, hospital.id)
        if not self.request.user.is_superuser and not (
            StaffRole.ADMIN in roles or StaffRole.HOSPITAL_MANAGER in roles
        ):
            raise PermissionDenied("Only this hospital's Admin or Manager can change it.")
        serializer.save()
        record_audit(self.request, "hospital.update", hospital, hospital=hospital)

    def perform_destroy(self, instance):
        self._require_platform_admin()
        record_audit(self.request, "hospital.delete", instance, hospital=None)
        instance.delete()


class _OrgStructureViewSet(HospitalScopedViewSet):
    """Members read; the hospital's Admin or Manager writes."""

    def get_permissions(self):
        if getattr(self, "action", None) in _WRITE_ACTIONS:
            return [IsAuthenticated(), IsStaffUser(), IsHospitalMember(), (IsAdmin | IsHospitalManager)()]
        return [IsAuthenticated(), IsStaffUser(), IsHospitalMember()]


class DepartmentViewSet(_OrgStructureViewSet):
    queryset = Department.objects.select_related("hospital").order_by("name")
    serializer_class = DepartmentSerializer


class WardViewSet(_OrgStructureViewSet):
    queryset = Ward.objects.select_related("hospital").order_by("name")
    serializer_class = WardSerializer


class RoomViewSet(_OrgStructureViewSet):
    queryset = Room.objects.select_related("ward__hospital").order_by("id")
    serializer_class = RoomSerializer


class BedViewSet(_OrgStructureViewSet):
    queryset = Bed.objects.select_related("room__ward__hospital").order_by("id")
    serializer_class = BedSerializer
