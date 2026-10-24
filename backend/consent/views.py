"""
Consent API.

- Consent forms: versioned templates a patient signs at a hospital.
- Record shares: a patient lets another hospital read selected records from
  one hospital until an expiry date; revocation takes effect immediately and
  every recipient read is logged.
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from hospital.models import Hospital
from patients.models import Patient
from users.models import StaffRole
from users.permissions import (
    get_linked_patient,
    get_request_hospital_id,
    get_user_hospital_ids,
    get_user_roles,
    is_active_staff,
)

from .models import CONSENT_FORMS, SHARE_SCOPES, ConsentRecord, RecordShare, RecordShareAccess

MAX_SHARE_DAYS = 365
RECORD_ROLES = {StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER, StaffRole.RECEPTIONIST, StaffRole.DOCTOR, StaffRole.NURSE}
CLINICAL_READ_ROLES = {StaffRole.ADMIN, StaffRole.DOCTOR, StaffRole.NURSE}


def _registered(patient, hospital_id):
    return patient.hospital_id == hospital_id or patient.hospital_memberships.filter(
        hospital_id=hospital_id, is_active=True
    ).exists()


class _Actor:
    """Who is acting: the patient themself, or staff in one acting hospital."""

    def __init__(self, request):
        self.request = request
        self.patient = None
        self.hospital_ids = []
        if is_active_staff(request.user):
            allowed = get_user_hospital_ids(request.user)
            acting = get_request_hospital_id(request)
            if acting is not None and acting not in allowed:
                raise PermissionDenied("You are not a member of that hospital.")
            self.hospital_ids = [acting] if acting is not None else allowed
        else:
            self.patient = get_linked_patient(request.user)
            if self.patient is None:
                raise PermissionDenied("Patient or staff account required.")

    @property
    def is_staff(self):
        return self.patient is None

    def has_role(self, hospital_id, roles):
        return bool(set(get_user_roles(self.request.user, hospital_id)) & roles)

    def patient_for(self, patient_id, hospital_id):
        """Resolve the patient this request concerns, enforcing scope."""
        if not self.is_staff:
            if patient_id not in (None, "", self.patient.pk, str(self.patient.pk)):
                raise NotFound("Patient not found.")
            if hospital_id is None or not _registered(self.patient, hospital_id):
                raise ValidationError({"hospital": "Choose a hospital you are registered at."})
            return self.patient
        if hospital_id not in self.hospital_ids:
            raise PermissionDenied("You are not a member of that hospital.")
        if not self.has_role(hospital_id, RECORD_ROLES):
            raise PermissionDenied("Your role cannot record consent.")
        try:
            patient = Patient.objects.get(pk=int(patient_id))
        except (Patient.DoesNotExist, TypeError, ValueError):
            raise NotFound("Patient not found.")
        if not _registered(patient, hospital_id):
            raise NotFound("Patient not found.")
        return patient


def _hospital_param(request, actor):
    hospital_id = get_request_hospital_id(request)
    if hospital_id is None and actor.is_staff and len(actor.hospital_ids) == 1:
        hospital_id = actor.hospital_ids[0]
    return hospital_id


def _record_payload(record):
    form = CONSENT_FORMS.get(record.form_code, {})
    return {
        "id": record.id,
        "patient": record.patient_id,
        "hospital": record.hospital_id,
        "form": record.form_code,
        "form_name": form.get("name", record.form_code),
        "form_version": record.form_version,
        "signed_name": record.signed_name,
        "signed_by_proxy": record.signed_by_proxy,
        "proxy_relationship": record.proxy_relationship,
        "signed_at": record.signed_at,
        "revoked_at": record.revoked_at,
        "is_active": record.is_active,
    }


def _share_payload(share):
    return {
        "id": share.id,
        "patient": share.patient_id,
        "patient_name": share.patient.name,
        "source_hospital": share.source_hospital_id,
        "source_hospital_name": share.source_hospital.name,
        "recipient_hospital": share.recipient_hospital_id,
        "recipient_hospital_name": share.recipient_hospital.name,
        "scope": share.scope,
        "purpose": share.purpose,
        "expires_at": share.expires_at,
        "created_at": share.created_at,
        "revoked_at": share.revoked_at,
        "is_active": share.is_active,
        "access_count": share.accesses.count(),
    }


class ConsentBaseView(APIView):
    permission_classes = [IsAuthenticated]


# ---------------------------------------------------------------------------
# Consent forms
# ---------------------------------------------------------------------------

class ConsentFormListView(ConsentBaseView):
    def get(self, request):
        return Response({"forms": [{"id": code, **form} for code, form in CONSENT_FORMS.items()]})


class ConsentFormDetailView(ConsentBaseView):
    def get(self, request, id):
        if id not in CONSENT_FORMS:
            raise NotFound("Consent form not found.")
        return Response({"id": id, **CONSENT_FORMS[id]})


class ConsentRecordListView(ConsentBaseView):
    """GET: signed consents in scope. POST: sign a consent form."""

    def get(self, request):
        actor = _Actor(request)
        if actor.is_staff:
            rows = ConsentRecord.objects.filter(hospital_id__in=actor.hospital_ids)
            patient_id = request.query_params.get("patient")
            if patient_id:
                rows = rows.filter(patient_id=patient_id)
        else:
            rows = ConsentRecord.objects.filter(patient=actor.patient)
        return Response({"results": [_record_payload(r) for r in rows[:200]]})

    def post(self, request):
        actor = _Actor(request)
        hospital_id = _hospital_param(request, actor)
        patient = actor.patient_for(request.data.get("patient"), hospital_id)
        code = request.data.get("form")
        if code not in CONSENT_FORMS:
            raise ValidationError({"form": "Unknown consent form."})
        signed_name = str(request.data.get("signed_name") or "").strip()
        if len(signed_name) < 2:
            raise ValidationError({"signed_name": "Type the full name of the person consenting."})
        if not str(request.data.get("confirm", "")).lower() in ("true", "1", "yes"):
            raise ValidationError({"confirm": "The consent text must be read and confirmed."})
        by_proxy = str(request.data.get("signed_by_proxy", "")).lower() in ("true", "1", "yes")
        record = ConsentRecord.objects.create(
            patient=patient,
            hospital_id=hospital_id,
            form_code=code,
            form_version=CONSENT_FORMS[code]["version"],
            signed_name=signed_name[:150],
            signed_by_proxy=by_proxy,
            proxy_relationship=str(request.data.get("proxy_relationship") or "")[:50] if by_proxy else "",
            recorded_by=request.user,
        )
        record_audit(request, "consent.record.signed", record, hospital=hospital_id, details={"form": code})
        return Response(_record_payload(record), status=status.HTTP_201_CREATED)


def _consent_record(request, id):
    actor = _Actor(request)
    rows = (
        ConsentRecord.objects.filter(hospital_id__in=actor.hospital_ids)
        if actor.is_staff else ConsentRecord.objects.filter(patient=actor.patient)
    )
    try:
        return actor, rows.get(pk=int(id))
    except (ConsentRecord.DoesNotExist, TypeError, ValueError):
        raise NotFound("Consent record not found.")


class ConsentRecordDetailView(ConsentBaseView):
    def get(self, request, id):
        return Response(_record_payload(_consent_record(request, id)[1]))


class ConsentRecordRevokeView(ConsentBaseView):
    def post(self, request, id):
        actor, record = _consent_record(request, id)
        if actor.is_staff and not actor.has_role(record.hospital_id, RECORD_ROLES):
            raise PermissionDenied("Your role cannot change consent.")
        if record.revoked_at:
            raise ValidationError("This consent is already revoked.")
        record.revoked_at = timezone.now()
        record.revoked_by = request.user
        record.save(update_fields=["revoked_at", "revoked_by"])
        record_audit(request, "consent.record.revoked", record, hospital=record.hospital_id)
        return Response(_record_payload(record))


# ---------------------------------------------------------------------------
# Record sharing
# ---------------------------------------------------------------------------

class RecordShareListView(ConsentBaseView):
    """GET: shares granted by the patient (or from the acting hospital). POST: grant one."""

    def get(self, request):
        actor = _Actor(request)
        if actor.is_staff:
            rows = RecordShare.objects.filter(source_hospital_id__in=actor.hospital_ids)
        else:
            rows = RecordShare.objects.filter(patient=actor.patient)
        rows = rows.select_related("patient", "source_hospital", "recipient_hospital")
        return Response({"results": [_share_payload(s) for s in rows[:200]], "scopes": SHARE_SCOPES})

    def post(self, request):
        actor = _Actor(request)
        source_id = _hospital_param(request, actor)
        patient = actor.patient_for(request.data.get("patient"), source_id)
        try:
            recipient = Hospital.objects.get(pk=int(request.data.get("recipient_hospital")), is_active=True)
        except (Hospital.DoesNotExist, TypeError, ValueError):
            raise ValidationError({"recipient_hospital": "Choose an active recipient hospital."})
        if recipient.pk == source_id:
            raise ValidationError({"recipient_hospital": "Records are already available at that hospital."})
        scope = request.data.get("scope") or []
        if not isinstance(scope, list) or not scope or any(item not in SHARE_SCOPES for item in scope):
            raise ValidationError({"scope": f"Choose one or more of: {', '.join(SHARE_SCOPES)}."})
        purpose = str(request.data.get("purpose") or "").strip()
        if not purpose:
            raise ValidationError({"purpose": "State why the records are being shared."})
        expires_at = parse_datetime(str(request.data.get("expires_at") or ""))
        now = timezone.now()
        if expires_at is None:
            raise ValidationError({"expires_at": "An expiry date and time is required."})
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at)
        if expires_at <= now or expires_at > now + timedelta(days=MAX_SHARE_DAYS):
            raise ValidationError({"expires_at": f"Expiry must be in the future and within {MAX_SHARE_DAYS} days."})
        if actor.is_staff and not str(request.data.get("patient_confirmed", "")).lower() in ("true", "1", "yes"):
            raise ValidationError({"patient_confirmed": "Confirm the patient agreed to this share."})
        share = RecordShare.objects.create(
            patient=patient,
            source_hospital_id=source_id,
            recipient_hospital=recipient,
            scope=sorted(set(scope)),
            purpose=purpose[:200],
            expires_at=expires_at,
            created_by=request.user,
        )
        record_audit(request, "consent.share.granted", share, hospital=source_id,
                     details={"recipient": recipient.pk, "scope": share.scope})
        return Response(_share_payload(share), status=status.HTTP_201_CREATED)


def _own_share(request, id):
    actor = _Actor(request)
    rows = (
        RecordShare.objects.filter(source_hospital_id__in=actor.hospital_ids)
        if actor.is_staff else RecordShare.objects.filter(patient=actor.patient)
    )
    try:
        return actor, rows.select_related("patient", "source_hospital", "recipient_hospital").get(pk=int(id))
    except (RecordShare.DoesNotExist, TypeError, ValueError):
        raise NotFound("Share not found.")


class RecordShareRevokeView(ConsentBaseView):
    def post(self, request, id):
        actor, share = _own_share(request, id)
        if actor.is_staff and not actor.has_role(share.source_hospital_id, RECORD_ROLES):
            raise PermissionDenied("Your role cannot change consent.")
        if share.revoked_at:
            raise ValidationError("This share is already revoked.")
        share.revoked_at = timezone.now()
        share.revoked_by = request.user
        share.save(update_fields=["revoked_at", "revoked_by"])
        record_audit(request, "consent.share.revoked", share, hospital=share.source_hospital_id)
        return Response(_share_payload(share))


class RecordShareAccessLogView(ConsentBaseView):
    """Who read a share and when — visible to the patient and the source hospital."""

    def get(self, request, id):
        _, share = _own_share(request, id)
        return Response({"results": [
            {"accessed_at": a.accessed_at, "accessed_by": getattr(a.accessed_by, "username", None)}
            for a in share.accesses.select_related("accessed_by")[:200]
        ]})


class ReceivedShareListView(ConsentBaseView):
    """Active shares addressed to the staff member's hospital."""

    def get(self, request):
        actor = _Actor(request)
        if not actor.is_staff:
            raise PermissionDenied("Staff only.")
        rows = RecordShare.objects.filter(
            recipient_hospital_id__in=actor.hospital_ids, revoked_at__isnull=True, expires_at__gt=timezone.now()
        ).select_related("patient", "source_hospital", "recipient_hospital")
        return Response({"results": [_share_payload(s) for s in rows[:200]]})


