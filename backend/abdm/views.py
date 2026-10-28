"""
ABDM / ABHA endpoints, mounted at /api/abdm/.

Built: link a patient's existing ABHA after an OTP check with ABDM (M1).
Not built: ABHA creation, consent manager, health-record sharing (M2/M3).

Flow for the registration desk:
  1. POST abha/request-otp  {patient, abha_number, otp_system}  -> {txn_id}
  2. POST abha/confirm-otp  {txn_id, otp}                       -> the saved link
The pending check lives in the cache for OTP_WINDOW_SECONDS and is bound to
the staff member, hospital, patient and ABHA number that started it.
"""

import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from patients.models import Patient
from users.models import StaffRole
from users.permissions import RoleBasedPermission, get_request_hospital_id, user_has_hospital_access

from .client import ABDMClient, ABDMError, ABDMNotConfigured, OTP_SCOPES, digits, is_configured
from .models import ABHALink

logger = logging.getLogger(__name__)

OTP_WINDOW_SECONDS = 10 * 60
ABHA_NUMBER_DIGITS = 14
PENDING_KEY = "abdm:pending:{}"


class CanLinkABHA(RoleBasedPermission):
    """Registration desk, doctors and admins may verify and link an ABHA."""
    required_roles = [StaffRole.RECEPTIONIST, StaffRole.DOCTOR, StaffRole.ADMIN]


def format_abha_number(value):
    raw = digits(value)
    return f"{raw[:2]}-{raw[2:6]}-{raw[6:10]}-{raw[10:]}"


def mask_abha_number(value):
    return f"**-****-****-{digits(value)[-4:]}"


class RequestOTPSerializer(serializers.Serializer):
    patient = serializers.IntegerField()
    abha_number = serializers.CharField(max_length=20)
    otp_system = serializers.ChoiceField(choices=list(OTP_SCOPES), default="aadhaar")

    def validate_abha_number(self, value):
        if len(digits(value)) != ABHA_NUMBER_DIGITS:
            raise serializers.ValidationError("An ABHA number has 14 digits, e.g. 91-1234-5678-9012.")
        return format_abha_number(value)


class ConfirmOTPSerializer(serializers.Serializer):
    txn_id = serializers.CharField(max_length=100)
    otp = serializers.RegexField(r"^\d{4,8}$", error_messages={"invalid": "The OTP is 4 to 8 digits."})


class ABHALinkSerializer(serializers.ModelSerializer):
    verified_by_name = serializers.CharField(source="verified_by.get_full_name", read_only=True, default="")

    class Meta:
        model = ABHALink
        fields = ["id", "patient", "hospital", "abha_number", "abha_address", "name_on_abha",
                  "otp_system", "verified_at", "verified_by_name"]


class ABDMUnavailable(Exception):
    """Raised inside a view when ABDM credentials are missing."""


