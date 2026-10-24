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
from rest_framework.response import Response
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
PROVIDER_UNAVAILABLE = (
    "AI service is not configured for this hospital. "
    "Document the consultation manually."
)


def _audio_error(audio_file):
    """Return an error message for an unacceptable upload, else None."""
    if audio_file.size > MAX_AUDIO_BYTES:
        return "Audio file too large. Maximum 100MB."
    content_type = (audio_file.content_type or "").split(";")[0].strip()
    if content_type not in ALLOWED_AUDIO_TYPES:
        return f"Unsupported audio format. Allowed: {', '.join(ALLOWED_AUDIO_TYPES)}"
    return None


def _doctor_for(request, hospital_id):
    """The Doctor profile of the signed-in user at this hospital, if any."""
    from doctors.models import Doctor

    return Doctor.objects.filter(user=request.user, hospital_id=hospital_id).first()


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
            session.audio_file = audio_file
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

        audio_file = request.FILES.get("audio_file")
        if not audio_file:
            return Response(
                {"error": "No audio file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        error = _audio_error(audio_file)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        session.audio_file = audio_file
        session.audio_format = audio_file.content_type.split("/")[-1]
        session.save(update_fields=["audio_file", "audio_format"])

        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def transcribe(self, request, pk=None):
        """Trigger speech-to-text transcription for this consultation"""
        from .services.stt import SpeechToTextService

        session = self.get_object()

        if not session.audio_file:
            return Response(
                {"error": "No audio file uploaded for this consultation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create transcript
        transcript, created = ConversationTranscript.objects.get_or_create(
            consultation=session,
            defaults={"status": ConversationTranscript.Status.PENDING},
        )

        if transcript.status == ConversationTranscript.Status.COMPLETED:
            return Response(
                {"message": "Transcript already exists", "transcript": ConversationTranscriptSerializer(transcript).data},
                status=status.HTTP_200_OK,
            )

        # Reset for reprocessing
        transcript.status = ConversationTranscript.Status.PROCESSING
        transcript.processing_started_at = timezone.now()
        transcript.error_message = ""
        transcript.save(update_fields=["status", "processing_started_at", "error_message"])

        # Process asynchronously (in production, use Celery)
        try:
            stt_service = SpeechToTextService()
            result = stt_service.transcribe(
                audio_file=session.audio_file.path,
                language=session.language,
            )

            transcript.text = result.text or ""
            transcript.structured_data = result.structured_data or {}
            transcript.provider = result.provider or ""
            transcript.provider_model = result.model or ""
            transcript.provider_metadata = result.metadata or {}
            transcript.detected_language = result.detected_language or ""
            transcript.language_confidence = result.language_confidence
            transcript.status = ConversationTranscript.Status.COMPLETED
            transcript.processing_completed_at = timezone.now()

        except Exception as e:
            logger.exception("STT processing failed")
            transcript.status = ConversationTranscript.Status.FAILED
            transcript.error_message = str(e)[:1000]
            transcript.processing_completed_at = timezone.now()
            transcript.save()
            return Response(
                {"error": PROVIDER_UNAVAILABLE if "not available" in str(e) else "Transcription failed. Try again or document manually.",
                 "transcript": ConversationTranscriptSerializer(transcript).data},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        transcript.save()
        # Give the doctor a draft to generate into; it stays a pending-review draft.
        if not session.ai_drafts.exists():
            AIConsultationDraft.objects.create(
                consultation=session,
                transcript=transcript,
                version=1,
                status=AIConsultationDraft.Status.GENERATED,
            )
        return Response(ConversationTranscriptSerializer(transcript).data)


class ConversationTranscriptViewSet(HospitalScopedViewSet):
    """API for managing conversation transcripts"""
    queryset = ConversationTranscript.objects.select_related(
        "consultation", "consultation__patient", "consultation__doctor", "consultation__hospital"
    )
    serializer_class = ConversationTranscriptSerializer
    permission_classes = [IsClinicalStaff]

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
        """Generate AI clinical draft from transcript"""
        from .services.llm import LLMClinicalService

        draft = self.get_object()

        if not draft.transcript or not draft.transcript.text:
            return Response(
                {"error": "No transcript available for AI generation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if draft.status != AIConsultationDraft.Status.GENERATED:
            return Response(
                {"error": f"Cannot generate draft in status: {draft.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark as processing
        draft.generation_started_at = timezone.now()
        draft.status = AIConsultationDraft.Status.UNDER_REVIEW
        draft.save(update_fields=["generation_started_at", "status"])

        try:
            llm_service = LLMClinicalService()
            result = llm_service.generate_clinical_draft(
                transcript_text=draft.transcript.text,
                language=draft.transcript.detected_language or draft.consultation.language,
                patient_context={
                    "name": draft.consultation.patient.name,
                    "age": draft.consultation.patient.age,
                    "gender": draft.consultation.patient.gender,
                },
            )

            draft.structured_extraction = result.get("structured_extraction", {})
            draft.summary = result.get("summary", "")
            draft.provider = result.get("provider", "")
            draft.provider_model = result.get("model", "")
            draft.prompt_version = result.get("prompt_version", "v1")
            draft.provider_metadata = result.get("metadata", {})
            draft.generation_completed_at = timezone.now()
            draft.generation_duration_ms = int(
                (draft.generation_completed_at - draft.generation_started_at).total_seconds() * 1000
            )
            draft.status = AIConsultationDraft.Status.UNDER_REVIEW

        except Exception as e:
            # Nothing is written to the clinical record on failure.
            logger.exception("LLM generation failed")
            draft.status = AIConsultationDraft.Status.GENERATED
            draft.generation_completed_at = timezone.now()
            draft.provider_metadata = {"error": str(e)[:1000]}
            draft.save()
            return Response(
                {"error": PROVIDER_UNAVAILABLE if "not available" in str(e) else "AI draft generation failed. Try again or document manually.",
                 "draft": self.get_serializer(draft).data},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        draft.save()
        return Response(self.get_serializer(draft).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def regenerate(self, request, pk=None):
        """Regenerate AI draft (creates new version)"""
        old_draft = self.get_object()

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
            # Apply doctor's edit to structured_extraction
            if section and doctor_value:
                draft.structured_extraction[section] = doctor_value
            draft.save(update_fields=["status", "structured_extraction", "updated_at"])

        return Response(DoctorReviewSerializer(review).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def approve(self, request, pk=None):
        """Approve AI draft and create final clinical note"""
        draft = self.get_object()

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

        for key, label in section_labels.items():
            value = extraction.get(key)
            if value:
                if isinstance(value, list):
                    formatted = "\n".join(f"  - {v}" for v in value)
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

    def get_queryset(self):
        qs = super().get_queryset()
        draft_id = self.request.query_params.get("draft")
        if draft_id:
            qs = qs.filter(ai_draft_id=draft_id)
        return qs


class ClinicalExtractionSchemaViewSet(HospitalScopedViewSet):
    """API for managing clinical extraction schemas"""
    queryset = ClinicalExtractionSchema.objects.filter(is_active=True)
    serializer_class = ClinicalExtractionSchemaSerializer
    permission_classes = [IsDoctor]


class AIPromptTemplateViewSet(HospitalScopedViewSet):
    """API for managing AI prompt templates"""
    queryset = AIPromptTemplate.objects.filter(is_active=True).select_related("schema_version")
    serializer_class = AIPromptTemplateSerializer
    permission_classes = [IsDoctor]
