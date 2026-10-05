from django.db import models
from django.conf import settings
from django.utils import timezone


class ConsultationSession(models.Model):
    """
    Represents a doctor-patient consultation session with audio recording capability.
    Linked to an existing Visit/Encounter for hospital isolation and clinical context.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RECORDING = "recording", "Recording"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    visit = models.OneToOneField(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="ai_consultation_session",
        help_text="The visit this consultation session belongs to",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_consultation_sessions",
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="ai_consultation_sessions",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="ai_consultation_sessions",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    recording_started_at = models.DateTimeField(null=True, blank=True)
    recording_stopped_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Audio file reference
    audio_file = models.FileField(
        upload_to="consultation_audio/",
        null=True,
        blank=True,
        help_text="Recorded audio file",
    )
    audio_duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration of recorded audio in seconds",
    )
    audio_format = models.CharField(
        max_length=20,
        blank=True,
        help_text="Audio format (wav, mp3, m4a, etc.)",
    )

    # Language for STT
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="Language code for transcription (en, hi, etc.)",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ai_consultations",
    )

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["doctor", "status"]),
            models.Index(fields=["visit"]),
        ]

    def __str__(self):
        return f"Consultation #{self.pk} - {self.patient.name} - {self.status}"

    def can_start_recording(self):
        return self.status in [self.Status.ACTIVE, self.Status.COMPLETED]

    def can_stop_recording(self):
        return self.status == self.Status.RECORDING


class ConversationTranscript(models.Model):
    """
    Stores the transcript from speech-to-text processing.
    One transcript per consultation session (can be regenerated).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    consultation = models.OneToOneField(
        ConsultationSession,
        on_delete=models.CASCADE,
        related_name="transcript",
    )

    # Raw transcript text
    text = models.TextField(blank=True, help_text="Full transcript text")

    # Structured transcript with speaker diarization (if available)
    structured_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured transcript with speakers, timestamps, confidence",
    )

    # STT provider info
    provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="STT provider used (whisper, google, azure, etc.)",
    )
    provider_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific model used (whisper-large-v3, etc.)",
    )
    provider_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional provider-specific metadata",
    )

    # Language detection
    detected_language = models.CharField(
        max_length=10,
        blank=True,
        help_text="Language detected by STT provider",
    )
    language_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score for language detection",
    )

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)

    # Timing
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transcript for Consultation #{self.consultation_id} - {self.status}"


class AIConsultationDraft(models.Model):
    """
    AI-generated clinical draft from transcript processing.
    Multiple versions can exist for regeneration support.
    """

    class Status(models.TextChoices):
        GENERATED = "generated", "Generated"
        UNDER_REVIEW = "under_review", "Under Review"
        EDITED = "edited", "Edited"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    consultation = models.ForeignKey(
        ConsultationSession,
        on_delete=models.CASCADE,
        related_name="ai_drafts",
    )
    transcript = models.ForeignKey(
        ConversationTranscript,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_drafts",
    )

    # Version for regeneration tracking
    version = models.PositiveIntegerField(default=1)

    # Structured clinical extraction (validated schema)
    structured_extraction = models.JSONField(
        default=dict,
        help_text="Validated structured clinical data from LLM",
    )

    # Human-readable summary
    summary = models.TextField(blank=True, help_text="AI-generated narrative summary")

    # LLM provider info
    provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="LLM provider (openai, anthropic, google, local, etc.)",
    )
    provider_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific model used (gpt-4, claude-3, etc.)",
    )
    prompt_version = models.CharField(
        max_length=50,
        default="v1",
        help_text="Version of the prompt template used",
    )
    provider_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Provider-specific metadata (tokens, latency, etc.)",
    )

    # Generation timing
    generation_started_at = models.DateTimeField(null=True, blank=True)
    generation_completed_at = models.DateTimeField(null=True, blank=True)
    generation_duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Generation time in milliseconds",
    )

    # Status workflow
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.GENERATED,
    )

    # Review tracking
    reviewed_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_ai_drafts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    # Approval tracking
    approved_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_ai_drafts",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Final clinical note created from this draft
    final_clinical_note = models.OneToOneField(
        "clinical.ClinicalNote",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_draft_source",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version"]
        unique_together = [["consultation", "version"]]
        indexes = [
            models.Index(fields=["consultation", "status"]),
            models.Index(fields=["reviewed_by", "status"]),
        ]

    def __str__(self):
        return f"AI Draft v{self.version} for Consultation #{self.consultation_id} - {self.status}"

    def is_editable(self):
        return self.status in [self.Status.GENERATED, self.Status.UNDER_REVIEW, self.Status.EDITED]

    def can_approve(self):
        return self.status in [self.Status.UNDER_REVIEW, self.Status.EDITED]


class DoctorReview(models.Model):
    """
    Records doctor's review actions on an AI draft.
    Each edit/accept/reject action creates a review record for audit trail.
    """

    class Action(models.TextChoices):
        VIEWED = "viewed", "Viewed"
        ACCEPTED_SECTION = "accepted_section", "Accepted Section"
        EDITED_SECTION = "edited_section", "Edited Section"
        REJECTED_SECTION = "rejected_section", "Rejected Section"
        REGENERATE_REQUESTED = "regenerate_requested", "Regenerate Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    ai_draft = models.ForeignKey(
        AIConsultationDraft,
        on_delete=models.CASCADE,
        related_name="doctor_reviews",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_draft_reviews",
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="ai_draft_reviews",
    )

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )

    # Section being reviewed (e.g., "chief_complaint", "symptoms", "assessment", etc.)
    section = models.CharField(
        max_length=50,
        blank=True,
        help_text="Clinical section this review action applies to",
    )

    # Original AI value
    ai_value = models.JSONField(
        default=dict,
        blank=True,
        help_text="The AI-generated value for this section",
    )

    # Doctor's edited value (if edited)
    doctor_value = models.JSONField(
        default=dict,
        blank=True,
        help_text="The doctor's corrected/edited value",
    )

    # Doctor's notes/comments
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ai_draft", "created_at"]),
            models.Index(fields=["doctor", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} by Dr.{self.doctor_id} on Draft #{self.ai_draft_id}"


class ClinicalExtractionSchema(models.Model):
    """
    Defines the structured schema for clinical extraction.
    This allows versioning of the extraction schema alongside prompt versions.
    """

    version = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # JSON Schema definition for validation
    schema = models.JSONField(
        help_text="JSON Schema for structured clinical extraction output",
    )

    # Example output for reference
    example_output = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"Clinical Schema {self.version} - {self.name}"


class AIPromptTemplate(models.Model):
    """
    Versioned prompt templates for LLM clinical extraction.
    Ensures reproducibility and auditability of AI generations.
    """

    version = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # System prompt
    system_prompt = models.TextField(
        help_text="System prompt defining AI role and constraints",
    )

    # User prompt template with placeholders
    user_prompt_template = models.TextField(
        help_text="User prompt template with {{transcript}}, {{language}}, etc. placeholders",
    )

    # Expected output schema version
    schema_version = models.ForeignKey(
        ClinicalExtractionSchema,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prompt_templates",
    )

    # Model configuration hints
    recommended_temperature = models.FloatField(default=0.1)
    recommended_max_tokens = models.PositiveIntegerField(default=4000)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"Prompt Template {self.version} - {self.name}"