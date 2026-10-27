from django.contrib import admin
from .models import (
    ConsultationSession,
    ConversationTranscript,
    AIConsultationDraft,
    DoctorReview,
    ClinicalExtractionSchema,
    AIPromptTemplate,
)


@admin.register(ConsultationSession)
class ConsultationSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "patient",
        "doctor",
        "hospital",
        "status",
        "started_at",
        "recording_started_at",
        "completed_at",
    ]
    list_filter = ["status", "hospital", "doctor"]
    search_fields = ["patient__name", "doctor__name", "visit__id"]
    readonly_fields = ["started_at", "created_by"]
    raw_id_fields = ["visit", "doctor", "hospital", "patient", "created_by"]


@admin.register(ConversationTranscript)
class ConversationTranscriptAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "consultation",
        "status",
        "provider",
        "detected_language",
        "created_at",
    ]
    list_filter = ["status", "provider", "detected_language"]
    search_fields = ["consultation__patient__name", "text"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["consultation"]


@admin.register(AIConsultationDraft)
class AIConsultationDraftAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "consultation",
        "version",
        "status",
        "provider",
        "provider_model",
        "reviewed_by",
        "approved_by",
        "created_at",
    ]
    list_filter = ["status", "provider", "provider_model"]
    search_fields = ["consultation__patient__name", "summary"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "generation_started_at",
        "generation_completed_at",
        "reviewed_at",
        "approved_at",
    ]
    raw_id_fields = ["consultation", "transcript", "reviewed_by", "approved_by", "final_clinical_note"]


@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "ai_draft",
        "doctor",
        "action",
        "section",
        "created_at",
    ]
    list_filter = ["action", "section"]
    search_fields = ["ai_draft__consultation__patient__name", "notes"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["ai_draft", "doctor", "hospital"]


@admin.register(ClinicalExtractionSchema)
class ClinicalExtractionSchemaAdmin(admin.ModelAdmin):
    list_display = ["version", "name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["version", "name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AIPromptTemplate)
class AIPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ["version", "name", "schema_version", "is_active", "created_at"]
    list_filter = ["is_active", "schema_version"]
    search_fields = ["version", "name"]
    readonly_fields = ["created_at", "updated_at"]


# Every other ai_scribe table, with default columns (config/admin_registry.py).
from config.admin_registry import register_app_models  # noqa: E402

register_app_models("ai_scribe")
