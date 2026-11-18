"""
The scribe's two provider-bound steps, shared by the API (synchronous) and
the Celery tasks (``ai_scribe.tasks``, asynchronous):

* ``run_transcription``: audio -> transcript (speech-to-text provider)
* ``run_generation``: transcript -> clinical draft (LLM provider)

Each step is claimed atomically before it starts, so two requests never
send the same input to a provider twice. A claim that outlived the provider
timeout (a crashed worker) may be taken again.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from ..models import AIConsultationDraft, ConversationTranscript
from . import languages

logger = logging.getLogger(__name__)

PROVIDER_UNAVAILABLE = (
    "AI service is not configured for this hospital. "
    "Document the consultation manually."
)
TRANSCRIPTION_FAILED = "Transcription failed. Try again or document manually."
GENERATION_FAILED = "AI draft generation failed. Try again or document manually."
# Longest a provider call may run (STT 120 s, LLM timeout) plus a margin.
STALE_CLAIM_MARGIN = timedelta(seconds=60)
STT_TIMEOUT = timedelta(seconds=120)


def stale_after():
    llm = timedelta(seconds=getattr(settings, "AI_SCRIBE_LLM_TIMEOUT_SECONDS", 60) or 60)
    return max(llm, STT_TIMEOUT) + STALE_CLAIM_MARGIN


def safe_error(exc):
    """The message a client may see; provider text is never echoed."""
    return PROVIDER_UNAVAILABLE if "not available" in str(exc) else None


def patient_identifiers(patient):
    """
    Every identifier the hospital holds for ``patient``, as ``(names,
    terms)``: names (the patient, the emergency contact, the login) are masked
    word by word; terms (phones, e-mail, address, UHID, insurance policy, ABHA)
    whole. They are masked before a transcript or record leaves the server.
    """
    names = [patient.name, getattr(patient, "emergency_contact_name", "")]
    terms = [
        patient.phone, patient.address, getattr(patient, "address_line", ""),
        getattr(patient, "emergency_contact_phone", ""), getattr(patient, "policy_number", ""),
    ]
    user = getattr(patient, "user", None)
    if user is not None:
        names += [user.first_name, user.last_name]
        terms += [user.email, user.username]
    terms += list(patient.hospital_memberships.values_list("uhid", flat=True))
    try:
        from abdm.models import ABHALink

        for number, address in ABHALink.objects.filter(patient=patient).values_list("abha_number", "abha_address"):
            terms += [number, address]
    except Exception:  # ABDM is optional; masking must never block drafting
        logger.debug("ABHA identifiers unavailable for redaction", exc_info=True)

    def clean(values):
        return [str(v).strip() for v in values if v and str(v).strip()]

    return clean(names), clean(terms)


def claim_transcription(session, force=False):
    """
    Mark the session's transcript as processing. Returns ``(transcript,
    claimed)``; ``claimed`` is False when a finished transcript is reused or
    another request is already transcribing.
    """
    transcript, _ = ConversationTranscript.objects.get_or_create(
        consultation=session, defaults={"status": ConversationTranscript.Status.PENDING},
    )
    if transcript.status == ConversationTranscript.Status.COMPLETED and not force:
        return transcript, False
    now = timezone.now()
    free = (~Q(status=ConversationTranscript.Status.PROCESSING)
            | Q(processing_started_at__lt=now - stale_after())
            | Q(processing_started_at__isnull=True))
    claimed = ConversationTranscript.objects.filter(Q(pk=transcript.pk) & free).update(
        status=ConversationTranscript.Status.PROCESSING, processing_started_at=now,
        processing_completed_at=None, error_message="",
    )
    transcript.refresh_from_db()
    return transcript, bool(claimed)


def run_transcription(transcript_id):
    """Speech-to-text for a claimed transcript. Returns ``(transcript, error)``."""
    from .stt import SpeechToTextService

    transcript = ConversationTranscript.objects.select_related("consultation").get(pk=transcript_id)
    session = transcript.consultation
    try:
        result = SpeechToTextService().transcribe(audio_file=session.audio_file.path, language=session.language)
    except Exception as exc:
        logger.exception("STT processing failed")
        transcript.status = ConversationTranscript.Status.FAILED
        transcript.error_message = str(exc)[:1000]
        transcript.processing_completed_at = timezone.now()
        transcript.save()
        return transcript, safe_error(exc) or TRANSCRIPTION_FAILED

    transcript.text = result.text or ""
    transcript.structured_data = result.structured_data or {}
    transcript.provider = result.provider or ""
    transcript.provider_model = result.model or ""
    transcript.provider_metadata = result.metadata or {}
    transcript.detected_language = result.detected_language or ""
    transcript.language_confidence = result.language_confidence
    transcript.status = ConversationTranscript.Status.COMPLETED
    transcript.processing_completed_at = timezone.now()
    transcript.save()
    # Give the doctor a draft to generate into; it stays a pending-review draft.
    if not session.ai_drafts.exists():
        AIConsultationDraft.objects.create(
            consultation=session, transcript=transcript, version=1,
            status=AIConsultationDraft.Status.GENERATED,
        )
    return transcript, None


def claim_generation(draft):
    """
    Move a draft into generation. Free drafts are those still waiting for
    generation, or stuck in a generation that outlived the provider timeout.
    """
    now = timezone.now()
    waiting = Q(status=AIConsultationDraft.Status.GENERATED)
    stuck = Q(status=AIConsultationDraft.Status.UNDER_REVIEW, generation_completed_at__isnull=True,
              generation_started_at__lt=now - stale_after())
    claimed = AIConsultationDraft.objects.filter(Q(pk=draft.pk) & (waiting | stuck)).update(
        status=AIConsultationDraft.Status.UNDER_REVIEW, generation_started_at=now,
        generation_completed_at=None,
    )
    draft.refresh_from_db()
    return bool(claimed)


def draft_language(draft):
    """
    The doctor's chosen language wins; only "auto" defers to what the STT
    provider heard (a Hinglish consultation is often detected as "hi", but
    its note should still be in English).
    """
    chosen = draft.consultation.language
    if chosen != languages.AUTO:
        return chosen
    detected = draft.transcript.detected_language
    return detected if detected in languages.SUPPORTED_LANGUAGES else languages.AUTO


def run_generation(draft_id):
    """LLM drafting for a claimed draft. Returns ``(draft, error)``."""
    from .llm import LLMClinicalService

    draft = AIConsultationDraft.objects.select_related(
        "consultation__patient", "transcript"
    ).get(pk=draft_id)
    patient = draft.consultation.patient
    names, terms = patient_identifiers(patient)
    try:
        # Only age and gender describe the patient; every identifier the
        # hospital holds is masked in the transcript before it is sent.
        result = LLMClinicalService().generate_clinical_draft(
            transcript_text=draft.transcript.text,
            language=draft_language(draft),
            patient_context={"age": patient.age, "gender": patient.gender},
            redact_terms=terms,
            redact_names=names,
        )
    except Exception as exc:
        # Nothing is written to the clinical record on failure.
        logger.exception("LLM generation failed")
        draft.status = AIConsultationDraft.Status.GENERATED
        draft.generation_completed_at = timezone.now()
        draft.provider_metadata = {"error": str(exc)[:1000]}
        draft.save()
        return draft, safe_error(exc) or GENERATION_FAILED

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
    draft.save()
    return draft, None
