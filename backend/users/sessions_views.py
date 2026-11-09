"""The signed-in user's own devices: list them, sign one out, or sign out everywhere (Phase 3)."""

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import record_audit
from config.auth_cookies import clear_auth_cookies

from .models import DeviceSession
from .tokens import SESSION_CLAIM, revoke_all_sessions, revoke_sessions

_FIELDS = ("device_id", "platform", "app_version", "user_agent", "created_at", "last_used_at")


def _current_session_id(request):
    token = getattr(request, "auth", None)
    return str(token.get(SESSION_CLAIM)) if token is not None and token.get(SESSION_CLAIM) else None


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
