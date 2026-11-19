import uuid
import json
import logging

from django.conf import settings
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.db.models import Max

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from users.viewsets import HospitalScopedViewSet
from users.permissions import IsDoctor, IsClinicalStaff

from .models import (
    ConsultationSession,
    ConversationTranscript,
    AIConsultationDraft,
    DoctorReview,
    ClinicalExtractionSchema,
    AIPromptTemplate,
)
from .serializers import (
    ConsultationSessionSerializer,
    ConversationTranscriptSerializer,
    AIConsultationDraftSerializer,
    AIConsultationDraftListSerializer,
    DoctorReviewSerializer,
    ClinicalExtractionSchemaSerializer,
    AIPromptTemplateSerializer,
)

from audit.services import record_audit
from . import audio_validation, tasks
from .services import languages, pipeline

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_TYPES = [
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/webm",
]
MAX_AUDIO_BYTES = 100 * 1024 * 1024
PROVIDER_UNAVAILABLE = pipeline.PROVIDER_UNAVAILABLE
_draft_language = pipeline.draft_language


def _audio_error(audio_file):
    """Return an error message for an unacceptable upload, else None."""
    if audio_file.size > MAX_AUDIO_BYTES:
        return "Audio file too large. Maximum 100MB."
    content_type = audio_validation.declared_type(audio_file)
    if content_type not in ALLOWED_AUDIO_TYPES:
        return f"Unsupported audio format. Allowed: {', '.join(ALLOWED_AUDIO_TYPES)}"
    # S-L6: the bytes must be that audio container, not just claim to be.
    return audio_validation.container_error(audio_file)


def _accept_audio(session, audio_file):
    """Attach a checked upload under a server-chosen name (never the client's)."""
    audio_file.name = audio_validation.safe_name(audio_file, f"consultation-{session.pk}")
    session.audio_file = audio_file


def _wants_async(request):
    """True when the client asked to queue the provider call and poll."""
    return str(request.data.get("async", "")).lower() in ("true", "1", "yes")

def _doctor_for(request, hospital_id):
    """The Doctor profile of the signed-in user at this hospital, if any."""
    from doctors.models import Doctor

    return Doctor.objects.filter(user=request.user, hospital_id=hospital_id).first()


NOT_CONSULTING_DOCTOR = "Only the consulting doctor of this session may do this."
NOT_RECORDED = "Not recorded in this consultation."


def _not_consulting_doctor(request, session):
    """
    A 403 response unless the signed-in user is the session's own doctor:
    recording, transcription, drafting and approval belong to the clinician
    who holds the consultation, not to any doctor of the hospital.
    """
    if session.doctor_id and session.doctor.user_id == request.user.pk:
        return None
    return Response({"error": NOT_CONSULTING_DOCTOR}, status=status.HTTP_403_FORBIDDEN)


