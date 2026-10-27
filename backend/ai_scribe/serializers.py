from rest_framework import serializers
from .models import (
    ConsultationSession,
    ConversationTranscript,
    AIConsultationDraft,
    DoctorReview,
    ClinicalExtractionSchema,
    AIPromptTemplate,
)
from users.permissions import get_user_hospital_ids
from users.viewsets import HospitalScopedViewSet


class ConsultationSessionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    visit_label = serializers.CharField(source="visit.__str__", read_only=True)

    class Meta:
        model = ConsultationSession
        fields = [
            "id",
            "visit",
            "doctor",
            "hospital",
            "patient",
            "status",
            "started_at",
            "recording_started_at",
            "recording_stopped_at",
            "completed_at",
            "audio_file",
            "audio_duration_seconds",
            "audio_format",
            "language",
            "recording_consent_at",
            "created_by",
            "patient_name",
            "doctor_name",
            "hospital_name",
            "visit_label",
        ]
        read_only_fields = [
            "id",
            "status",
            "audio_file",
            "audio_duration_seconds",
            "audio_format",
            "recording_consent_at",
            "started_at",
            "recording_started_at",
            "recording_stopped_at",
            "completed_at",
            "created_by",
        ]

    def validate_hospital(self, value):
        """Ensure user has access to the hospital."""
        request = self.context.get("request")
        if request and value:
            user_hospital_ids = get_user_hospital_ids(request.user)
            if value.id not in user_hospital_ids:
                raise serializers.ValidationError(
                    "You do not have access to this hospital."
                )
        return value

    def validate(self, attrs):
        # Ensure hospital matches user's hospital access
        hospital = attrs.get("hospital")
        if hospital:
            user_hospital_ids = get_user_hospital_ids(self.context["request"].user)
            if hospital.id not in user_hospital_ids:
                raise serializers.ValidationError(
                    {"hospital": "You do not have access to this hospital."}
                )

        # Ensure doctor belongs to hospital
        doctor = attrs.get("doctor")
        if doctor and hospital and doctor.hospital_id != hospital.id:
            raise serializers.ValidationError(
                {"doctor": "This doctor does not belong to this hospital."}
            )

        # Ensure visit belongs to hospital and patient
        visit = attrs.get("visit")
        if visit:
            if hospital and visit.hospital_id != hospital.id:
                raise serializers.ValidationError(
                    {"visit": "This visit does not belong to this hospital."}
                )
            patient = attrs.get("patient")
            if patient and visit.patient_id != patient.id:
                raise serializers.ValidationError(
                    {"visit": "This visit does not belong to the selected patient."}
                )

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class ConversationTranscriptSerializer(serializers.ModelSerializer):
    consultation_id = serializers.IntegerField(source="consultation.id", read_only=True)
    patient_name = serializers.CharField(
        source="consultation.patient.name", read_only=True
    )

    class Meta:
        model = ConversationTranscript
        fields = [
            "id",
            "consultation",
            "text",
            "structured_data",
            "provider",
            "provider_model",
            "provider_metadata",
            "detected_language",
            "language_confidence",
            "status",
            "error_message",
            "processing_started_at",
            "processing_completed_at",
            "created_at",
            "updated_at",
            "consultation_id",
            "patient_name",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "processing_started_at",
            "processing_completed_at",
        ]



def draft_review_label(draft):
    """Shown on every AI draft so unreviewed text is never mistaken for a record."""
    if draft.status == "approved":
        return "Approved by clinician"
    if draft.status == "rejected":
        return "AI Draft — Rejected"
    return "AI Draft — Pending Review"


class AIConsultationDraftSerializer(serializers.ModelSerializer):
    review_label = serializers.SerializerMethodField()

    def get_review_label(self, obj):
        return draft_review_label(obj)

    consultation_id = serializers.IntegerField(source="consultation.id", read_only=True)
    patient_name = serializers.CharField(
        source="consultation.patient.name", read_only=True
    )
    doctor_name = serializers.CharField(
        source="consultation.doctor.name", read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.name", read_only=True, allow_null=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.name", read_only=True, allow_null=True
    )

    class Meta:
        model = AIConsultationDraft
        fields = [
            "review_label",
            "id",
            "consultation",
            "transcript",
            "version",
            "structured_extraction",
            "summary",
            "provider",
            "provider_model",
            "prompt_version",
            "provider_metadata",
            "generation_started_at",
            "generation_completed_at",
            "generation_duration_ms",
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "approved_by",
            "approved_at",
            "final_clinical_note",
            "created_at",
            "updated_at",
            "consultation_id",
            "patient_name",
            "doctor_name",
            "reviewed_by_name",
            "approved_by_name",
        ]
        # Workflow state changes only through the generate/review/approve/
        # reject actions, which check the clinician and write the audit trail.
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "version",
            "structured_extraction",
            "summary",
            "provider",
            "provider_model",
            "prompt_version",
            "provider_metadata",
            "generation_started_at",
            "generation_completed_at",
            "generation_duration_ms",
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "approved_by",
            "approved_at",
            "final_clinical_note",
        ]


class AIConsultationDraftListSerializer(serializers.ModelSerializer):
    review_label = serializers.SerializerMethodField()

    def get_review_label(self, obj):
        return draft_review_label(obj)

    """Lightweight serializer for list views"""
    consultation_id = serializers.IntegerField(source="consultation.id", read_only=True)
    patient_name = serializers.CharField(
        source="consultation.patient.name", read_only=True
    )

    class Meta:
        model = AIConsultationDraft
        fields = [
            "review_label",
            "id",
            "consultation_id",
            "patient_name",
            "version",
            "status",
            "provider",
            "provider_model",
            "prompt_version",
            "summary",
            "reviewed_by",
            "approved_by",
            "created_at",
        ]


class DoctorReviewSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    ai_draft_version = serializers.IntegerField(source="ai_draft.version", read_only=True)

    class Meta:
        model = DoctorReview
        fields = [
            "id",
            "ai_draft",
            "doctor",
            "hospital",
            "action",
            "section",
            "ai_value",
            "doctor_value",
            "notes",
            "created_at",
            "doctor_name",
            "ai_draft_version",
        ]
        read_only_fields = ["id", "created_at", "hospital"]


class ClinicalExtractionSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalExtractionSchema
        fields = [
            "id",
            "version",
            "name",
            "description",
            "schema",
            "example_output",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AIPromptTemplateSerializer(serializers.ModelSerializer):
    schema_version_str = serializers.CharField(
        source="schema_version.version", read_only=True, allow_null=True
    )

    class Meta:
        model = AIPromptTemplate
        fields = [
            "id",
            "version",
            "name",
            "description",
            "system_prompt",
            "user_prompt_template",
            "schema_version",
            "recommended_temperature",
            "recommended_max_tokens",
            "is_active",
            "created_at",
            "updated_at",
            "schema_version_str",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]