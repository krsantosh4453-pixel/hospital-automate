"""
Family / caregiver (proxy) access.

A patient grants a family member view-only access. The family member signs in
with an OTP sent to their own mobile number and receives tokens that carry the
grant id (``proxy_grant`` claim). On every request the grant is re-checked, so
revoking it ends access at once, and writes are refused.

DRF loads ``config.auth_cookies`` (which calls ``apply_proxy_scope``) while it
reads its settings, so models are imported inside functions here.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework_simplejwt.tokens import RefreshToken

PROXY_CLAIM = "proxy_grant"
PROXY_USERNAME_PREFIX = "proxy-"
MAX_ACTIVE_GRANTS = 5
TICKET_SALT = "hms.proxy-login"
TICKET_MAX_AGE = timedelta(minutes=10)
OTP_TTL = timedelta(minutes=5)
GENERIC_OTP_MESSAGE = "If this mobile number has family access, a verification code has been sent."
# Session endpoints only; family-access management refuses proxies itself.
WRITE_ALLOWED_PREFIX = "/api/auth/"

User = get_user_model()


def active_grants_for_phone(phone):
    from patients.models import ProxyAccess

    return list(
        ProxyAccess.objects.select_related("patient")
        .filter(phone=phone, revoked_at__isnull=True)
        .order_by("patient__name")
    )


def grant_payload(grant):
    """What the patient sees about a family member they have added."""
    return {
        "id": grant.id,
        "name": grant.name,
        "relationship": grant.relationship,
        "phone": grant.phone,
        "created_at": grant.created_at,
        "last_used_at": grant.last_used_at,
    }


def proxy_payload(grant):
    """What the signed-in family member sees about their own access."""
    return {"id": grant.id, "name": grant.name, "relationship": grant.relationship}


def login_choice_payload(grant):
    return {"id": grant.id, "patient_name": grant.patient.name, "relationship": grant.relationship}


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------

def request_proxy_otp(phone):
    """Returns (status, message, delivery) in the shape of request_patient_otp."""
    from django.conf import settings

    from notifications.models import OTPVerification
    from users.patient_auth import _sms_provider_configured, _too_many_requests, normalize_phone
    from users.sms import SMS_NOT_CONFIGURED, SMSService

    normalized = normalize_phone(phone)
    if not normalized:
        return "invalid", "A valid 10-digit mobile number is required.", None

    mode = getattr(settings, "PATIENT_OTP_DELIVERY", "sms")
    if mode == "off":
        # Answered before looking the number up, so it reveals nothing (RL-06).
        return "unavailable", SMS_NOT_CONFIGURED, "sms"
    if not active_grants_for_phone(normalized):
        # Same answer as a real send, so numbers with access are not revealed.
        if mode == "sms" and not _sms_provider_configured():
            return "unavailable", SMS_NOT_CONFIGURED, "sms"
        return "pending", GENERIC_OTP_MESSAGE, "sms" if mode == "sms" else mode

    if _too_many_requests(phone=normalized, channel="sms"):
        return "limited", "Too many OTP requests. Please try again later.", None

    result = SMSService().send_otp(normalized)
    if not result.ok:
        return "unavailable", result.message, result.delivery

    OTPVerification.objects.create(
        phone=normalized,
        channel="sms",
        purpose="proxy_login",
        expires_at=timezone.now() + OTP_TTL,
    )
    message = result.message if result.delivery == "console" else GENERIC_OTP_MESSAGE
    return "pending", message, result.delivery


def verify_proxy_otp(phone, otp):
    """Returns (normalized phone, active grants, error message)."""
    from notifications.models import OTPVerification
    from users.patient_auth import normalize_phone
    from users.sms import SMSService

    normalized = normalize_phone(phone)
    code = "".join(ch for ch in str(otp or "") if ch.isdigit())
    if not normalized or len(code) != 6:
        return normalized, [], "Invalid OTP."

    result = SMSService().verify_otp(normalized, code)
    if not result.ok:
        return normalized, [], result.message or "Invalid OTP."

    grants = active_grants_for_phone(normalized)
    if not grants:
        return normalized, [], "Invalid OTP."

    OTPVerification.objects.filter(
        phone=normalized, channel="sms", purpose="proxy_login", is_verified=False
    ).update(is_verified=True)
    return normalized, grants, None


def make_ticket(phone):
    """Short-lived proof that this phone passed OTP, used to pick a patient."""
    return signing.dumps({"phone": phone}, salt=TICKET_SALT)


def read_ticket(ticket):
    try:
        data = signing.loads(str(ticket or ""), salt=TICKET_SALT, max_age=TICKET_MAX_AGE)
    except signing.BadSignature:
        return None
    return data.get("phone") if isinstance(data, dict) else None


def proxy_user_for(phone):
    """
    The sign-in identity for a family member's phone. It is kept apart from
    patient and staff accounts, and refused if it has become either.
    """
    from users.models import StaffProfile

    user, created = User.objects.get_or_create(username=f"{PROXY_USERNAME_PREFIX}{phone}")
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    if not user.is_active or StaffProfile.objects.filter(user=user).exists():
        return None
    if getattr(user, "patient_account", None) is not None:
        return None
    return user


def issue_proxy_tokens(user, grant):
    # Claims on the refresh token are copied into every access token minted from it.
    refresh = RefreshToken.for_user(user)
    refresh[PROXY_CLAIM] = grant.id
    refresh["role"] = "Patient"
    refresh["patient_id"] = grant.patient_id
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


# ---------------------------------------------------------------------------
# Every authenticated request
# ---------------------------------------------------------------------------

def apply_proxy_scope(request, user, token):
    """
    For a proxy token: confirm the grant is still active, refuse writes, and
    attach the patient so ``get_linked_patient`` scopes every query to them.
    """
    grant_id = token.get(PROXY_CLAIM) if token is not None else None
    if grant_id is None:
        return

    from patients.models import ProxyAccess

    grant = (
        ProxyAccess.objects.select_related("patient")
        .filter(pk=grant_id, proxy_user=user, revoked_at__isnull=True)
        .first()
    )
    if grant is None:
        raise AuthenticationFailed("This family access has ended. Ask the patient to grant it again.")
    if request.method not in SAFE_METHODS and not request.path.startswith(WRITE_ALLOWED_PREFIX):
        raise PermissionDenied("Family members have view-only access.")
    user.proxy_patient = grant.patient
    user.proxy_grant = grant


def get_proxy_grant(user):
    return getattr(user, "proxy_grant", None) if user is not None else None
