"""
Inviting staff to a hospital.

The hospital's Admin or Manager enters the person's name, mobile, email and
role. The account is created at once with that membership but no password;
the person opens the invitation link, sees their username and sets a
password. The link is Django's password-reset token, so it expires after
PASSWORD_RESET_TIMEOUT and stops working once a password is set. The link is
emailed when possible and always returned to the inviter to share.
"""

import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from hospital.models import Department

from .models import StaffHospitalMembership, StaffProfile
from .patient_auth import normalize_phone
from .staff_admin import _acting_hospital, _role, _row

logger = logging.getLogger(__name__)
User = get_user_model()

INVALID_LINK = "This invitation link is invalid or has expired. Ask your hospital administrator for a new one."


def _invite_path(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return f"/staff-invite/{uid}/{default_token_generator.make_token(user)}"


def _invite_url(request, path):
    """
    FRONTEND_URL, else the web app the inviter is using (its Origin, when
    trusted: behind a dev proxy the Host is the API server's), else this host.
    """
    base = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    if not base:
        origin = request.headers.get("Origin", "")
        if origin and origin in getattr(settings, "CSRF_TRUSTED_ORIGINS", []):
            base = origin
    return f"{base}{path}" if base else request.build_absolute_uri(path)


def _email_invite(user, hospital_name, role, url):
    if not user.email:
        return False
    try:
        send_mail(
            f"You are invited to {hospital_name}",
            (
                f"Hello {user.get_full_name() or user.username},\n\n"
                f"You have been added to {hospital_name} as {role}.\n"
                f"Your username is {user.username}. Set your password here:\n{url}\n\n"
                "The link works once and expires in a few days."
            ),
            None,
            [user.email],
        )
        return True
    except Exception:
        logger.warning("Staff invitation email could not be sent", exc_info=True)
        return False


def _unique_username(email, phone):
    base = (email.split("@")[0] if email else f"staff_{phone}")[:80]
    username, suffix = base, 1
    while User.objects.filter(username__iexact=username).exists():
        username, suffix = f"{base}_{suffix}", suffix + 1
    return username


def _unique_employee_id():
    while True:
        employee_id = f"EMP-{uuid.uuid4().hex[:10].upper()}"
        if not StaffProfile.objects.filter(employee_id=employee_id).exists():
            return employee_id


def _invite_fields(data, hospital_id):
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    phone = normalize_phone(str(data.get("phone") or ""))
    errors = {}
    if not name:
        errors["name"] = "Name is required."
    if len(phone) != 10:
        errors["phone"] = "A valid 10-digit mobile number is required (it receives the sign-in code)."
    if email:
        try:
            validate_email(email)
        except DjangoValidationError:
            errors["email"] = "Enter a valid email address."
    department = None
    if data.get("department"):
        department = Department.objects.filter(pk=data["department"], hospital_id=hospital_id).first()
        if department is None:
            errors["department"] = "Department not found in this hospital."
    if errors:
        raise ValidationError(errors)
    return name, email, phone, department


def _response(request, profile, membership, hospital_name, invited):
    body = {**_row(profile, membership), "invited": invited}
    if invited:
        path = _invite_path(profile.user)
        url = _invite_url(request, path)
        body["invite_path"] = path
        body["invite_url"] = url
        body["emailed"] = _email_invite(profile.user, hospital_name, membership.role, url)
    return body


class StaffInviteView(APIView):
    """
    POST /api/users/invite/ {name, phone, email?, role, department?}

    Creates the account and membership. Someone who is already staff
    elsewhere (same email) is added to this hospital and keeps their password.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        hospital_id, granter_roles = _acting_hospital(request)
        role = _role(request.data.get("role"), granter_roles)
        name, email, phone, department = _invite_fields(request.data, hospital_id)

        existing = User.objects.filter(email__iexact=email).first() if email else None
        if existing is not None:
            profile = StaffProfile.objects.filter(user=existing).first()
            if profile is None:
                raise ValidationError({"email": "This email belongs to a patient account. Use another email."})
            if StaffHospitalMembership.objects.filter(staff=profile, hospital_id=hospital_id).exists():
                raise ValidationError({"email": "This person is already staff at this hospital."})
            invited = not existing.has_usable_password()
        else:
            first, _, last = name.partition(" ")
            user = User(username=_unique_username(email, phone), email=email,
                        first_name=first[:150], last_name=last[:150])
            user.set_unusable_password()
            user.save()
            profile = StaffProfile.objects.create(
                user=user, role=role, phone=phone, employee_id=_unique_employee_id(), is_active_staff=True
            )
            invited = True
        membership = StaffHospitalMembership.objects.create(
            staff=profile, hospital_id=hospital_id, role=role, department=department, is_active=True
        )
        record_audit(request, "users.staff.invited", profile, hospital=hospital_id,
                     details={"user": profile.user_id, "role": role, "new_account": existing is None})
        return Response(
            _response(request, profile, membership, membership.hospital.name, invited),
            status=status.HTTP_201_CREATED,
        )


class StaffInviteResendView(APIView):
    """POST /api/users/<id>/invite/ — a fresh link for someone who has not set a password yet."""

    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        hospital_id, _ = _acting_hospital(request)
        membership = (
            StaffHospitalMembership.objects.select_related("staff__user", "hospital")
            .filter(staff__user_id=user_id, hospital_id=hospital_id).first()
        )
        if membership is None:
            raise NotFound("This person is not staff at this hospital.")
        if membership.staff.user.has_usable_password():
            raise ValidationError("This person has already set a password.")
        record_audit(request, "users.staff.invite_resent", membership.staff, hospital=hospital_id,
                     details={"user": user_id})
        return Response(_response(request, membership.staff, membership, membership.hospital.name, True))


def _invited_user(uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None
    if user.has_usable_password() or not default_token_generator.check_token(user, token):
        return None
    return user


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def accept_staff_invite(request, uidb64, token):
    """
    GET: who the invitation is for. POST {password, confirm_password}: set
    the password; the person then signs in normally.
    """
    user = _invited_user(uidb64, token)
    if user is None:
        return Response({"error": INVALID_LINK}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "GET":
        memberships = StaffHospitalMembership.objects.filter(staff__user=user, is_active=True).select_related("hospital")
        return Response({
            "name": user.get_full_name() or user.username,
            "username": user.username,
            "hospitals": [{"name": m.hospital.name, "role": m.role} for m in memberships],
        })

    password = request.data.get("password") or ""
    if password != (request.data.get("confirm_password") or ""):
        return Response({"error": "Password and confirm password do not match."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        return Response({"error": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password)
    user.save(update_fields=["password"])
    record_audit(request, "users.staff.invite_accepted", user=user)
    return Response({"message": "Password set. Sign in with your username and password.", "username": user.username})