class ConsultationSessionViewSet(HospitalScopedViewSet):
    """
    API for managing AI consultation sessions.
    Linked to Visits for hospital isolation.
    """
    queryset = ConsultationSession.objects.select_related(
        "visit", "doctor", "hospital", "patient", "created_by"
    ).prefetch_related("transcript", "ai_drafts")
    serializer_class = ConsultationSessionSerializer
    permission_classes = [IsClinicalStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)
        return qs

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def start_recording(self, request, pk=None):
        """Start audio recording for this consultation"""
        session = self.get_object()
        denied = _not_consulting_doctor(request, session)
        if denied:
            return denied

        if not session.can_start_recording():
            return Response(
                {"error": f"Cannot start recording in status: {session.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consent = str(request.data.get("patient_consent", "")).lower() in ("true", "1", "yes")
        if not consent and not session.recording_consent_at:
            return Response(
                {"error": "Record the patient's consent to audio recording before starting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not session.recording_consent_at:
            session.recording_consent_at = timezone.now()
            session.recording_consent_by = request.user
            record_audit(request, "ai.recording_consent.recorded", session, hospital=session.hospital_id)

        session.status = ConsultationSession.Status.RECORDING
        session.recording_started_at = timezone.now()
        session.save(update_fields=["status", "recording_started_at", "recording_consent_at", "recording_consent_by"])

        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def stop_recording(self, request, pk=None):
        """Stop audio recording and optionally upload audio file"""
        session = self.get_object()
        denied = _not_consulting_doctor(request, session)
        if denied:
            return denied

        if not session.can_stop_recording():
            return Response(
                {"error": f"Cannot stop recording in status: {session.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle audio file upload
        audio_file = request.FILES.get("audio_file")
        audio_duration = request.data.get("duration_seconds")
        audio_format = request.data.get("format", "")

        if audio_file:
            error = _audio_error(audio_file)
            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
            _accept_audio(session, audio_file)
        if audio_duration:
            try:
                session.audio_duration_seconds = int(audio_duration)
            except (ValueError, TypeError):
                pass
        if audio_format:
            session.audio_format = audio_format

        session.status = ConsultationSession.Status.COMPLETED
        session.recording_stopped_at = timezone.now()
        session.completed_at = timezone.now()
        session.save(
            update_fields=[
                "status",
                "audio_file",
                "audio_duration_seconds",
                "audio_format",
                "recording_stopped_at",
                "completed_at",
            ]
        )

        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def upload_audio(self, request, pk=None):
        """Upload audio file for an existing consultation"""
        session = self.get_object()
        denied = _not_consulting_doctor(request, session)
        if denied:
            return denied

        audio_file = request.FILES.get("audio_file")
        if not audio_file:
            return Response(
                {"error": "No audio file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        error = _audio_error(audio_file)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        _accept_audio(session, audio_file)
        session.audio_format = audio_validation.declared_type(audio_file).split("/")[-1]
        session.save(update_fields=["audio_file", "audio_format"])

        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def transcribe(self, request, pk=None):
        """
        Speech-to-text for this consultation. With ``{"async": true}`` the
        work is queued and the transcript comes back as ``processing`` (202);
        poll ``ai/transcripts/?consultation=<id>``. Otherwise the call waits.
        """
        session = self.get_object()
        denied = _not_consulting_doctor(request, session)
        if denied:
            return denied

        if not session.audio_file:
            return Response(
                {"error": "No audio file uploaded for this consultation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The doctor may pick the spoken language right before transcribing.
        language_changed = False
        if "language" in request.data:
            try:
                chosen_language = languages.normalize_language(request.data.get("language"))
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if chosen_language != session.language:
                session.language = chosen_language
                session.save(update_fields=["language"])
                language_changed = True

        # A finished transcript is reused unless the doctor changed the language;
        # one already being transcribed is not sent to the provider again.
        transcript, claimed = pipeline.claim_transcription(session, force=language_changed)
        if not claimed:
            if transcript.status == ConversationTranscript.Status.COMPLETED:
                message = "Transcript already exists"
            else:
                message = "Transcription is already in progress"
            return Response({"message": message, "transcript": ConversationTranscriptSerializer(transcript).data},
                            status=status.HTTP_200_OK)

        if _wants_async(request):
            transaction.on_commit(lambda: tasks.transcribe_consultation.delay(transcript.pk))
            return Response(ConversationTranscriptSerializer(transcript).data, status=status.HTTP_202_ACCEPTED)

        transcript, error = pipeline.run_transcription(transcript.pk)
        if error:
            return Response({"error": error, "transcript": ConversationTranscriptSerializer(transcript).data},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(ConversationTranscriptSerializer(transcript).data)


class ConversationTranscriptViewSet(HospitalScopedViewSet):
    """API for managing conversation transcripts"""
    queryset = ConversationTranscript.objects.select_related(
        "consultation", "consultation__patient", "consultation__doctor", "consultation__hospital"
    )
    serializer_class = ConversationTranscriptSerializer
    permission_classes = [IsClinicalStaff]
    # Read-only: the transcript is the AI draft's input and is written only by
    # the session's transcribe step, never edited or deleted by hand.
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        consultation_id = self.request.query_params.get("consultation")
        if consultation_id:
            qs = qs.filter(consultation_id=consultation_id)
        return qs


class AIConsultationDraftViewSet(HospitalScopedViewSet):
    """
    API for managing AI clinical drafts.
    Supports generation, review, approval, and regeneration workflows.
    """
    queryset = AIConsultationDraft.objects.select_related(
        "consultation", "transcript", "consultation__patient",
        "consultation__doctor", "consultation__hospital",
        "reviewed_by", "approved_by", "final_clinical_note"
    ).prefetch_related("doctor_reviews")
    serializer_class = AIConsultationDraftSerializer
    permission_classes = [IsDoctor]
    # Drafts are made by the pipeline and changed only through the workflow
    # actions below (POST), so plain create, edit and delete are refused.
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def get_serializer_class(self):
        if self.action == "list":
            return AIConsultationDraftListSerializer
        return AIConsultationDraftSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        consultation_id = self.request.query_params.get("consultation")
        if consultation_id:
            qs = qs.filter(consultation_id=consultation_id)
        draft_status = self.request.query_params.get("status")
        if draft_status:
            qs = qs.filter(status=draft_status)
        return qs

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def generate(self, request, pk=None):
        """
        Generate the AI clinical draft from the transcript. With
        ``{"async": true}`` the work is queued (202): the draft reads
        ``under_review`` with no ``generation_completed_at`` until it is ready.
        """
        draft = self.get_object()
        denied = _not_consulting_doctor(request, draft.consultation)
        if denied:
            return denied

        if not draft.transcript or not draft.transcript.text:
            return Response(
                {"error": "No transcript available for AI generation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Claim the draft atomically: of two simultaneous requests only one
        # calls the provider, so the same transcript is never sent twice.
        if not pipeline.claim_generation(draft):
            return Response(
                {"error": f"Cannot generate draft in status: {draft.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if _wants_async(request):
            transaction.on_commit(lambda: tasks.generate_draft.delay(draft.pk))
            return Response(self.get_serializer(draft).data, status=status.HTTP_202_ACCEPTED)

        draft, error = pipeline.run_generation(draft.pk)
        if error:
            return Response({"error": error, "draft": self.get_serializer(draft).data},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        record_audit(request, "ai.draft.generated", draft, hospital=draft.consultation.hospital_id,
                     details={"provider": draft.provider, "model": draft.provider_model, "version": draft.version})
        return Response(self.get_serializer(draft).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def regenerate(self, request, pk=None):
        """Regenerate AI draft (creates new version)"""
        old_draft = self.get_object()
        denied = _not_consulting_doctor(request, old_draft.consultation)
        if denied:
            return denied
        if old_draft.status == AIConsultationDraft.Status.APPROVED:
            return Response({"error": "An approved draft is final and cannot be regenerated."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Create new version
        new_version = (
            AIConsultationDraft.objects.filter(consultation=old_draft.consultation)
            .aggregate(max_version=Max("version"))["max_version"]
            or 0
        ) + 1

        new_draft = AIConsultationDraft.objects.create(
            consultation=old_draft.consultation,
            transcript=old_draft.transcript,
            version=new_version,
            status=AIConsultationDraft.Status.GENERATED,
        )

        # Log the regeneration request
        DoctorReview.objects.create(
            ai_draft=old_draft,
            doctor=_doctor_for(request, old_draft.consultation.hospital_id),
            hospital=old_draft.consultation.hospital,
            action=DoctorReview.Action.REGENERATE_REQUESTED,
            section="full_draft",
            ai_value=old_draft.structured_extraction,
            notes=f"Regeneration requested, created version {new_version}",
        )

        return Response(
            AIConsultationDraftSerializer(new_draft).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def review(self, request, pk=None):
        """Record doctor's review action on a draft section"""
        draft = self.get_object()
        denied = _not_consulting_doctor(request, draft.consultation)
        if denied:
            return denied

        if not draft.is_editable():
            return Response(
                {"error": f"Draft cannot be reviewed in status: {draft.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get("action")
        section = request.data.get("section", "")
        ai_value = request.data.get("ai_value", {})
        doctor_value = request.data.get("doctor_value", {})
        notes = request.data.get("notes", "")

        try:
            action_enum = DoctorReview.Action(action)
        except ValueError:
            return Response(
                {"error": f"Invalid action: {action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action_enum in (DoctorReview.Action.APPROVED, DoctorReview.Action.REJECTED,
                           DoctorReview.Action.REGENERATE_REQUESTED):
            return Response(
                {"error": "Use the approve, reject or regenerate action for this."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if action_enum == DoctorReview.Action.EDITED_SECTION:
            from .services.llm import LLMClinicalService

            try:
                doctor_value = LLMClinicalService.coerce_section(section, doctor_value)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        doctor = _doctor_for(request, draft.consultation.hospital_id)

        review = DoctorReview.objects.create(
            ai_draft=draft,
            doctor=doctor,
            hospital=draft.consultation.hospital,
            action=action_enum,
            section=section,
            ai_value=ai_value,
            doctor_value=doctor_value,
            notes=notes,
        )

        # Update draft status based on action
        if action_enum == DoctorReview.Action.EDITED_SECTION:
            draft.status = AIConsultationDraft.Status.EDITED
            # Apply the doctor's edit; an emptied section stays empty (missing).
            draft.structured_extraction = {**draft.structured_extraction, section: doctor_value}
            if section == "summary":
                draft.summary = doctor_value
            draft.save(update_fields=["status", "structured_extraction", "summary", "updated_at"])
            record_audit(request, "ai.draft.section_edited", draft, hospital=draft.consultation.hospital_id,
                         details={"section": section, "version": draft.version})

        return Response(DoctorReviewSerializer(review).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def approve(self, request, pk=None):
        """Approve AI draft and create final clinical note"""
        draft = self.get_object()
        denied = _not_consulting_doctor(request, draft.consultation)
        if denied:
            return denied

        if not draft.can_approve():
            return Response(
                {"error": f"Draft cannot be approved in status: {draft.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = _doctor_for(request, draft.consultation.hospital_id)

        if not doctor:
            return Response(
                {"error": "Only a doctor of this hospital, linked to your login, can approve clinical drafts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not draft.generation_completed_at or not draft.provider:
            return Response({"error": "The AI draft is not ready yet; wait for it to finish generating."},
                            status=status.HTTP_400_BAD_REQUEST)
        if draft.provider == "development" and not getattr(settings, "AI_SCRIBE_ALLOW_MOCK_PROVIDERS", False):
            return Response(
                {"error": "This draft came from the development mock provider and cannot enter a medical record."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not draft.consultation.visit_id:
            return Response({"error": "The consultation has no visit to attach a note to."},
                            status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Create final clinical note
            from clinical.models import ClinicalNote

            clinical_note = ClinicalNote.objects.create(
                visit=draft.consultation.visit,
                doctor=doctor,
                note=self._build_clinical_note_text(draft),
            )

            # Update draft
            draft.status = AIConsultationDraft.Status.APPROVED
            draft.approved_by = doctor
            draft.approved_at = timezone.now()
            draft.final_clinical_note = clinical_note
            draft.reviewed_by = doctor
            draft.reviewed_at = timezone.now()
            draft.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "approved_at",
                    "final_clinical_note",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

            # Log approval
            DoctorReview.objects.create(
                ai_draft=draft,
                doctor=doctor,
                hospital=draft.consultation.hospital,
                action=DoctorReview.Action.APPROVED,
                section="full_draft",
                ai_value=draft.structured_extraction,
                doctor_value=draft.structured_extraction,
                notes="Draft approved and clinical note created",
            )

        record_audit(request, "ai.draft.approved", draft, hospital=draft.consultation.hospital_id,
                     details={"clinical_note": clinical_note.id, "version": draft.version})
        return Response(
            {
                "message": "Draft approved and clinical note created",
                "draft": self.get_serializer(draft).data,
                "clinical_note_id": clinical_note.id,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def reject(self, request, pk=None):
        """Reject AI draft"""
        draft = self.get_object()
        denied = _not_consulting_doctor(request, draft.consultation)
        if denied:
            return denied

        if draft.status == AIConsultationDraft.Status.APPROVED:
            return Response(
                {"error": "Cannot reject an approved draft"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = _doctor_for(request, draft.consultation.hospital_id)

        draft.status = AIConsultationDraft.Status.REJECTED
        draft.reviewed_by = doctor
        draft.reviewed_at = timezone.now()
        draft.review_notes = request.data.get("notes", "Rejected by doctor")
        draft.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes", "updated_at"])

        DoctorReview.objects.create(
            ai_draft=draft,
            doctor=doctor,
            hospital=draft.consultation.hospital,
            action=DoctorReview.Action.REJECTED,
            section="full_draft",
            ai_value=draft.structured_extraction,
            notes=draft.review_notes,
        )

        return Response(self.get_serializer(draft).data)

    def _build_clinical_note_text(self, draft):
        """Build human-readable clinical note from structured extraction"""
        parts = []

        if draft.summary:
            parts.append(f"AI-Generated Summary:\n{draft.summary}\n")

        extraction = draft.structured_extraction

        section_labels = {
            "chief_complaint": "Chief Complaint",
            "symptoms": "Symptoms",
            "history": "History",
            "allergies": "Allergies",
            "medications": "Current Medications",
            "examination": "Examination Findings",
            "vitals": "Vital Signs",
            "assessment": "Assessment",
            "investigations": "Investigations",
            "plan": "Plan",
            "follow_up": "Follow-up",
        }

        # Every section is listed: one the consultation did not cover says so
        # instead of disappearing from the note.
        for key, label in section_labels.items():
            value = extraction.get(key)
            if not value:
                formatted = f"  {NOT_RECORDED}"
            elif isinstance(value, list):
                formatted = "\n".join(f"  - {v}" for v in value)
            elif isinstance(value, dict):
                formatted = "\n".join(f"  - {k}: {v}" for k, v in value.items())
            else:
                formatted = str(value)
            parts.append(f"{label}:\n{formatted}\n")

        parts.append(
            "\n---\n"
            f"This clinical note was generated with AI assistance and reviewed by Dr. {draft.approved_by.name if draft.approved_by else 'Unknown'}.\n"
            f"AI Draft Version: {draft.version}\n"
            f"AI Provider: {draft.provider} ({draft.provider_model})\n"
            f"Prompt Version: {draft.prompt_version}\n"
            f"Generated: {draft.generation_completed_at}\n"
            f"Approved: {draft.approved_at}"
        )

        return "\n".join(parts)


class DoctorReviewViewSet(HospitalScopedViewSet):
    """API for viewing doctor review history"""
    queryset = DoctorReview.objects.select_related(
        "ai_draft", "doctor", "hospital", "ai_draft__consultation"
    )
    serializer_class = DoctorReviewSerializer
    permission_classes = [IsClinicalStaff]
    # Review history is written only by the draft's review/approve/reject actions.
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        draft_id = self.request.query_params.get("draft")
        if draft_id:
            qs = qs.filter(ai_draft_id=draft_id)
        return qs


# S-L8 (2026-11-18): extraction schemas and prompt templates are platform-wide
# rows (no hospital). Any doctor of any hospital could POST, edit or delete
# them, changing configuration for every tenant. The scribe pipeline does not
# read them (its prompts and schema live in ai_scribe/services), so the API is
# read-only; platform superusers manage the rows in the Django admin, where
# changes are logged.
class ClinicalExtractionSchemaViewSet(HospitalScopedViewSet):
    """Read-only list of clinical extraction schemas (platform reference data)."""
    queryset = ClinicalExtractionSchema.objects.filter(is_active=True)
    serializer_class = ClinicalExtractionSchemaSerializer
    permission_classes = [IsDoctor]
    http_method_names = ["get", "head", "options"]
    tenant_global = True


class AIPromptTemplateViewSet(HospitalScopedViewSet):
    """Read-only list of AI prompt templates (platform reference data)."""
    queryset = AIPromptTemplate.objects.filter(is_active=True).select_related("schema_version")
    serializer_class = AIPromptTemplateSerializer
    permission_classes = [IsDoctor]
    http_method_names = ["get", "head", "options"]
    tenant_global = True


CNN_UNAVAILABLE = (
    "No validated imaging model, dataset or approved medical use case is configured. "
    "Image predictions are not available."
)


class AICapabilitiesView(APIView):
    """
    GET /api/ai/capabilities/: which AI assists this server can run, with
    the provider and model names (never keys). Clinical staff only.
    """

    permission_classes = [IsClinicalStaff]

    def get(self, request):
        from .services.llm import LLMClinicalService
        from .services.stt import SpeechToTextService

        stt = SpeechToTextService()
        llm = LLMClinicalService()
        stt_name = stt._default_provider or ""
        llm_name = llm._default_provider or ""
        llm_provider = llm._providers.get(llm_name)
        stt_provider = stt._providers.get(stt_name)
        return Response({
            "scribe": {
                "speech_to_text": {
                    "available": bool(stt_name),
                    "provider": stt_name,
                    "model": getattr(stt_provider, "model", "") or "",
                    "mock": stt_name == "development",
                },
                "drafting": {
                    "available": bool(llm_name),
                    "provider": llm_name,
                    "model": getattr(llm_provider, "default_model", "") or "",
                    "mock": llm_name == "development",
                },
                "languages": sorted(languages.SUPPORTED_LANGUAGES),
            },
            "image_prediction": {"available": False, "status": "blocked", "reason": CNN_UNAVAILABLE},
            "notice": "AI output is a draft for a qualified clinician to review. It is never a diagnosis or a prescription.",
        })
