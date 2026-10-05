"""Patient identity checks used by OTP, password, and Google login."""

import hashlib
import hmac
import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.models import OTPVerification
from patients.models import Patient
from users.sms import SMSService, SMS_NOT_CONFIGURED

logger = logging.getLogger(__name__)

User = get_user_model()
OTP_TTL = timedelta(minutes=5)
OTP_ATTEMPT_LIMIT = 5
OTP_REQUEST_LIMIT = 3
OTP_REQUEST_WINDOW = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
EMAIL_SEND_FAILED = "Unable to send verification email. Please check email configuration."


def normalize_phone(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) < 10:
        return ""
    return digits[-10:]


def hash_otp(phone, otp):
    material = f"{normalize_phone(phone)}:{otp}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def hash_email_otp(email, otp):
    material = f"email:{str(email or '').strip().lower()}:{otp}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _new_otp():
    return f"{secrets.randbelow(1000000):06d}"


def _too_many_requests(phone="", email="", channel=""):
    window_start = timezone.now() - OTP_REQUEST_WINDOW
    recent = OTPVerification.objects.filter(created_at__gte=window_start)
    if channel:
        recent = recent.filter(channel=channel)
    if phone:
        recent = recent.filter(phone=phone)
    if email:
        recent = recent.filter(email__iexact=email)
    if recent.count() >= OTP_REQUEST_LIMIT:
        return True
    latest = recent.order_by("-created_at").first()
    if latest and latest.created_at >= timezone.now() - OTP_RESEND_COOLDOWN:
        return True
    return False


def _check_otp_record(record, expected_hash):
    """Return an error message, or None when the code matches."""
    if record is None:
        return "Invalid OTP."
    if record.expires_at < timezone.now():
        return "OTP has expired."
    if record.is_verified:
        return "Invalid OTP."
    if record.attempts >= OTP_ATTEMPT_LIMIT:
        return "Too many OTP requests. Please try again later."
    if not record.otp_hash or not hmac.compare_digest(record.otp_hash, expected_hash):
        record.attempts += 1
        record.save(update_fields=["attempts"])
        return "Invalid OTP."
    record.is_verified = True
    record.save(update_fields=["is_verified"])
    return None


def linked_patients_for_phone(phone):
    normalized = normalize_phone(phone)
    if not normalized:
        return []
    return list(
        Patient.objects.select_related("user").filter(
            user__isnull=False,
            user__is_active=True,
            phone__endswith=normalized,
        )
    )


