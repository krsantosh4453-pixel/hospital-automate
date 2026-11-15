"""The signed-in account (Phase 3): what it may act as, and its devices (list, sign out one or all)."""

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import record_audit
from config.auth_cookies import clear_auth_cookies

from hospital.models import Hospital

from .models import DeviceSession
from .permissions import get_linked_patient, get_user_active_hospital_memberships, is_active_staff
from .platform import platform_role
from .role_permissions import permissions_for, restricted_modules
from .tokens import SESSION_CLAIM, revoke_all_sessions, revoke_sessions

_FIELDS = ("device_id", "platform", "app_version", "user_agent", "created_at", "last_used_at")


def _current_session_id(request):
    token = getattr(request, "auth", None)
    return str(token.get(SESSION_CLAIM)) if token is not None and token.get(SESSION_CLAIM) else None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_contexts(request):
    """
    GET: what this account may act as. Staff get one entry per active
    membership in an active hospital, with its role and permissions after the
    hospital's restrictions; patients get the hospitals they are registered at.
    Send the chosen hospital as X-Hospital-ID; the server checks it every time.
    """
    user = request.user
    if is_active_staff(user):
        account_type = "staff"
        contexts = [
            {
                "hospital": {"id": m.hospital_id, "name": m.hospital.name},
                "role": m.role,
                "department": m.department.name if m.department else None,
                "permissions": sorted(permissions_for(user, m.hospital_id)),
                "restricted_modules": restricted_modules(user, m.hospital_id),
            }
            for m in get_user_active_hospital_memberships(user).filter(hospital__is_active=True)
            .order_by("hospital__name")
        ]
    elif get_linked_patient(user) is not None:
        patient = get_linked_patient(user)
        account_type = "proxy" if getattr(user, "proxy_patient", None) is not None else "patient"
        hospital_ids = set(patient.hospital_memberships.filter(is_active=True).values_list("hospital_id", flat=True))
        if patient.hospital_id:
            hospital_ids.add(patient.hospital_id)
        contexts = [{"hospital": {"id": h.id, "name": h.name}, "role": "Patient"}
                    for h in Hospital.objects.filter(id__in=hospital_ids, is_active=True).order_by("name")]
    else:
        account_type, contexts = ("platform" if platform_role(user) else "none"), []
    return Response({"account_type": account_type, "platform_role": platform_role(user), "contexts": contexts})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_list(request):
    """GET: this account's signed-in devices, newest first; ``current`` marks this one."""
    current = _current_session_id(request)
    rows = DeviceSession.objects.filter(user=request.user, revoked_at__isnull=True)
    return Response({"sessions": [
        {"id": str(row.pk), **{name: getattr(row, name) for name in _FIELDS}, "current": str(row.pk) == current}
        for row in rows
    ]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def session_revoke(request, session_id):
    """POST: sign one of this account's devices out (404 for anyone else's)."""
    session = get_object_or_404(DeviceSession, pk=session_id, user=request.user, revoked_at__isnull=True)
    revoke_sessions(DeviceSession.objects.filter(pk=session.pk), "signed out from another device")
    record_audit(request, "auth.session.revoked", details={"session": str(session.pk)})
    response = Response({"revoked": str(session.pk)})
    if str(session.pk) == _current_session_id(request):
        clear_auth_cookies(response)
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_all(request):
    """POST: sign this account out on every device, this one included."""
    count = revoke_all_sessions(request.user, "signed out everywhere")
    record_audit(request, "auth.session.logout_all", details={"sessions": count})
    response = Response({"revoked_sessions": count})
    clear_auth_cookies(response)
    return response
