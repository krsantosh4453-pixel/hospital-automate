"""
Discharge summary AI assist (mounted at /api/ai/discharge/).

POST admissions/<id>/draft/        -> a draft for the clinician to review
POST admissions/<id>/draft-review/ -> record what the clinician did with it

The draft is never written to the discharge summary here: the clinician
edits it in the IPD summary dialog and saves it through the IPD API.
"""

import json

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, NotFound, ValidationError
from rest_framework.response import Response

from audit.models import AIInteraction
from audit.services import record_audit
from ipd.models import Admission
from users.permissions import IsDoctor
from users.viewsets import HospitalScopedViewSet

from .discharge import draft_discharge_summary

DRAFT_STATUS = "Discharge Draft"
MAX_INPUT_CHARS = 20000
REVIEW_OUTCOMES = {"accepted": "Discharge Draft Accepted", "edited": "Discharge Draft Edited",
                   "discarded": "Discharge Draft Discarded"}
DRAFT_NOTICE = "AI-assisted draft. Check every line against the record and edit before saving."


class DischargeDraftViewSet(HospitalScopedViewSet):
    queryset = Admission.objects.select_related("patient", "hospital")
    permission_classes = [IsDoctor]
    http_method_names = ["post", "options"]

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(detail=True, methods=["post"])
    def draft(self, request, pk=None):
        admission = self.get_object()
        context, draft = draft_discharge_summary(admission)
        interaction = AIInteraction.objects.create(
            patient=admission.patient,
            hospital=admission.hospital,
            input_text=json.dumps({"admission": admission.pk, "context": context}, ensure_ascii=False)[:MAX_INPUT_CHARS],
            ai_output=draft.text,
            status=DRAFT_STATUS,
        )
        record_audit(request, "ai.discharge_draft.generated", admission, hospital=admission.hospital_id,
                     details={"draft": interaction.pk, "source": draft.source, "provider": draft.provider})
        return Response({
            "draft_id": interaction.pk,
            "admission": admission.pk,
            "text": draft.text,
            "sections": draft.sections,
            "source": draft.source,
            "provider": draft.provider,
            "model": draft.model,
            "warnings": draft.warnings,
            "notice": DRAFT_NOTICE,
            "generated_at": interaction.created_at,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="draft-review")
    def draft_review(self, request, pk=None):
        """{draft_id, outcome: accepted|edited|discarded} after the clinician saved or dropped the draft."""
        from doctors.models import Doctor

        admission = self.get_object()
        outcome = str(request.data.get("outcome") or "")
        if outcome not in REVIEW_OUTCOMES:
            raise ValidationError({"outcome": f"Choose one of: {', '.join(REVIEW_OUTCOMES)}."})
        try:
            interaction = AIInteraction.objects.get(
                pk=int(request.data.get("draft_id")), patient=admission.patient,
                hospital=admission.hospital, status=DRAFT_STATUS,
            )
        except (AIInteraction.DoesNotExist, TypeError, ValueError):
            raise NotFound("Open draft not found for this admission.")
        interaction.status = REVIEW_OUTCOMES[outcome]
        interaction.reviewed_by = Doctor.objects.filter(user=request.user, hospital_id=admission.hospital_id).first()
        interaction.save(update_fields=["status", "reviewed_by"])
        record_audit(request, "ai.discharge_draft.reviewed", admission, hospital=admission.hospital_id,
                     details={"draft": interaction.pk, "outcome": outcome})
        return Response({"draft_id": interaction.pk, "status": interaction.status})