def request_patient_otp(phone):
    """
    Create a hashed mobile OTP for a registered patient.

    Returns (status, message, delivery). Missing accounts get the same
    pending response as a successful send so phone numbers are not enumerated,
    except when the SMS provider itself is not configured.
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return "invalid", "A valid 10-digit mobile number is required.", None

    patients = linked_patients_for_phone(normalized)
    if not patients:
        mode = getattr(settings, "PATIENT_OTP_DELIVERY", "sms")
        if mode == "sms" and not _sms_provider_configured():
            return "unavailable", SMS_NOT_CONFIGURED, "sms"
        return (
            "pending",
            "If this mobile number is registered, a verification code has been sent.",
            "sms" if mode == "sms" else mode,
        )

    if _too_many_requests(phone=normalized, channel="sms"):
        return "limited", "Too many OTP requests. Please try again later.", None

    otp = _new_otp()
    result = SMSService().send_otp(normalized, otp)
    if not result.ok:
        return "unavailable", result.message, result.delivery

    OTPVerification.objects.create(
        phone=normalized,
        email=patients[0].user.email or "",
        channel="sms",
        purpose="login",
        otp="",
        otp_hash=hash_otp(normalized, otp),
        expires_at=timezone.now() + OTP_TTL,
    )
    if result.delivery == "sms":
        message = "A verification code was sent to your mobile number."
    elif result.delivery == "console":
        message = result.message
    else:
        message = "If this mobile number is registered, a verification code has been sent."
    return "pending", message, result.delivery


def _sms_provider_configured():
    sid = getattr(settings, "TWILIO_ACCOUNT_SID", "") or ""
    token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
    sender = getattr(settings, "TWILIO_PHONE_NUMBER", "") or ""
    return bool(sid and token and sender)


def verify_patient_otp(phone, otp):
    """Return (patient or None, error message or None)."""
    normalized = normalize_phone(phone)
    code = "".join(ch for ch in str(otp or "") if ch.isdigit())
    if not normalized or len(code) != 6:
        return None, "Invalid OTP."

    record = (
        OTPVerification.objects.filter(phone=normalized, channel="sms")
        .order_by("-created_at")
        .first()
    )
    if record is None:
        expired = (
            OTPVerification.objects.filter(phone=normalized, channel="sms")
            .order_by("-created_at")
            .first()
        )
        if expired and expired.expires_at < timezone.now():
            return None, "OTP has expired."
        return None, "Invalid OTP."

    error = _check_otp_record(record, hash_otp(normalized, code))
    if error:
        return None, error

    patients = linked_patients_for_phone(normalized)
    if len(patients) != 1 or not patients[0].user:
        return None, "Invalid OTP."

    patient = patients[0]
    if not patient.phone_verified:
        patient.phone_verified = True
        patient.save(update_fields=["phone_verified"])
    cache.delete(f"patient-otp:{normalized}")
    return patient, None


def _email_backend_is_development():
    backend = getattr(settings, "EMAIL_BACKEND", "")
    return any(name in backend for name in ("console", "locmem", "filebased"))


def send_email_otp(email, purpose="verify_email"):
    """
    Generate, store, and send an email OTP.

    Returns (status, message, delivery). The code is never included.
    """
    address = str(email or "").strip().lower()
    if not address or "@" not in address:
        return "invalid", "A valid email address is required.", None

    user = User.objects.filter(email__iexact=address, is_active=True).first()
    patient = getattr(user, "patient_account", None) if user else None
    if user is None or patient is None:
        return "pending", "If this email is registered, a verification code has been sent.", "email"

    if _too_many_requests(email=address, channel="email"):
        return "limited", "Too many OTP requests. Please try again later.", None

    otp = _new_otp()
    try:
        sent = send_mail(
            subject="Your hospital verification code",
            message=(
                f"Your verification code is {otp}. "
                "It expires in 5 minutes. If you did not request this code, ignore this email."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[address],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Patient email OTP delivery failed")
        return "unavailable", EMAIL_SEND_FAILED, "email"
    if not sent:
        return "unavailable", EMAIL_SEND_FAILED, "email"

    OTPVerification.objects.create(
        phone=normalize_phone(patient.phone),
        email=address,
        channel="email",
        purpose=purpose,
        otp="",
        otp_hash=hash_email_otp(address, otp),
        expires_at=timezone.now() + OTP_TTL,
    )
    if _email_backend_is_development():
        message = (
            "Verification email was written to the development email console. "
            "It was not delivered to an inbox. Check the Django server log."
        )
        delivery = "console"
    else:
        message = "A verification code was sent to your email address."
        delivery = "email"
    return "pending", message, delivery


def verify_email_otp(email, otp):
    """Mark the patient email verified. Returns (patient or None, error or None)."""
    address = str(email or "").strip().lower()
    code = "".join(ch for ch in str(otp or "") if ch.isdigit())
    if not address or len(code) != 6:
        return None, "Invalid OTP."

    record = (
        OTPVerification.objects.filter(email__iexact=address, channel="email")
        .order_by("-created_at")
        .first()
    )
    error = _check_otp_record(record, hash_email_otp(address, code))
    if error:
        return None, error

    user = User.objects.filter(email__iexact=address, is_active=True).first()
    patient = getattr(user, "patient_account", None) if user else None
    if patient is None:
        return None, "Invalid OTP."
    if not patient.email_verified:
        patient.email_verified = True
        patient.save(update_fields=["email_verified"])
    return patient, None


def authenticate_patient_email(email, password):
    """
    Return (patient, error_message, status_code).

    Password checks use Django's hasher. A missing account and a wrong
    password share the same message.
    """
    address = str(email or "").strip().lower()
    if not address or not password:
        return None, "Invalid email or password.", 401

    user = User.objects.filter(email__iexact=address, is_active=True).first()
    patient = getattr(user, "patient_account", None) if user else None
    if user is None or patient is None or not user.check_password(password):
        return None, "Invalid email or password.", 401
    if not patient.email_verified:
        return None, "Email is not verified.", 403
    return patient, None, 200


def patients_for_identifier(identifier):
    ident = str(identifier or "").strip()
    if not ident:
        return []

    base = Patient.objects.select_related("user").filter(
        user__isnull=False,
        user__is_active=True,
    )
    phone = normalize_phone(ident)
    if phone and len("".join(ch for ch in ident if ch.isdigit())) >= 10:
        return list(base.filter(phone__endswith=phone))

    if ident.isdigit():
        return list(base.filter(pk=int(ident)))

    by_uhid = list(
        base.filter(hospital_memberships__uhid__iexact=ident).distinct()
    )
    if by_uhid:
        return by_uhid

    user = User.objects.filter(username__iexact=ident).first()
    if user is None and "@" in ident:
        user = User.objects.filter(email__iexact=ident).first()
    patient = getattr(user, "patient_account", None) if user else None
    if patient and patient.user_id:
        return [patient]
    return []


def authenticate_patient_identifier(identifier, password):
    if not password:
        return None
    matches = []
    for patient in patients_for_identifier(identifier):
        user = patient.user
        if user and user.is_active and user.check_password(password):
            matches.append(patient)
    if len(matches) != 1:
        return None
    return matches[0]


def issue_login_tokens(user, patient=None):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access["role"] = "Patient" if patient is not None else ""
    if patient is not None:
        access["patient_id"] = patient.id
    return {"access": str(access), "refresh": str(refresh)}


def patient_payload(patient):
    user = patient.user
    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "phone": patient.phone,
        "email": user.email if user else "",
        "status": patient.status,
        "email_verified": patient.email_verified,
        "phone_verified": patient.phone_verified,
    }


def verify_google_identity(token):
    """
    Verify a Google ID token with Google. Unsigned payloads are rejected.
    """
    expected_audience = (getattr(settings, "GOOGLE_CLIENT_ID", "") or "").strip()
    if not token or not expected_audience:
        return None

    url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode(
        {"id_token": token}
    )
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "HospitalManagementSystem/1.0"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        logger.warning("Google token verification failed")
        return None

    if not isinstance(data, dict):
        return None
    if data.get("aud") != expected_audience:
        return None
    issuer = data.get("iss")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        return None
    if str(data.get("email_verified", "")).lower() not in ("true", "1"):
        return None
    if not data.get("sub") or not data.get("email"):
        return None
    return data


def link_google_patient(user, name, email):
    patient = getattr(user, "patient_account", None)
    if patient:
        return patient

    from users.models import GoogleAccount

    google_account = GoogleAccount.objects.filter(user=user).first()
    if google_account and google_account.patient_id:
        patient = google_account.patient
        if patient.user_id is None:
            patient.user = user
            patient.save(update_fields=["user"])
        return patient

    patient = Patient.objects.create(
        user=user,
        name=(name or email.split("@")[0] or "Patient")[:100],
        age=1,
        gender="Other",
        phone="",
        doctor="",
        status="Active",
        email_verified=True,
    )
    return patient