def shared_records(share):
    """Records of the source hospital covered by the share's scope."""
    from clinical.models import Allergy, Diagnosis, Prescription
    from encounters.models import Visit
    from ipd.models import DischargeSummary
    from laboratory.models import LabTest

    patient_id, hospital_id = share.patient_id, share.source_hospital_id
    data = {}
    if "visits" in share.scope:
        data["visits"] = list(Visit.objects.filter(patient_id=patient_id, hospital_id=hospital_id).values(
            "id", "visit_type", "chief_complaint", "status", "visit_date"))
    if "diagnoses" in share.scope:
        data["diagnoses"] = list(Diagnosis.objects.filter(
            visit__patient_id=patient_id, visit__hospital_id=hospital_id
        ).values("id", "name", "icd10_code", "diagnosis_type", "created_at"))
    if "prescriptions" in share.scope:
        data["prescriptions"] = [
            {"id": p.id, "status": p.status, "created_at": p.created_at,
             "items": list(p.items.values("name", "dosage", "frequency", "duration"))}
            for p in Prescription.objects.filter(patient_id=patient_id, hospital_id=hospital_id).prefetch_related("items")
        ]
    if "lab_results" in share.scope:
        data["lab_results"] = list(LabTest.objects.filter(
            patient_id=patient_id, hospital_id=hospital_id, status="Released"
        ).values("id", "name", "result", "released_at"))
    if "discharge_summaries" in share.scope:
        data["discharge_summaries"] = list(DischargeSummary.objects.filter(
            admission__patient_id=patient_id, admission__hospital_id=hospital_id, finalized=True
        ).values("id", "summary", "finalized_at"))
    if "allergies" in share.scope:
        data["allergies"] = list(Allergy.objects.filter(
            patient_id=patient_id
        ).filter(Q(hospital_id=hospital_id)).values("id", "name", "reaction", "severity"))
    return data


class SharedRecordsView(ConsentBaseView):
    """Recipient clinical staff read the records a patient chose to share."""

    def get(self, request, id):
        actor = _Actor(request)
        if not actor.is_staff:
            raise PermissionDenied("Staff only.")
        try:
            share = RecordShare.objects.select_related("patient", "source_hospital", "recipient_hospital").get(
                pk=int(id), recipient_hospital_id__in=actor.hospital_ids
            )
        except (RecordShare.DoesNotExist, TypeError, ValueError):
            raise NotFound("Share not found.")
        if not actor.has_role(share.recipient_hospital_id, CLINICAL_READ_ROLES):
            raise PermissionDenied("Only clinical staff can read shared records.")
        if not share.is_active:
            record_audit(request, "consent.share.access_denied", share, hospital=share.recipient_hospital_id)
            raise PermissionDenied("This share has been revoked or has expired.")
        RecordShareAccess.objects.create(share=share, accessed_by=request.user)
        record_audit(request, "consent.share.accessed", share, hospital=share.recipient_hospital_id)
        return Response({"share": _share_payload(share), "records": shared_records(share)})
