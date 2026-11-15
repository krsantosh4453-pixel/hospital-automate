from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from patients.models import Patient
from .models import Consent, Notification, NotificationDelivery, OTPVerification, VoiceCallFallback
from .serializers import (
    ConsentSerializer,
    NotificationDeliverySerializer,
    NotificationSerializer,
    OTPVerificationSerializer,
    VoiceCallFallbackSerializer,
)
from users.viewsets import HospitalScopedViewSet, ReadOnlyHospitalScopedViewSet
from users.permissions import (
    IsAdmin,
    IsDoctor,
    IsHospitalManager,
    IsLinkedPatient,
    IsNurse,
    IsPatientReadOnly,
    IsReceptionist,
    get_linked_patient,
    get_request_hospital_id,
    is_active_staff,
)
from users.platform import has_platform_permission

STAFF = IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsNurse


class NotificationViewSet(HospitalScopedViewSet):
    """In-app notifications: sent by the engine, or written by staff to a patient
    of their hospital (tenancy-checked and audited by the base class)."""

    serializer_class = NotificationSerializer
    permission_classes = [STAFF | IsPatientReadOnly]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if getattr(self, "action", None) == "mark_read":
            return [(STAFF | IsLinkedPatient)()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset().order_by("-created_at")
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(self.get_serializer(notification).data)


class TwilioStatusView(APIView):
    """
    POST /api/notifications/twilio/status/: Twilio's message status callback
    (P1-09). Only requests signed with this account's auth token are accepted;
    it never needs a login and is not throttled, as Twilio sends one per message.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    FINAL = {"delivered": NotificationDelivery.Status.DELIVERED,
             "failed": NotificationDelivery.Status.FAILED,
             "undelivered": NotificationDelivery.Status.FAILED}

    def post(self, request):
        from django.conf import settings
        from twilio.request_validator import RequestValidator

        token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
        url = getattr(settings, "TWILIO_STATUS_CALLBACK_URL", "") or request.build_absolute_uri()
        params = request.POST.dict()
        signature = request.headers.get("X-Twilio-Signature", "")
        if not token or not RequestValidator(token).validate(url, params, signature):
            return Response({"error": "Signature not valid."}, status=status.HTTP_403_FORBIDDEN)

        outcome = self.FINAL.get(params.get("MessageStatus", ""))
        sid = params.get("MessageSid", "")
        if outcome and sid:
            changes = {"status": outcome}
            if outcome == NotificationDelivery.Status.FAILED:
                changes["error"] = f"Twilio error {params.get('ErrorCode') or 'unknown'}"[:255]
            NotificationDelivery.objects.filter(provider_message_id=sid).update(**changes)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationDeliveryViewSet(ReadOnlyHospitalScopedViewSet):
    """Delivery history per channel (sent / failed / skipped), for audit and follow-up."""

    serializer_class = NotificationDeliverySerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsNurse]

    def get_queryset(self):
        qs = super().get_queryset().select_related("patient")
        for param in ("patient", "status", "channel", "event"):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{f"{param}_id" if param == "patient" else param: value})
        return qs


class VoiceCallFallbackViewSet(ReadOnlyHospitalScopedViewSet):
    """Voice calls queued after SMS/WhatsApp delivery failed (queued / placed / failed / skipped)."""

    queryset = VoiceCallFallback.objects.select_related("patient")
    serializer_class = VoiceCallFallbackSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsNurse]

    def get_queryset(self):
        qs = super().get_queryset()
        for param in ("status", "event"):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{param: value})
        patient_id = self.request.query_params.get("patient")
        return qs.filter(patient_id=patient_id) if patient_id else qs


class ConsentViewSet(HospitalScopedViewSet):
    """
    Communication consent (SMS / WhatsApp / voice / email) per hospital.
    Rows are append-only: grant and revoke add a row and the newest answer
    for a purpose is the one the notification engine honours.
    """

    serializer_class = ConsentSerializer
    permission_classes = [STAFF | IsPatientReadOnly]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if getattr(self, "action", None) in {"grant", "revoke", "check"}:
            return [IsAuthenticated(), (STAFF | IsLinkedPatient)()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Use grant/ or revoke/."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def get_queryset(self):
        qs = super().get_queryset().order_by("-created_at", "-id")
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs

    def _target(self, request):
        purpose = str(request.data.get("purpose") or request.query_params.get("purpose") or "").strip()
        if not purpose or len(purpose) > 200:
            raise ValidationError({"purpose": "A consent purpose such as 'notifications_sms' is required."})
        hospital_id = get_request_hospital_id(request, self)
        linked = get_linked_patient(request.user)
        if linked is not None and not is_active_staff(request.user):
            patient = linked
        else:
            patient_id = request.data.get("patient") or request.query_params.get("patient")
            patient = Patient.objects.filter(pk=patient_id).first() if str(patient_id or "").isdigit() else None
            if patient is None:
                raise ValidationError({"patient": "Patient is required."})
            if hospital_id is None or hospital_id not in self.get_acting_hospital_ids():
                raise ValidationError({"hospital": "Select a hospital you belong to."})
        if hospital_id is None:
            raise ValidationError({"hospital": "Select the hospital this consent is for."})
        registered = patient.hospital_id == hospital_id or patient.hospital_memberships.filter(
            hospital_id=hospital_id, is_active=True
        ).exists()
        if not registered:
            raise ValidationError({"patient": "Patient is not registered at this hospital."})
        return patient, hospital_id, purpose

    def _record(self, request, granted):
        patient, hospital_id, purpose = self._target(request)
        consent = Consent.objects.create(patient=patient, hospital_id=hospital_id, purpose=purpose, granted=granted)
        record_audit(request, f"notifications.consent.{'granted' if granted else 'revoked'}", consent,
                     hospital=hospital_id, details={"purpose": purpose})
        return Response(ConsentSerializer(consent).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def grant(self, request):
        return self._record(request, True)

    @action(detail=False, methods=["post"])
    def revoke(self, request):
        return self._record(request, False)

    @action(detail=False, methods=["get"])
    def check(self, request):
        patient, hospital_id, purpose = self._target(request)
        latest = Consent.objects.filter(patient=patient, hospital_id=hospital_id, purpose=purpose).order_by(
            "-created_at", "-id"
        ).first()
        return Response({"purpose": purpose, "granted": bool(latest and latest.granted),
                         "recorded_at": latest.created_at if latest else None})


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_platform_permission(request.user, "platform.otp_log.view")


class OTPVerificationViewSet(viewsets.ReadOnlyModelViewSet):
    """OTP rows hold phone numbers across hospitals: platform administrators only."""

    serializer_class = OTPVerificationSerializer
    permission_classes = [IsPlatformAdmin]
    queryset = OTPVerification.objects.all().order_by("-created_at")
