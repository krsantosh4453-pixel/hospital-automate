"""
The hospital Admin's read-only security overview (decision 3 / Q3, 2026-11-09).

Covers only the acting hospital's staff: their roles and permissions, signed-in
devices, sign-in history, the hospital's module restrictions, and alerts. It
never returns IP addresses, token ids or patient details, and changes
nothing: server-wide settings stay in environment variables and are shown to
platform staff only (users/security_settings.py).

S-L5 (2026-11-18): staff can work at several hospitals, and their audit rows
and devices are account-wide. Sessions, sign-in history and alerts cover only
people with an active membership here, and only audit rows recorded for this
hospital or for no hospital (sign-in itself is not tied to one). Rows another
hospital recorded, and the client-chosen device id that would let two
hospitals' admins match one device, are never returned.
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.models import AuditLog, BreakGlassAccess
from doctors.models import Doctor
from users.models import DeviceSession, StaffHospitalMembership, StaffRole
from users.permissions import get_request_hospital_id, get_user_hospital_ids, get_user_roles
from users.role_permissions import permissions_for

from .models import Hospital, RoleModuleRestriction

HISTORY_DAYS = 30
HISTORY_LIMIT = 200
ALERT_DAYS = 7


def _acting_hospital(request):
    """The hospital being looked at; the caller must be its Admin."""
    allowed = get_user_hospital_ids(request.user)
    hospital_id = get_request_hospital_id(request)
    if hospital_id is None and len(allowed) == 1:
        hospital_id = allowed[0]
    if hospital_id is None:
        raise ValidationError({"hospital": "Send X-Hospital-ID for the hospital to review."})
    if hospital_id not in allowed or StaffRole.ADMIN not in get_user_roles(request.user, hospital_id):
        raise PermissionDenied("Only this hospital's Admin can see its security overview.")
    return Hospital.objects.get(pk=hospital_id)


def _name(user):
    return user.get_full_name() or user.username


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def security_overview(request):
    hospital = _acting_hospital(request)
    memberships = list(
        StaffHospitalMembership.objects.filter(hospital=hospital)
        .select_related("staff__user", "department").order_by("staff__user__username")
    )
    users = {m.staff.user_id: m.staff.user for m in memberships}
    # Only current members' accounts can act here, so only theirs are reviewed.
    active_users = {
        m.staff.user_id: m.staff.user for m in memberships if m.is_active and m.staff.is_active_staff
    }
    now = timezone.now()

    staff = [{
        "user_id": m.staff.user_id,
        "name": _name(m.staff.user),
        "username": m.staff.user.username,
        "role": m.role,
        "department": m.department.name if m.department else None,
        "is_active": m.is_active and m.staff.is_active_staff,
        "permissions": sorted(permissions_for(m.staff.user, hospital.id)) if m.is_active else [],
    } for m in memberships]

    sessions = [{
        "user_id": s.user_id, "name": _name(active_users[s.user_id]), "platform": s.platform,
        "app_version": s.app_version, "created_at": s.created_at, "last_used_at": s.last_used_at,
    } for s in DeviceSession.objects.filter(user_id__in=active_users, revoked_at__isnull=True)]

    history = [{
        "user_id": row.user_id, "name": _name(active_users[row.user_id]), "action": row.action, "at": row.created_at,
    } for row in _audit_rows(hospital, active_users).filter(
        action__startswith="auth.", created_at__gte=now - timedelta(days=HISTORY_DAYS),
    ).order_by("-created_at")[:HISTORY_LIMIT]]

    return Response({
        "hospital": {"id": hospital.id, "name": hospital.name},
        "staff": staff,
        "sessions": sessions,
        "sign_in_history": history,
        "restricted_modules": list(
            RoleModuleRestriction.objects.filter(hospital=hospital).values("role", "module", "access")),
        "alerts": _alerts(hospital, active_users, now),
        "settings": {
            "require_verified_doctors": hospital.require_verified_doctors,
            "unverified_doctors": Doctor.objects.filter(hospital=hospital, registration_verified_at__isnull=True)
            .exclude(status="Inactive").count(),
        },
    })


def _audit_rows(hospital, users):
    """These members' audit rows that belong to this hospital or to no hospital."""
    return AuditLog.objects.filter(user_id__in=users).filter(Q(hospital=hospital) | Q(hospital__isnull=True))


def _alerts(hospital, users, now):
    since = now - timedelta(days=ALERT_DAYS)
    alerts = [{
        "kind": "refresh_reuse", "user_id": row.user_id, "name": _name(users[row.user_id]), "at": row.created_at,
        "detail": "A signed-out refresh token was used again; that session was signed out.",
    } for row in _audit_rows(hospital, users).filter(action="auth.refresh_reuse", created_at__gte=since)]
    alerts += [{
        "kind": "otp_failures", "user_id": user_id, "name": _name(users[user_id]), "at": None,
        "detail": f"{count} wrong sign-in code(s) in the last {ALERT_DAYS} days.",
    } for user_id, count in _counts(hospital, users, "auth.staff_otp.failed", since).items()]
    alerts += [{
        "kind": "break_glass_unreviewed", "user_id": grant.user_id, "name": _name(grant.user), "at": grant.created_at,
        "detail": "Emergency access waiting for an Admin's review.",
    } for grant in BreakGlassAccess.objects.filter(hospital=hospital, reviewed_at__isnull=True).select_related("user")]
    return alerts


def _counts(hospital, users, action, since):
    counts = {}
    for user_id in _audit_rows(hospital, users).filter(action=action, created_at__gte=since) \
            .values_list("user_id", flat=True):
        counts[user_id] = counts.get(user_id, 0) + 1
    return counts
