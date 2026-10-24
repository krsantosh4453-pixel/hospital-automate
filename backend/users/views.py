import logging
import uuid
from datetime import date

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)

from .models import GoogleAccount, StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient
from .patient_auth import (
    authenticate_patient_email,
    authenticate_patient_identifier,
    issue_login_tokens,
    link_google_patient,
    normalize_phone,
    patient_payload,
    request_patient_otp,
    send_email_otp,
    verify_email_otp,
    verify_google_identity,
    verify_patient_otp,
)
from .sms import SMSService
from .twilio_verify import get_twilio_verify_service


def _auth_response(user, patient=None, extra=None):
    staff_data = _get_staff_data(user)
    if staff_data and patient is None:
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        access["staff_id"] = user.id
        access["staff_role"] = staff_data["staff_role"]
        access["roles"] = staff_data["roles"]
        access["hospitals"] = [h["id"] for h in staff_data["hospitals"]]
        payload = {
            "access": str(access),
            "refresh": str(refresh),
            "account_type": "staff",
            "user": staff_data,
            "roles": staff_data["roles"],
            "hospitals": staff_data["hospitals"],
        }
    else:
        payload = {
            "account_type": "patient",
            "role": "Patient",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": patient.name if patient else user.get_full_name(),
            },
            "patient": patient_payload(patient) if patient else None,
            **issue_login_tokens(user, patient),
        }
    if extra:
        payload.update(extra)
    return payload


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    token = request.data.get("credential")

    if not token:
        return Response(
            {"error": "Google credential is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    google_data = verify_google_identity(token)
    if not google_data:
        return Response(
            {"error": "Google authentication failed."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    google_id = google_data.get("sub")
    email = (google_data.get("email") or "").strip().lower()
    name = google_data.get("name", "") or ""
    picture = google_data.get("picture", "") or ""

    try:
        google_account = GoogleAccount.objects.filter(google_id=google_id).first()
        if google_account:
            user = google_account.user
            google_account.email = email or google_account.email
            google_account.name = name or google_account.name
            google_account.picture = picture or google_account.picture
            google_account.save()
        else:
            user = User.objects.filter(email__iexact=email).first() if email else None
            if user is None and email:
                user = User.objects.filter(username__iexact=email).first()
            if user is None:
                user = User.objects.create_user(
                    username=_unique_username(email, ""),
                    email=email,
                    password=uuid.uuid4().hex,
                    first_name=name[:150],
                )
                user.set_unusable_password()
                user.save(update_fields=["password"])
            google_account = GoogleAccount.objects.create(
                user=user,
                google_id=google_id,
                email=email,
                name=name,
                picture=picture,
            )

        staff_data = _get_staff_data(user)
        if staff_data:
            return Response({
                "status": "success",
                **_auth_response(user),
            })

        patient = link_google_patient(user, name, email)
        if google_account.patient_id != patient.id:
            google_account.patient = patient
            google_account.save(update_fields=["patient"])

        return Response({
            "status": "success",
            "message": "Google login successful.",
            **_auth_response(user, patient, extra={
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": google_account.name or user.first_name,
                    "picture": google_account.picture,
                }
            }),
        })
    except Exception:
        return Response(
            {"error": "Google authentication failed."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


def _get_staff_data(user):
    """Helper to build staff data with roles and hospitals."""
    try:
        staff_profile = user.staff_profile
    except StaffProfile.DoesNotExist:
        return None

    if not staff_profile.is_active_staff:
        return None

    # Get active hospital memberships
    memberships = StaffHospitalMembership.objects.filter(
        staff=staff_profile,
        is_active=True
    ).select_related("hospital", "department")

    roles = [staff_profile.role]
    hospitals = []

    for membership in memberships:
        if membership.role not in roles:
            roles.append(membership.role)
        hospitals.append({
            "id": membership.hospital.id,
            "name": membership.hospital.name,
            "role": membership.role,
            "department": membership.department.name if membership.department else None,
        })

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "staff_role": staff_profile.role,
        "employee_id": staff_profile.employee_id,
        "phone": staff_profile.phone,
        "roles": roles,
        "hospitals": hospitals,
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def staff_login(request):
    """
    Staff login with username/email and password.
    Returns JWT access and refresh tokens with user info, roles, and hospitals.
    """
    username = request.data.get("username") or request.data.get("email")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Username/email and password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Authenticate using Django's authenticate (supports username or email)
    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {"error": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "Account is disabled."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Check if user has staff profile
    staff_data = _get_staff_data(user)
    if staff_data is None:
        return Response(
            {"error": "Not authorized as staff."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    # Add custom claims to access token
    access["staff_id"] = user.id
    access["staff_role"] = staff_data["staff_role"]
    access["roles"] = staff_data["roles"]
    access["hospitals"] = [h["id"] for h in staff_data["hospitals"]]

    return Response({
        "access": str(access),
        "refresh": str(refresh),
        "user": staff_data,
        "roles": staff_data["roles"],
        "hospitals": staff_data["hospitals"],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def staff_login_start_otp(request):
    """
    Staff login step 1: Validate credentials and start OTP verification.
    Returns otp_required: true and a temporary auth state if credentials are valid.
    """
    username = request.data.get("username") or request.data.get("email")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Username/email and password are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {"error": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "Account is disabled."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    staff_data = _get_staff_data(user)
    if staff_data is None:
        return Response(
            {"error": "Not authorized as staff."},
            status=status.HTTP_403_FORBIDDEN
        )

    phone = staff_data.get("phone")
    if not phone:
        return Response(
            {"error": "No mobile number registered for this staff account."},
            status=status.HTTP_400_BAD_REQUEST
        )

    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return Response(
            {"error": "Invalid mobile number format."},
            status=status.HTTP_400_BAD_REQUEST
        )

    otp_provider = getattr(settings, "OTP_PROVIDER", "twilio")
    if otp_provider != "twilio":
        return Response(
            {"error": "OTP service not configured for production."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    verify_service = get_twilio_verify_service()
    if not verify_service.is_configured():
        return Response(
            {"error": "Twilio Verify is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    result = verify_service.start_verification(normalized_phone, channel="sms")
    if not result.ok:
        return Response(
            {"error": result.message},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    masked_phone = f"******{normalized_phone[-4:]}" if len(normalized_phone) >= 4 else "****"
    return Response({
        "otp_required": True,
        "message": f"OTP sent to your registered mobile number ({masked_phone}).",
        "user_id": user.id,
        "staff_role": staff_data["staff_role"],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def staff_otp_verify(request):
    """
    Staff login step 2: Verify OTP and issue JWT tokens.
    """
    user_id = request.data.get("user_id")
    otp = request.data.get("otp")

    if not user_id or not otp:
        return Response(
            {"error": "User ID and OTP are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return Response(
            {"error": "Invalid user."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    staff_data = _get_staff_data(user)
    if staff_data is None:
        return Response(
            {"error": "Not authorized as staff."},
            status=status.HTTP_403_FORBIDDEN
        )

    phone = staff_data.get("phone")
    if not phone:
        return Response(
            {"error": "No mobile number registered for this staff account."},
            status=status.HTTP_400_BAD_REQUEST
        )

    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return Response(
            {"error": "Invalid mobile number format."},
            status=status.HTTP_400_BAD_REQUEST
        )

    verify_service = get_twilio_verify_service()
    if not verify_service.is_configured():
        return Response(
            {"error": "Twilio Verify is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    result = verify_service.check_verification(normalized_phone, otp)
    if not result.ok:
        code = status.HTTP_401_UNAUTHORIZED
        if "too many" in result.message.lower() or "rate limit" in result.message.lower():
            code = status.HTTP_429_TOO_MANY_REQUESTS
        return Response(
            {"error": result.message},
            status=code
        )

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access["staff_id"] = user.id
    access["staff_role"] = staff_data["staff_role"]
    access["roles"] = staff_data["roles"]
    access["hospitals"] = [h["id"] for h in staff_data["hospitals"]]

    return Response({
        "access": str(access),
        "refresh": str(refresh),
        "user": staff_data,
        "roles": staff_data["roles"],
        "hospitals": staff_data["hospitals"],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def staff_otp_resend(request):
    """
    Resend OTP for staff login with cooldown and rate limiting.
    """
    user_id = request.data.get("user_id")

    if not user_id:
        return Response(
            {"error": "User ID is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return Response(
            {"error": "Invalid user."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    staff_data = _get_staff_data(user)
    if staff_data is None:
        return Response(
            {"error": "Not authorized as staff."},
            status=status.HTTP_403_FORBIDDEN
        )

    phone = staff_data.get("phone")
    if not phone:
        return Response(
            {"error": "No mobile number registered for this staff account."},
            status=status.HTTP_400_BAD_REQUEST
        )

    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return Response(
            {"error": "Invalid mobile number format."},
            status=status.HTTP_400_BAD_REQUEST
        )

    from notifications.models import OTPVerification
    from django.utils import timezone
    from datetime import timedelta

    cooldown = timedelta(seconds=60)
    recent = OTPVerification.objects.filter(
        phone=normalized_phone,
        channel="sms",
        created_at__gte=timezone.now() - cooldown
    ).first()

    if recent:
        return Response(
            {"error": "Please wait before requesting another OTP."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    verify_service = get_twilio_verify_service()
    if not verify_service.is_configured():
        return Response(
            {"error": "Twilio Verify is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    result = verify_service.start_verification(normalized_phone, channel="sms")
    if not result.ok:
        return Response(
            {"error": result.message},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    masked_phone = f"******{normalized_phone[-4:]}" if len(normalized_phone) >= 4 else "****"
    return Response({
        "message": f"OTP resent to your registered mobile number ({masked_phone}).",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def staff_logout(request):
    """
    Staff logout - blacklists the refresh token.
    """
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return Response(
            {"error": "Refresh token is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Successfully logged out."})
    except TokenError:
        return Response(
            {"error": "Invalid or expired refresh token."},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_me(request):
    """
    Get current authenticated staff user info with roles and hospitals.
    """
    staff_data = _get_staff_data(request.user)

    if staff_data is None:
        return Response(
            {"error": "Not authorized as staff."},
            status=status.HTTP_403_FORBIDDEN
        )

    return Response({
        "user": staff_data,
        "roles": staff_data["roles"],
        "hospitals": staff_data["hospitals"],
    })


SELF_REGISTER_ROLES = {
    "Patient",
    "Doctor",
    "Nurse",
    "Compounder",
    "Receptionist",
    "Admin",
}

STAFF_SELF_REGISTER_ROLES = {
    StaffRole.DOCTOR,
    StaffRole.NURSE,
    StaffRole.COMPOUNDER,
    StaffRole.RECEPTIONIST,
}


def _age_from_dob(dob_value):
    if not dob_value:
        return 1
    try:
        dob = date.fromisoformat(str(dob_value)[:10])
    except ValueError:
        return 1
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(age, 1)


def _unique_username(email, phone):
    if email:
        base = email.split("@")[0][:80]
    elif phone:
        base = f"user_{phone}"
    else:
        base = f"user_{uuid.uuid4().hex[:8]}"

    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}_{suffix}"
        suffix += 1
    return username


@api_view(["POST"])
@permission_classes([AllowAny])
def register_account(request):
    """
    Public registration. Privileged roles are never granted from the
    frontend selector alone:
    - Patient: self-registration, active immediately
    - Doctor/Nurse/Compounder/Receptionist: pending staff until approved
    - Admin: requires ADMIN_INVITE_CODE; otherwise rejected
    """
    data = request.data or {}
    requested_role = str(data.get("role") or "Patient").strip()
    full_name = str(data.get("full_name") or data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    phone = str(data.get("phone") or data.get("mobile") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or data.get("password_confirm") or ""

    if requested_role not in SELF_REGISTER_ROLES:
        return Response(
            {"error": "Invalid role selection."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not full_name:
        return Response(
            {"error": "Full name is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not phone or len("".join(ch for ch in phone if ch.isdigit())) < 10:
        return Response(
            {"error": "A valid 10-digit mobile number is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not password or len(str(password)) < 8:
        return Response(
            {"error": "Password must be at least 8 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if str(password) != str(confirm_password):
        return Response(
            {"error": "Password and confirm password do not match."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if requested_role == "Patient":
        if not email:
            return Response(
                {"error": "A valid email address is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"error": "A valid email address is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if email and User.objects.filter(email__iexact=email).exists():
        return Response(
            {"error": "Account already exists with this email."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    normalized_phone = normalize_phone(phone)
    if Patient.objects.filter(phone__endswith=normalized_phone).exists():
        return Response(
            {"error": "Account already exists with this mobile number."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0][:150]
    last_name = name_parts[1][:150] if len(name_parts) > 1 else ""

    if requested_role == "Admin":
        expected = (getattr(settings, "ADMIN_INVITE_CODE", "") or "").strip()
        invite = str(data.get("invite_code") or data.get("admin_invite_code") or "").strip()
        if not expected or invite != expected:
            return Response(
                {
                    "error": (
                        "Admin accounts cannot be self-registered. "
                        "Use an admin invitation code or ask an existing administrator."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    dob_raw = data.get("date_of_birth") or data.get("dob") or ""
    dob_value = None
    if requested_role == "Patient" and dob_raw:
        try:
            dob_value = date.fromisoformat(str(dob_raw)[:10])
        except ValueError:
            return Response(
                {"error": "Date of birth is not valid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    created_patient = None
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=_unique_username(email, phone),
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            if requested_role == "Patient":
                gender = str(data.get("gender") or "Other").strip() or "Other"
                created_patient = Patient.objects.create(
                    user=user,
                    name=full_name[:100],
                    age=_age_from_dob(dob_raw),
                    gender=gender[:20],
                    phone=normalized_phone[:15],
                    address=str(data.get("address") or ""),
                    date_of_birth=dob_value,
                    doctor="",
                    email_verified=False,
                    phone_verified=False,
                    status="Active",
                )
            else:
                staff_role = requested_role
                is_active = requested_role == "Admin"
                employee_id = str(data.get("employee_id") or data.get("staff_id") or "").strip()
                if not employee_id:
                    employee_id = f"EMP-{uuid.uuid4().hex[:10].upper()}"

                while StaffProfile.objects.filter(employee_id=employee_id).exists():
                    employee_id = f"EMP-{uuid.uuid4().hex[:10].upper()}"

                StaffProfile.objects.create(
                    user=user,
                    role=staff_role,
                    phone=normalized_phone[:15],
                    employee_id=employee_id,
                    license_number=str(
                        data.get("license_number") or data.get("nursing_registration") or ""
                    ).strip()[:100],
                    specialization=str(data.get("specialization") or "").strip()[:100],
                    department_name=str(data.get("department") or "").strip()[:100],
                    years_experience=str(data.get("experience") or "").strip()[:20],
                    is_active_staff=is_active,
                )

                if requested_role == "Admin":
                    message = "Admin account created. You can now sign in with your username and password."
                else:
                    message = (
                        f"{requested_role} registration received. "
                        "The account is pending hospital approval and does not have "
                        f"{requested_role} access until an administrator activates it."
                    )

                return Response(
                    {
                        "status": "success",
                        "pending_approval": not is_active,
                        "role": requested_role,
                        "message": message,
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "name": full_name,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
    except Exception:
        logger.exception("Account registration failed")
        return Response(
            {"error": "Account registration failed."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    email_status, email_message, email_delivery = send_email_otp(email, purpose="verify_email")
    verification = {
        "channel": "email",
        "sent": email_status == "pending" and email_delivery in ("email", "console"),
        "delivery": email_delivery,
        "message": email_message,
    }
    return Response(
        {
            "status": "success",
            "pending_approval": False,
            "role": "Patient",
            "message": "Patient account created. Verify your email before signing in.",
            "email_verified": False,
            "phone_verified": False,
            "verification": verification,
            "user": {
                "id": created_patient.user_id,
                "username": created_patient.user.username,
                "email": email,
                "name": full_name,
            },
            "patient": {
                "id": created_patient.id,
                "name": created_patient.name,
                "age": created_patient.age,
                "gender": created_patient.gender,
                "phone": created_patient.phone,
                "email": email,
            },
        },
        status=status.HTTP_201_CREATED,
    )


def _otp_response(status_name, message, delivery=None):
    if status_name == "invalid":
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
    if status_name == "limited":
        return Response({"error": message}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    if status_name == "unavailable":
        return Response({"error": message, "delivery": delivery}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    body = {"status": "pending", "message": message}
    if delivery:
        body["delivery"] = delivery
    return Response(body)


@api_view(["POST"])
@permission_classes([AllowAny])
def patient_otp_request(request):
    status_name, message, delivery = request_patient_otp(
        request.data.get("phone") or request.data.get("mobile")
    )
    return _otp_response(status_name, message, delivery)


@api_view(["POST"])
@permission_classes([AllowAny])
def patient_otp_verify(request):
    patient, error = verify_patient_otp(
        request.data.get("phone") or request.data.get("mobile"),
        request.data.get("otp"),
    )
    if error or patient is None or patient.user is None:
        code = status.HTTP_401_UNAUTHORIZED
        if error == "Too many OTP requests. Please try again later.":
            code = status.HTTP_429_TOO_MANY_REQUESTS
        return Response({"error": error or "Invalid OTP."}, status=code)
    return Response({
        "status": "success",
        **_auth_response(patient.user, patient),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def patient_email_otp_request(request):
    status_name, message, delivery = send_email_otp(
        request.data.get("email"),
        purpose="verify_email",
    )
    return _otp_response(status_name, message, delivery)


@api_view(["POST"])
@permission_classes([AllowAny])
def patient_email_otp_verify(request):
    patient, error = verify_email_otp(request.data.get("email"), request.data.get("otp"))
    if error or patient is None:
        code = status.HTTP_401_UNAUTHORIZED
        if error == "Too many OTP requests. Please try again later.":
            code = status.HTTP_429_TOO_MANY_REQUESTS
        return Response({"error": error or "Invalid OTP."}, status=code)
    return Response({
        "status": "success",
        "email_verified": True,
        "message": "Email verified. You can now sign in with your email and password.",
        "patient": {
            "id": patient.id,
            "email": patient.user.email if patient.user else "",
        },
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def patient_email_login(request):
    patient, error, http_status = authenticate_patient_email(
        request.data.get("email"),
        request.data.get("password") or "",
    )
    if patient is None:
        return Response({"error": error}, status=http_status)
    return Response({
        "status": "success",
        **_auth_response(patient.user, patient),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def patient_token_login(request):
    patient = authenticate_patient_identifier(
        request.data.get("identifier") or request.data.get("token") or request.data.get("patient_id"),
        request.data.get("password") or "",
    )
    if patient is None or patient.user is None:
        return Response(
            {"error": "Invalid patient credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return Response({
        "status": "success",
        **_auth_response(patient.user, patient),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def patient_me(request):
    patient = getattr(request.user, "patient_account", None)
    if patient is None:
        return Response(
            {"error": "Not authorized as a patient."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response({
        "role": "Patient",
        "patient": patient_payload(patient),
        "user": {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
        },
    })
