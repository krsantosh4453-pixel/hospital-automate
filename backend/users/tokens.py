"""
Signing in and out (Phase 3): every sign-in creates a DeviceSession and a JWT
pair whose ``sid`` claim names it.

- Access tokens carry no roles or hospitals. Authorisation always reads the
  database (users/permissions.py), so a role change counts on the next request.
- Revoking a session refuses its access token on the next request
  (``CookieJWTAuthentication``) and its refresh token at once.
- Presenting a refresh token that was already rotated is treated as theft:
  the whole session is revoked. A token rotated in the last few seconds is
  only refused, because two browser tabs often refresh at the same moment.
- Tokens issued before sessions existed carry no ``sid``; they work until
  they expire.
"""

import ipaddress
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from config.client_ip import client_ip

from .models import DeviceSession

SESSION_CLAIM = "sid"
ACCOUNT_TYPE_CLAIM = "account_type"
# A rotated refresh token presented again within this window is a slow
# browser tab, not a stolen token.
REUSE_GRACE = timedelta(seconds=30)
SIGNED_OUT = "This session has been signed out. Sign in again."
_CACHE_KEY = "device-session:{}"
_REVOKED, _ACTIVE = "revoked", "active"


# ---------------------------------------------------------------------------
# Signing in
# ---------------------------------------------------------------------------

def issue_session_tokens(user, request=None, *, account_type, claims=None):
    """Create a DeviceSession and return ``{"access", "refresh"}`` naming it."""
    session = DeviceSession.objects.create(user=user, account_type=account_type, **_device_fields(request))
    refresh = RefreshToken.for_user(user)
    refresh[SESSION_CLAIM] = str(session.pk)
    refresh[ACCOUNT_TYPE_CLAIM] = account_type
    # Claims on the refresh token are copied into every access token minted from it.
    for name, value in (claims or {}).items():
        refresh[name] = value
    DeviceSession.objects.filter(pk=session.pk).update(current_jti=refresh["jti"])
    cache.set(_CACHE_KEY.format(session.pk), _ACTIVE, _cache_seconds())
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _device_fields(request):
    if request is None:
        return {}
    data = getattr(request, "data", None) or {}
    platform = str(data.get("platform") or "").lower()
    if platform not in DeviceSession.Platform.values:
        platform = DeviceSession.Platform.WEB if request.headers.get("X-Auth-Mode") == "cookie" else (
            DeviceSession.Platform.OTHER)
    return {
        "device_id": str(data.get("device_id") or "")[:64],
        "platform": platform,
        "app_version": str(data.get("app_version") or "")[:32],
        "user_agent": request.headers.get("User-Agent", "")[:200],
        "ip_prefix": _network_of(client_ip(request)),
    }


def _network_of(address):
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return ""
    prefix = 24 if ip.version == 4 else 48
    return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False))


# ---------------------------------------------------------------------------
# Signing out
# ---------------------------------------------------------------------------

def revoke_sessions(sessions, reason):
    """Revoke the given DeviceSession queryset; returns how many were still active."""
    ids = list(sessions.filter(revoked_at__isnull=True).values_list("pk", flat=True))
    if not ids:
        return 0
    DeviceSession.objects.filter(pk__in=ids).update(revoked_at=timezone.now(), revoked_reason=reason[:100])
    keys = [_CACHE_KEY.format(pk) for pk in ids]
    # Now: forget the cached state, so the next check reads the database (this
    # transaction sees the revoke; a rollback leaves the sessions active).
    cache.delete_many(keys)
    # After the commit: pin "revoked", overwriting any "active" another request
    # cached from the row before the commit (is_session_revoked only adds).
    transaction.on_commit(lambda: cache.set_many(dict.fromkeys(keys, _REVOKED), _cache_seconds()))
    return len(ids)


def revoke_all_sessions(user, reason):
    """Sign the user out everywhere, including tokens issued before sessions existed."""
    count = revoke_sessions(DeviceSession.objects.filter(user=user), reason)
    for token in OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now()):
        BlacklistedToken.objects.get_or_create(token=token)
    return count


def session_id_of(raw_refresh):
    """The ``sid`` of a refresh token whose signature checks out, or None."""
    try:
        return UntypedToken(raw_refresh).get(SESSION_CLAIM)
    except TokenError:
        return None


# ---------------------------------------------------------------------------
# Every request
# ---------------------------------------------------------------------------

