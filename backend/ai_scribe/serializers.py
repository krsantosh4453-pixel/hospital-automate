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
        fields = "__all__"
        read_only_fields = [
            "started_at",
            "recording_started_at",
            "recording_stopped_at",
            "completed_at",
            "created_by",
        ]

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
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "processing_started_at",
            "processing_completed_at",
        ]


class AIConsultationDraftSerializer(serializers.ModelSerializer):
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
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
            "generation_started_at",
            "generation_completed_at",
            "generation_duration_ms",
            "reviewed_at",
            "approved_at",
        ]


class AIConsultationDraftListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    consultation_id = serializers.IntegerField(source="consultation.id", read_only=True)
    patient_name = serializers.CharField(
        source="consultation.patient.name", read_only=True
    )

    class Meta:
        model = AIConsultationDraft
        fields = [
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
        fields = "__all__"
        read_only_fields = ["created_at", "hospital"]


class ClinicalExtractionSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalExtractionSchema
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class AIPromptTemplateSerializer(serializers.ModelSerializer):
    schema_version_str = serializers.CharField(
        source="schema_version.version", read_only=True, allow_null=True
    )

    class Meta:
        model = AIPromptTemplate
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]