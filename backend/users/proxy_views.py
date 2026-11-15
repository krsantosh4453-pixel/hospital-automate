"""
Family / caregiver (proxy) access endpoints.

Patients add and revoke family members under /api/auth/patient/family-access/.
Family members sign in with their own mobile number:
  1. POST /api/auth/proxy/otp/request/  {phone}
  2. POST /api/auth/proxy/otp/verify/   {phone, otp}      -> grants + ticket
  3. POST /api/auth/proxy/login/        {ticket, grant}   -> tokens (view-only)
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from audit.services import record_audit
from patients.models import ProxyAccess
from users.patient_auth import normalize_phone, patient_payload
from users.permissions import is_active_staff
from users.proxy_access import (
    MAX_ACTIVE_GRANTS,
    get_proxy_grant,
    grant_payload,
    issue_proxy_tokens,
    login_choice_payload,
    make_ticket,
    proxy_payload,
    proxy_user_for,
    read_ticket,
    request_proxy_otp,
    verify_proxy_otp,
)

NAME_MAX = 100
RELATIONSHIP_MAX = 50


def _owning_patient(request):
    """The patient managing their own family access, or None."""
    user = request.user
    if get_proxy_grant(user) is not None or is_active_staff(user):
        return None
    return getattr(user, "patient_account", None)


def _forbidden():
    return Response(
        {"error": "Only the patient can manage family access."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _validate_grant_input(data):
    name = str(data.get("name") or "").strip()
    relationship = str(data.get("relationship") or "").strip()
    phone = normalize_phone(data.get("phone"))
    errors = {}
    if not name or len(name) > NAME_MAX:
        errors["name"] = f"Enter the family member's name (up to {NAME_MAX} characters)."
    if not relationship or len(relationship) > RELATIONSHIP_MAX:
        errors["relationship"] = f"Enter the relationship (up to {RELATIONSHIP_MAX} characters)."
    if not phone:
        errors["phone"] = "Enter a valid 10-digit mobile number."
    return name, relationship, phone, errors


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def family_access(request):
    patient = _owning_patient(request)
    if patient is None:
        return _forbidden()

    active = patient.proxy_grants.filter(revoked_at__isnull=True)
    if request.method == "GET":
        return Response([grant_payload(grant) for grant in active])

    name, relationship, phone, errors = _validate_grant_input(request.data)
    if errors:
        return Response({"error": " ".join(errors.values()), "details": errors}, status=status.HTTP_400_BAD_REQUEST)
    if active.count() >= MAX_ACTIVE_GRANTS:
        return Response(
            {"error": f"You can give family access to at most {MAX_ACTIVE_GRANTS} people. Remove one first."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        with transaction.atomic():
            grant = ProxyAccess.objects.create(
                patient=patient, name=name, relationship=relationship, phone=phone
            )
    except IntegrityError:
        return Response(
            {"error": "This mobile number already has family access."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    record_audit(request, "patients.proxy_access.grant", grant, hospital=patient.hospital_id)
    return Response(grant_payload(grant), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def revoke_family_access(request, grant_id):
    patient = _owning_patient(request)
    if patient is None:
        return _forbidden()
    grant = patient.proxy_grants.filter(pk=grant_id, revoked_at__isnull=True).first()
    if grant is None:
        return Response({"error": "Family access not found."}, status=status.HTTP_404_NOT_FOUND)
    grant.revoked_at = timezone.now()
    grant.save(update_fields=["revoked_at"])
    record_audit(request, "patients.proxy_access.revoke", grant, hospital=patient.hospital_id)
    return Response(grant_payload(grant))


@api_view(["POST"])
@permission_classes([AllowAny])
def proxy_otp_request(request):
    from users.views import _otp_response

    status_name, message, delivery = request_proxy_otp(
        request.data.get("phone") or request.data.get("mobile")
    )
    return _otp_response(status_name, message, delivery)


@api_view(["POST"])
@permission_classes([AllowAny])
def proxy_otp_verify(request):
    phone, grants, error = verify_proxy_otp(
        request.data.get("phone") or request.data.get("mobile"),
        request.data.get("otp"),
    )
    if error:
        return Response({"error": error}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({
        "ticket": make_ticket(phone),
        "grants": [login_choice_payload(grant) for grant in grants],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def proxy_login(request):
    phone = read_ticket(request.data.get("ticket"))
    if not phone:
        return Response(
            {"error": "Your sign-in has expired. Request a new code."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    grant = (
        ProxyAccess.objects.select_related("patient")
        .filter(pk=request.data.get("grant"), phone=phone, revoked_at__isnull=True)
        .first()
    )
    user = proxy_user_for(phone) if grant is not None else None
    if grant is None or user is None:
        return Response(
            {"error": "This family access is not available for your mobile number."},
            status=status.HTTP_403_FORBIDDEN,
        )
    grant.proxy_user = user
    grant.last_used_at = timezone.now()
    grant.save(update_fields=["proxy_user", "last_used_at"])
    record_audit(request, "auth.proxy.login", grant, hospital=grant.patient.hospital_id, user=user)
    return Response({
        "status": "success",
        "account_type": "patient",
        "role": "Patient",
        "user": {"id": user.id, "username": user.username, "name": grant.name},
        "patient": patient_payload(grant.patient),
        "proxy": proxy_payload(grant),
        **issue_proxy_tokens(user, grant, request),
    })