def _service_unavailable(message):
    return Response({"error": message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


def _bad_gateway(message):
    return Response({"error": message}, status=status.HTTP_502_BAD_GATEWAY)


class ABDMBaseView(APIView):
    permission_classes = [CanLinkABHA]
    throttle_scope = "otp"
    hospital_id = None

    def check_permissions(self, request):
        if not getattr(settings, "ABDM_ENABLED", False):
            raise NotFound("ABDM integration is not enabled on this server.")
        super().check_permissions(request)
        hospital_id = get_request_hospital_id(request, self)
        if hospital_id is None:
            raise ValidationError({"hospital": "Send the X-Hospital-ID header."})
        if not user_has_hospital_access(request.user, hospital_id):
            self.permission_denied(request, message="You do not work at this hospital.")
        self.hospital_id = hospital_id

    def patient_in_hospital(self, patient_id):
        in_hospital = Q(hospital_id=self.hospital_id) | Q(
            hospital_memberships__hospital_id=self.hospital_id, hospital_memberships__is_active=True
        )
        patient = Patient.objects.filter(in_hospital, pk=patient_id).distinct().first()
        if patient is None:
            raise NotFound("Patient not found in this hospital.")
        return patient

    def abdm_client(self):
        try:
            return ABDMClient()
        except ABDMNotConfigured as exc:
            raise ABDMUnavailable(str(exc)) from exc


class StatusView(ABDMBaseView):
    """GET status: whether ABDM is switched on and has credentials (no secrets returned)."""

    throttle_scope = None

    def get(self, request):
        base_url = getattr(settings, "ABDM_BASE_URL", "") or ""
        return Response({
            "enabled": True,
            "configured": is_configured(),
            "gateway_host": urlparse(base_url).hostname or "",
            "built": ["Verify an existing ABHA by OTP and link it to a patient"],
            "not_built": ["Create a new ABHA", "Consent manager", "Share health records (HIP/HIU)"],
        })


class RequestOTPView(ABDMBaseView):
    def post(self, request):
        data = RequestOTPSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        patient = self.patient_in_hospital(data.validated_data["patient"])
        abha_number = data.validated_data["abha_number"]
        otp_system = data.validated_data["otp_system"]
        try:
            txn_id = self.abdm_client().request_login_otp(digits(abha_number), otp_system)
        except ABDMUnavailable as exc:
            return _service_unavailable(str(exc))
        except ABDMError as exc:
            return _bad_gateway(str(exc))

        cache.set(PENDING_KEY.format(txn_id), {
            "user": request.user.pk, "hospital": self.hospital_id, "patient": patient.pk,
            "abha_number": abha_number, "otp_system": otp_system,
        }, OTP_WINDOW_SECONDS)
        record_audit(request, "abdm.abha_otp_requested", obj=patient, hospital=self.hospital_id,
                     details={"abha_number": mask_abha_number(abha_number), "otp_system": otp_system})
        return Response({"txn_id": txn_id, "expires_in_seconds": OTP_WINDOW_SECONDS,
                         "message": "OTP sent to the mobile number linked with this ABHA."})


class ConfirmOTPView(ABDMBaseView):
    def post(self, request):
        data = ConfirmOTPSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        txn_id = data.validated_data["txn_id"]
        pending = cache.get(PENDING_KEY.format(txn_id))
        if not pending or pending["user"] != request.user.pk or pending["hospital"] != self.hospital_id:
            return Response({"error": "This OTP request has expired. Request a new OTP."},
                            status=status.HTTP_400_BAD_REQUEST)
        patient = self.patient_in_hospital(pending["patient"])
        try:
            account = self.abdm_client().verify_login_otp(txn_id, data.validated_data["otp"], pending["otp_system"])
        except ABDMUnavailable as exc:
            return _service_unavailable(str(exc))
        except ABDMError as exc:
            return _bad_gateway(str(exc))
        cache.delete(PENDING_KEY.format(txn_id))

        if digits(account["abha_number"]) != digits(pending["abha_number"]):
            return Response({"error": "ABDM verified a different ABHA number. Nothing was linked."},
                            status=status.HTTP_409_CONFLICT)
        return self._save_link(request, patient, pending, account)

    def _save_link(self, request, patient, pending, account):
        abha_number = pending["abha_number"]
        taken = ABHALink.objects.filter(hospital_id=self.hospital_id, abha_number=abha_number).exclude(patient=patient)
        if taken.exists():
            return Response({"error": "This ABHA is already linked to another patient here. "
                                      "Check for a duplicate registration."},
                            status=status.HTTP_409_CONFLICT)
        try:
            with transaction.atomic():
                link, _ = ABHALink.objects.update_or_create(
                    patient=patient, hospital_id=self.hospital_id,
                    defaults={
                        "abha_number": abha_number,
                        "abha_address": (account.get("abha_address") or "")[:100],
                        "name_on_abha": (account.get("name") or "")[:200],
                        "otp_system": pending["otp_system"],
                        "verified_by": request.user,
                    },
                )
        except IntegrityError:
            return Response({"error": "This ABHA was linked to another patient just now."},
                            status=status.HTTP_409_CONFLICT)
        record_audit(request, "abdm.abha_linked", obj=patient, hospital=self.hospital_id,
                     details={"abha_number": mask_abha_number(abha_number)})
        body = ABHALinkSerializer(link).data
        # Shown so the desk can compare ABDM's record with the registration.
        body["abha_profile"] = {k: account.get(k, "") for k in ("name", "gender", "year_of_birth")}
        return Response(body, status=status.HTTP_201_CREATED)


class LinkListView(ABDMBaseView):
    """GET abha/links?patient=<id>: verified ABHA links in this hospital."""

    throttle_scope = None

    def get(self, request):
        links = ABHALink.objects.filter(hospital_id=self.hospital_id).select_related("verified_by")
        patient_id = request.query_params.get("patient")
        if patient_id:
            if not str(patient_id).isdigit():
                raise ValidationError({"patient": "Patient must be a numeric id."})
            links = links.filter(patient_id=int(patient_id))
        return Response(ABHALinkSerializer(links.order_by("-verified_at")[:200], many=True).data)