def is_session_revoked(session_id):
    """Whether this sid is signed out (cached; a missing row counts as signed out)."""
    key = _CACHE_KEY.format(session_id)
    state = cache.get(key)
    if state is None:
        active = DeviceSession.objects.filter(pk=session_id, revoked_at__isnull=True).exists()
        state = _ACTIVE if active else _REVOKED
        cache.add(key, state, _cache_seconds())
    return state == _REVOKED


def account_may_continue(user):
    """An active login that, if it is staff, is still active staff."""
    if user is None or not user.is_active:
        return False
    profile = getattr(user, "staff_profile", None) if hasattr(user, "staff_profile") else None
    return profile is None or profile.is_active_staff


def _cache_seconds():
    return int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())


# ---------------------------------------------------------------------------
# Refreshing (SIMPLE_JWT["TOKEN_REFRESH_SERIALIZER"])
# ---------------------------------------------------------------------------

class SessionTokenRefreshSerializer(TokenRefreshSerializer):
    """SimpleJWT's refresh with rotation, plus the session and account checks above."""

    def validate(self, attrs):
        raw = attrs["refresh"]
        try:
            token = RefreshToken(raw)
        except TokenError:
            _revoke_if_reused(raw)
            raise
        session_id = token.get(SESSION_CLAIM)
        if session_id is None:
            return self._refresh(attrs, token, session_id=None)
        with transaction.atomic():
            # One refresh per session at a time: parallel requests with the same
            # token wait here, and only the newest token of the session counts.
            session = DeviceSession.objects.select_for_update().filter(pk=session_id).first()
            if session is None or session.revoked_at is not None:
                raise AuthenticationFailed(SIGNED_OUT, code="session_revoked")
            if session.current_jti and session.current_jti != token["jti"]:
                # Rotated by a parallel request a moment ago; the client uses that one.
                raise AuthenticationFailed("This sign-in was refreshed elsewhere. Use the newest token.",
                                           code="stale_refresh")
            try:
                return self._refresh(attrs, token, session_id=session_id)
            except _AccountDisabled:
                pass
        # Outside the block above, which the refusal rolls back.
        revoke_sessions(DeviceSession.objects.filter(pk=session_id), "account disabled")
        raise AuthenticationFailed(_ACCOUNT_DISABLED, code="account_disabled")

    def _refresh(self, attrs, token, session_id):
        user = get_user_model().objects.filter(pk=token.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])).first()
        if not account_may_continue(user) or not _proxy_grant_active(token):
            if session_id is not None:
                raise _AccountDisabled()
            raise AuthenticationFailed(_ACCOUNT_DISABLED, code="account_disabled")

        data = super().validate(attrs)
        if session_id is not None:
            newest = RefreshToken(data["refresh"])["jti"] if "refresh" in data else token["jti"]
            DeviceSession.objects.filter(pk=session_id).update(current_jti=newest, last_used_at=timezone.now())
        return data


class _AccountDisabled(Exception):
    """The session's account or family-access grant has ended (internal signal)."""


_ACCOUNT_DISABLED = "This account can no longer sign in."


def _proxy_grant_active(token):
    """Family-access tokens refresh only while their grant is active."""
    from .proxy_access import PROXY_CLAIM

    grant_id = token.get(PROXY_CLAIM)
    if grant_id is None:
        return True
    from patients.models import ProxyAccess

    return ProxyAccess.objects.filter(pk=grant_id, revoked_at__isnull=True).exists()


def _revoke_if_reused(raw):
    """A validly signed refresh token that is blacklisted was used before: revoke its session."""
    try:
        token = UntypedToken(raw)
    except TokenError:
        return  # expired or forged: nothing to learn from it
    session_id = token.get(SESSION_CLAIM)
    if session_id is None:
        return
    rotated = BlacklistedToken.objects.filter(token__jti=token.get("jti")).values_list("blacklisted_at", flat=True)
    rotated_at = rotated.first()
    if rotated_at is None or timezone.now() - rotated_at < REUSE_GRACE:
        return
    if revoke_sessions(DeviceSession.objects.filter(pk=session_id), "refresh token reused"):
        from audit.services import record_audit

        record_audit(None, "auth.refresh_reuse", user=DeviceSession.objects.get(pk=session_id).user,
                     details={"session": str(session_id)})
