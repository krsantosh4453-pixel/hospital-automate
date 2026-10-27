from django.db import models
from django.db.models import OuterRef, Subquery
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from audit.services import record_audit
from users.permissions import (
    IsStaffUser,
    IsAdmin,
    IsHospitalManager,
    IsHospitalMember,
    get_request_hospital_id,
    get_user_hospital_ids,
    get_user_roles,
)
from users.viewsets import HospitalScopedViewSet, hospital_id_of, resolve_hospital_lookup
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

    def _hospital_of_data(self, data):
        """Hospital a new or changed row would belong to (via its ward, room, …)."""
        for value in data.values():
            if isinstance(value, Hospital):
                return value.pk
            if isinstance(value, models.Model):
                owner = hospital_id_of(value, resolve_hospital_lookup(type(value)))
                if owner is not None:
                    return owner
        return get_request_hospital_id(self.request, self)

    def _require_manager_of(self, hospital_id):
        # The permission class checks the role at the hospital named in the
        # request; the row may belong to another hospital the user is in.
        if self.request.user.is_superuser or hospital_id is None:
            return
        roles = get_user_roles(self.request.user, hospital_id)
        if StaffRole.ADMIN not in roles and StaffRole.HOSPITAL_MANAGER not in roles:
            raise PermissionDenied("Only this hospital's Admin or Manager can change its wards, rooms and beds.")

    def perform_create(self, serializer):
        self._require_manager_of(self._hospital_of_data(serializer.validated_data))
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._require_manager_of(self.get_object_hospital_id(serializer.instance))
        self._require_manager_of(self._hospital_of_data(serializer.validated_data))
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._require_manager_of(self.get_object_hospital_id(instance))
        super().perform_destroy(instance)

    def _filter_by_param(self, queryset, param):
        value = self.request.query_params.get(param)
        return queryset.filter(**{f"{param}_id": value}) if value and value.isdigit() else queryset


class DepartmentViewSet(_OrgStructureViewSet):
    queryset = Department.objects.select_related("hospital").order_by("name")
    serializer_class = DepartmentSerializer


class WardViewSet(_OrgStructureViewSet):
    queryset = Ward.objects.select_related("hospital").order_by("name")
    serializer_class = WardSerializer


class RoomViewSet(_OrgStructureViewSet):
    queryset = Room.objects.select_related("ward__hospital").order_by("id")
    serializer_class = RoomSerializer

    def get_queryset(self):
        return self._filter_by_param(super().get_queryset(), "ward")


class BedViewSet(_OrgStructureViewSet):
    queryset = Bed.objects.select_related("room__ward__hospital").order_by("id")
    serializer_class = BedSerializer

    def get_queryset(self):
        from ipd.models import BedAllocation  # ipd depends on hospital

        current = BedAllocation.objects.filter(bed=OuterRef("pk"), is_active=True).order_by("-allocated_at")
        queryset = super().get_queryset().annotate(
            current_patient_name=Subquery(current.values("admission__patient__name")[:1])
        )
        return self._filter_by_param(queryset, "room")

    def perform_destroy(self, instance):
        self._require_manager_of(self.get_object_hospital_id(instance))
        # Deleting would also delete the admissions' bed history.
        if instance.allocations.exists():
            raise ValidationError(
                {"detail": "This bed has admission history and cannot be deleted. Set it to Maintenance instead."}
            )
        super().perform_destroy(instance)


class HospitalDirectoryView(APIView):
    """
    Active hospitals with public contact details, for the patient hospital
    picker and record-sharing recipient lists. For a patient login each row
    says whether they are registered there.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from users.permissions import get_linked_patient

        patient = get_linked_patient(request.user)
        registered = set()
        if patient is not None:
            registered = set(patient.hospital_memberships.filter(is_active=True).values_list("hospital_id", flat=True))
            if patient.hospital_id:
                registered.add(patient.hospital_id)
        rows = Hospital.objects.filter(is_active=True).order_by("name")
        search = (request.query_params.get("search") or "").strip()
        if search:
            rows = rows.filter(name__icontains=search)
        return Response([
            {
                "id": h.id, "name": h.name, "address": h.address, "city": h.city, "state": h.state,
                "phone": h.phone, "is_active": h.is_active,
                **({"registered": h.id in registered} if patient is not None else {}),
            }
            for h in rows[:200]
        ])
