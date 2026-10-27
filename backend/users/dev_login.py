"""
Temporary development sign-in: one shared mobile number or email and one
password open the seed_demo account of any role, so every page can be built
and checked before SMS OTP (Twilio) is set up.

It works only when DEBUG is on and DEV_LOGIN_ENABLED, DEV_LOGIN_PASSWORD and
DEV_LOGIN_MOBILE or DEV_LOGIN_EMAIL are set in .env. Production settings
switch it off. To remove it later: delete this file, its URL, the
DEV_LOGIN_* settings and src/components/DevLoginPanel.jsx.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from audit.services import record_audit

from . import security
from .views import _auth_response

PATIENT_ROLE = "Patient"

# Role shown in the sign-in form -> seed_demo account it opens.
DEV_ACCOUNTS = {
    "Admin": "demo.admin",
    "Doctor": "demo.doctor1",
    "Nurse": "demo.nurse",
    "Compounder": "demo.compounder",
    "Receptionist": "demo.desk.main",
    "Pharmacist": "demo.pharmacist",
    "Lab Staff": "demo.lab",
    "Blood Bank Staff": "demo.bloodbank",
    "Billing Staff": "demo.billing",
    "Inventory Staff": "demo.inventory",
    "Hospital Manager": "demo.manager",
    PATIENT_ROLE: "demo.patient",
}

LOCKOUT_KEY = "dev-login"
MOBILE_DIGITS = 10


def dev_login_enabled():
    return bool(
        settings.DEBUG
        and getattr(settings, "DEV_LOGIN_ENABLED", False)
        and getattr(settings, "DEV_LOGIN_PASSWORD", "")
        and (getattr(settings, "DEV_LOGIN_MOBILE", "") or getattr(settings, "DEV_LOGIN_EMAIL", ""))
    )


def _last_digits(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[-MOBILE_DIGITS:] if len(digits) >= MOBILE_DIGITS else ""


def _identifier_matches(identifier):
    identifier = str(identifier or "").strip()
    email = getattr(settings, "DEV_LOGIN_EMAIL", "").strip().lower()
    if "@" in identifier:
        return bool(email) and constant_time_compare(identifier.lower(), email)
    mobile = _last_digits(getattr(settings, "DEV_LOGIN_MOBILE", ""))
    given = _last_digits(identifier)
    return bool(mobile and given) and constant_time_compare(given, mobile)


def _session_for(role):
    user = get_user_model().objects.filter(username=DEV_ACCOUNTS[role], is_active=True).first()
    if user is None:
        return None
    if role == PATIENT_ROLE:
        patient = getattr(user, "patient_account", None)
        return _auth_response(user, patient) if patient else None
    return _auth_response(user)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def dev_login(request):
    if not dev_login_enabled():
        return Response({"enabled": False}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response({"enabled": True, "roles": list(DEV_ACCOUNTS)})

    if security.is_locked_out(LOCKOUT_KEY):
        return Response(
            {"error": "Too many failed sign-in attempts. Try again in 15 minutes."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    role = request.data.get("role")
    if role not in DEV_ACCOUNTS:
        return Response({"error": "Choose a role to sign in as."}, status=status.HTTP_400_BAD_REQUEST)

    password = str(request.data.get("password") or "")
    if not (_identifier_matches(request.data.get("identifier"))
            and constant_time_compare(password, settings.DEV_LOGIN_PASSWORD)):
        security.record_failure(LOCKOUT_KEY)
        return Response({"error": "Invalid mobile number, email or password."}, status=status.HTTP_401_UNAUTHORIZED)

    payload = _session_for(role)
    if payload is None:
        return Response(
            {"error": f"No demo account for {role}. Run: python manage.py seed_demo --password <any password>"},
            status=status.HTTP_409_CONFLICT,
        )

    security.clear_failures(LOCKOUT_KEY)
    record_audit(request, "auth.dev_login.success", details={"role": role})
    return Response({"status": "success", **payload})
