"""
P1-03 (DPDP Act 2023): data-principal requests and the privacy notice.

    GET  /api/consent/rights-requests/                 patient: own; Admin/Manager: their hospitals' (?status=)
    POST /api/consent/rights-requests/                 patient: {hospital, kind, details}
    POST /api/consent/rights-requests/<id>/respond/    Admin/Manager: {status, response}
    GET  /api/consent/privacy-notice/?hospital=<id>    grievance officer and response time

Requests are answered by people, not executed by the system: erasure in
particular is weighed against medical-record retention duties, and the reason
is written in the response.
"""

from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from hospital.models import Hospital
from users.models import StaffRole
from users.permissions import (
    get_linked_patient,
    get_request_hospital_id,
    get_user_hospital_ids,
    get_user_roles,
    is_active_staff,
)

from .models import DataRightsRequest
from .views import _registered

HANDLER_ROLES = {StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER}
MIN_RESPONSE = 10
MAX_ROWS = 200


def _response_days():
    return int(getattr(settings, "DPDP_RESPONSE_DAYS", 30))


def _row(item):
    handler = item.handled_by
    return {
        "id": item.pk, "patient": item.patient_id, "patient_name": item.patient.name,
        "hospital": item.hospital_id, "hospital_name": item.hospital.name,
        "kind": item.kind, "kind_label": item.get_kind_display(), "details": item.details,
        "status": item.status, "response": item.response,
        "created_at": item.created_at, "due_at": item.due_at, "closed_at": item.closed_at,
        "overdue": item.overdue,
        "handled_by_name": (handler.get_full_name() or handler.username) if handler else "",
    }


def _handler_hospitals(request):
    """Acting hospitals where this user is an Admin or Hospital Manager."""
    allowed = get_user_hospital_ids(request.user)
    acting = get_request_hospital_id(request)
    hospitals = [acting] if acting is not None and acting in allowed else ([] if acting is not None else allowed)
    return [h for h in hospitals if set(get_user_roles(request.user, h)) & HANDLER_ROLES]


class RightsRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = DataRightsRequest.objects.select_related("patient", "hospital", "handled_by")
        if is_active_staff(request.user):
            hospitals = _handler_hospitals(request)
            if not hospitals:
                raise PermissionDenied("Only an Admin or Hospital Manager handles data requests.")
            rows = rows.filter(hospital_id__in=hospitals)
        else:
            patient = get_linked_patient(request.user)
            if patient is None:
                raise PermissionDenied("Patient or staff account required.")
            rows = rows.filter(patient=patient)
        wanted = request.query_params.get("status")
        if wanted:
            rows = rows.filter(status__in=wanted.split(","))
        return Response({"results": [_row(item) for item in rows[:MAX_ROWS]]})

    def post(self, request):
        patient = get_linked_patient(request.user)
        if patient is None or is_active_staff(request.user):
            raise PermissionDenied("Requests are made by the patient from the patient portal.")
        kind = str(request.data.get("kind") or "")
        if kind not in DataRightsRequest.Kind.values:
            raise ValidationError({"kind": "Choose what you are asking for."})
        try:
            hospital_id = int(request.data.get("hospital"))
        except (TypeError, ValueError):
            raise ValidationError({"hospital": "Choose the hospital."})
        if not _registered(patient, hospital_id):
            raise ValidationError({"hospital": "Choose a hospital you are registered at."})
        item = DataRightsRequest.objects.create(
            patient=patient, hospital_id=hospital_id, kind=kind,
            details=str(request.data.get("details") or "").strip()[:2000],
            due_at=timezone.now() + timedelta(days=_response_days()),
        )
        record_audit(request, "consent.rights_request.create", item, hospital=hospital_id,
                     details={"kind": kind, "patient_id": patient.pk})
        return Response(_row(item), status=status.HTTP_201_CREATED)


class RightsRequestRespondView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        if not is_active_staff(request.user):
            raise PermissionDenied("Only hospital staff answer data requests.")
        hospitals = _handler_hospitals(request)
        if not hospitals and get_user_hospital_ids(request.user):
            raise PermissionDenied("Only an Admin or Hospital Manager answers data requests.")
        item = get_object_or_404(DataRightsRequest.objects.select_related("patient", "hospital"),
                                 pk=id, hospital_id__in=hospitals)
        new_status = str(request.data.get("status") or "")
        if new_status not in (DataRightsRequest.Status.IN_PROGRESS, DataRightsRequest.Status.COMPLETED,
                              DataRightsRequest.Status.REFUSED):
            raise ValidationError({"status": "Choose in progress, completed or refused."})
        answer = str(request.data.get("response") or "").strip()
        closing = new_status != DataRightsRequest.Status.IN_PROGRESS
        if closing and len(answer) < MIN_RESPONSE:
            raise ValidationError({"response": f"Tell the patient what was done or why not ({MIN_RESPONSE}+ characters)."})
        item.status = new_status
        item.response = answer[:2000] or item.response
        item.handled_by = request.user
        item.closed_at = timezone.now() if closing else None
        item.save(update_fields=["status", "response", "handled_by", "closed_at"])
        record_audit(request, "consent.rights_request.respond", item, hospital=item.hospital_id,
                     details={"kind": item.kind, "status": new_status})
        return Response(_row(item))


class PrivacyNoticeView(APIView):
    """The hospital's grievance officer and how long an answer may take."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            hospital = Hospital.objects.get(pk=int(request.query_params.get("hospital")))
        except (Hospital.DoesNotExist, TypeError, ValueError):
            raise ValidationError({"hospital": "Choose the hospital."})
        return Response({
            "hospital": hospital.pk,
            "hospital_name": hospital.name,
            "grievance_officer": {
                "name": hospital.grievance_officer_name,
                "email": hospital.grievance_officer_email,
                "phone": hospital.grievance_officer_phone,
            },
            "response_days": _response_days(),
            "kinds": [{"value": value, "label": label} for value, label in DataRightsRequest.Kind.choices],
        })
