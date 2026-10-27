"""
Hospital staff administration: list staff and pending registrations, approve
an applicant into the acting hospital with a role, and change or end a
membership. Only that hospital's Admin or Hospital Manager may do this, and
only an Admin may grant the Admin role. Every change is audited.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from hospital.models import Department

from .models import StaffHospitalMembership, StaffProfile, StaffRole
from .permissions import (
    get_request_hospital_id,
    get_user_hospital_ids,
    get_user_roles,
    is_active_staff,
)

User = get_user_model()
MANAGER_ROLES = {StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER}


def _acting_hospital(request):
    """The single hospital being administered; the caller must manage it."""
    if not is_active_staff(request.user):
        raise PermissionDenied("Staff only.")
    allowed = get_user_hospital_ids(request.user)
    hospital_id = get_request_hospital_id(request)
    if hospital_id is None and len(allowed) == 1:
        hospital_id = allowed[0]
    if hospital_id is None:
        raise ValidationError({"hospital": "Select the hospital to administer."})
    if hospital_id not in allowed:
        raise PermissionDenied("You are not a member of that hospital.")
    roles = set(get_user_roles(request.user, hospital_id))
    if not roles & MANAGER_ROLES:
        raise PermissionDenied("Only this hospital's Admin or Manager can manage staff.")
    return hospital_id, roles


def _role(value, granter_roles):
    if value not in StaffRole.values:
        raise ValidationError({"role": f"Role must be one of: {', '.join(StaffRole.values)}."})
    if value == StaffRole.ADMIN and StaffRole.ADMIN not in granter_roles:
        raise PermissionDenied("Only an Admin can grant the Admin role.")
    return value


def _row(profile, membership=None):
    user = profile.user
    return {
        "id": user.id,
        "username": user.username,
        "name": user.get_full_name() or user.username,
        "email": user.email,
        "phone": profile.phone,
        "employee_id": profile.employee_id,
        "requested_role": profile.role,
        "is_active_staff": profile.is_active_staff,
        "membership": None if membership is None else {
            "hospital": membership.hospital_id,
            "role": membership.role,
            "department": membership.department_id,
            "is_active": membership.is_active,
        },
    }


class StaffListView(APIView):
    """GET /api/users/ — staff of the acting hospital and pending registrations."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        hospital_id, _ = _acting_hospital(request)
        memberships = StaffHospitalMembership.objects.filter(hospital_id=hospital_id).select_related(
            "staff__user"
        )
        search = (request.query_params.get("search") or "").strip()
        if search:
            memberships = memberships.filter(
                Q(staff__user__username__icontains=search) | Q(staff__user__first_name__icontains=search)
                | Q(staff__user__last_name__icontains=search) | Q(staff__employee_id__icontains=search)
            )
        staff = [_row(m.staff, m) for m in memberships.order_by("staff__user__username")[:500]]
        pending = StaffProfile.objects.filter(
            is_active_staff=False, hospital_memberships__isnull=True, user__is_active=True
        ).select_related("user")
        return Response({"staff": staff, "pending": [_row(p) for p in pending[:200]]})


class StaffApproveView(APIView):
    """POST /api/users/<id>/approve/ {role, department?} — admit an applicant to this hospital."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, user_id):
        hospital_id, granter_roles = _acting_hospital(request)
        try:
            profile = StaffProfile.objects.select_for_update().select_related("user").get(user_id=user_id)
        except StaffProfile.DoesNotExist:
            raise NotFound("Staff registration not found.")
        if profile.is_active_staff and profile.hospital_memberships.exists():
            raise ValidationError("Already approved; use the membership endpoint to change the role.")
        role = _role(request.data.get("role") or profile.role, granter_roles)
        department = None
        if request.data.get("department"):
            department = Department.objects.filter(pk=request.data["department"], hospital_id=hospital_id).first()
            if department is None:
                raise ValidationError({"department": "Department not found in this hospital."})
        profile.is_active_staff = True
        profile.role = role
        profile.save(update_fields=["is_active_staff", "role"])
        membership, _ = StaffHospitalMembership.objects.update_or_create(
            staff=profile, hospital_id=hospital_id,
            defaults={"role": role, "department": department, "is_active": True},
        )
        record_audit(request, "users.staff.approved", profile, hospital=hospital_id,
                     details={"user": profile.user_id, "role": role})
        return Response(_row(profile, membership), status=status.HTTP_200_OK)


class StaffMembershipView(APIView):
    """PATCH /api/users/<id>/membership/ {role?, is_active?, department?} in the acting hospital."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, user_id):
        hospital_id, granter_roles = _acting_hospital(request)
        try:
            membership = StaffHospitalMembership.objects.select_for_update().select_related("staff__user").get(
                staff__user_id=user_id, hospital_id=hospital_id
            )
        except StaffHospitalMembership.DoesNotExist:
            raise NotFound("This person is not staff at this hospital.")
        if membership.staff.user_id == request.user.id:
            raise ValidationError("You cannot change your own access.")
        if membership.role == StaffRole.ADMIN and StaffRole.ADMIN not in granter_roles:
            raise PermissionDenied("Only an Admin can change another Admin.")
        changes = {}
        if "role" in request.data:
            membership.role = _role(request.data["role"], granter_roles)
            changes["role"] = membership.role
        if "is_active" in request.data:
            membership.is_active = str(request.data["is_active"]).lower() in ("true", "1", "yes")
            changes["is_active"] = membership.is_active
        if "department" in request.data:
            dept_id = request.data["department"]
            membership.department = (
                Department.objects.filter(pk=dept_id, hospital_id=hospital_id).first() if dept_id else None
            )
            if dept_id and membership.department is None:
                raise ValidationError({"department": "Department not found in this hospital."})
            changes["department"] = dept_id
        if not changes:
            raise ValidationError("Nothing to change.")
        membership.save()
        record_audit(request, "users.staff.membership_changed", membership.staff, hospital=hospital_id,
                     details={"user": user_id, **changes})
        return Response(_row(membership.staff, membership))
