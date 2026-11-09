"""
Signed clinical records (decision 2 / Q4, 2026-11-09).

A clinical note or diagnosis is a draft that only its author edits. The author
signs it with POST .../{id}/sign/; from then on edits are refused (409) and a
correction is a new record with ``amends`` set, so the signed original stays
as it was. Removing a record stays the audited "entered in error" path, which
keeps the row. Where the hospital requires it (Q2), only a doctor whose
registration the Admin has verified may sign.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response

from audit.services import record_audit
from doctors.models import Doctor


class AlreadySigned(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This record is signed and cannot be changed. Add an amendment instead."
    default_code = "signed"


def require_signing_doctor(user, hospital_id):
    """The user's Doctor profile at this hospital, if it may sign there; otherwise 403."""
    doctor = Doctor.objects.select_related("hospital").filter(user=user, hospital_id=hospital_id).first()
    if doctor is None:
        raise PermissionDenied("Only a doctor of this hospital can sign clinical records.")
    if not doctor.may_sign():
        raise PermissionDenied("This hospital requires a verified registration before you can sign. "
                               "Ask the hospital Admin to verify it.")
    return doctor


def check_amends(data):
    """An amendment corrects a record of the same patient."""
    original, visit = data.get("amends"), data.get("visit")
    if original is not None and visit is not None and original.visit.patient_id != visit.patient_id:
        raise ValidationError({"amends": "An amendment must be for the same patient as the record it corrects."})


class SignedRecordMixin:
    """For HospitalScopedViewSets of clinical records with ``signed_at``/``signed_by``/``amends``."""

    def author_id(self, record):
        """The user id of the record's author."""
        raise NotImplementedError

    def _require_author(self, record):
        # A draft with no recorded author (written before authors were recorded)
        # stays editable by the hospital's doctors; the permission classes have
        # already required the doctor role, and every change is audited.
        author = self.author_id(record)
        if author is not None and author != self.request.user.id:
            raise PermissionDenied("Only the author can change or sign this record.")

    def update(self, request, *args, **kwargs):
        # Before the body is validated: a signed record or another author's draft
        # answers 409/403, not a field error.
        record = self.get_object()
        if record.signed_at is not None:
            raise AlreadySigned()
        self._require_author(record)
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        self._require_author(instance)
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        record = self.get_object()
        self._require_author(record)
        if record.signed_at is not None:
            raise AlreadySigned("This record is already signed.")
        require_signing_doctor(request.user, self.get_object_hospital_id(record))
        record.signed_at = timezone.now()
        record.signed_by = request.user
        record.save(update_fields=["signed_at", "signed_by"])
        record_audit(request, f"clinical.{record._meta.model_name}.signed", record)
        return Response(self.get_serializer(record).data)
