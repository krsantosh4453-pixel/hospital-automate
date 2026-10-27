from rest_framework import serializers
from hospital.models import Hospital
from .models import (
    EmergencyVisit,
    EmergencyTriage,
    EmergencyVitals,
    EmergencyOrder,
    EmergencyMedication,
)


class EmergencyTriageSerializer(serializers.ModelSerializer):
    triaged_by_name = serializers.CharField(source="triaged_by.name", read_only=True)

    class Meta:
        model = EmergencyTriage
        fields = [
            "id",
            "visit",
            "chief_complaint",
            "vitals",
            "pain_score",
            "glasgow_coma_scale",
            "triage_notes",
            "triaged_by",
            "triaged_at",
            "triaged_by_name",
        ]
        read_only_fields = ["id", "triaged_at", "triaged_by_name"]


class EmergencyVitalsSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.name", read_only=True)

    class Meta:
        model = EmergencyVitals
        fields = [
            "id",
            "visit",
            "temperature",
            "systolic_bp",
            "diastolic_bp",
            "heart_rate",
            "respiratory_rate",
            "spo2",
            "blood_sugar",
            "recorded_by",
            "recorded_at",
            "recorded_by_name",
        ]
        read_only_fields = ["id", "recorded_at", "recorded_by_name"]


class EmergencyOrderSerializer(serializers.ModelSerializer):
    ordered_by_name = serializers.CharField(source="ordered_by.name", read_only=True)

    class Meta:
        model = EmergencyOrder
        fields = [
            "id",
            "visit",
            "order_type",
            "description",
            "status",
            "ordered_by",
            "ordered_at",
            "completed_at",
            "result",
            "ordered_by_name",
        ]
        read_only_fields = ["id", "ordered_at", "completed_at", "ordered_by_name"]


class EmergencyMedicationSerializer(serializers.ModelSerializer):
    prescribed_by_name = serializers.CharField(source="prescribed_by.name", read_only=True)
    administered_by_name = serializers.CharField(source="administered_by.name", read_only=True)

    class Meta:
        model = EmergencyMedication
        fields = [
            "id",
            "visit",
            "name",
            "dose",
            "route",
            "frequency",
            "duration",
            "prescribed_by",
            "prescribed_at",
            "administered",
            "administered_by",
            "administered_at",
            "prescribed_by_name",
            "administered_by_name",
        ]
        read_only_fields = ["id", "prescribed_at", "administered_at", "prescribed_by_name", "administered_by_name"]


class EmergencyVisitSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    attending_doctor_name = serializers.CharField(source="attending_doctor.name", read_only=True)
    triage = EmergencyTriageSerializer(read_only=True)
    vitals_records = EmergencyVitalsSerializer(many=True, read_only=True)
    orders = EmergencyOrderSerializer(many=True, read_only=True)
    medications = EmergencyMedicationSerializer(many=True, read_only=True)

    class Meta:
        model = EmergencyVisit
        fields = [
            "id",
            "patient",
            "hospital",
            "visit_number",
            "triage_level",
            "status",
            "arrival_time",
            "triage_time",
            "consultation_start_time",
            "discharge_time",
            "remarks",
            "attending_doctor",
            "disposition",
            "discharge_diagnosis",
            "follow_up_instructions",
            "patient_name",
            "hospital_name",
            "attending_doctor_name",
            "triage",
            "vitals_records",
            "orders",
            "medications",
        ]
        read_only_fields = [
            "id", "visit_number", "arrival_time", "triage_time", "consultation_start_time",
            "discharge_time", "patient_name", "hospital_name",
            "attending_doctor_name", "triage", "vitals_records", "orders", "medications"
        ]

    def validate_hospital(self, value):
        """Ensure user has access to the hospital."""
        request = self.context.get("request")
        if request and value:
            from users.permissions import get_user_hospital_ids
            user_hospital_ids = get_user_hospital_ids(request.user)
            if value.id not in user_hospital_ids:
                raise serializers.ValidationError(
                    "You do not have access to this hospital."
                )
        return value

    def validate_patient(self, value):
        """Ensure patient belongs to the hospital."""
        hospital = self.initial_data.get("hospital")
        if hospital and value:
            from clinical.serializers import _patient_belongs_to_hospital
            if not _patient_belongs_to_hospital(value, hospital):
                raise serializers.ValidationError(
                    "This patient is not registered in this hospital."
                )
        return value


class EmergencyVisitCreateSerializer(serializers.ModelSerializer):
    hospital = serializers.PrimaryKeyRelatedField(
        queryset=Hospital.objects.none(), required=False, allow_null=True
    )

    class Meta:
        model = EmergencyVisit
        fields = [
            "patient", "hospital", "triage_level", "remarks", "attending_doctor"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set hospital queryset based on user permissions
        request = self.context.get("request")
        if request:
            from users.permissions import get_user_hospital_ids
            user_hospital_ids = get_user_hospital_ids(request.user)
            self.fields["hospital"].queryset = Hospital.objects.filter(id__in=user_hospital_ids)

    def validate_hospital(self, value):
        """Ensure user has access to the hospital."""
        request = self.context.get("request")
        if request and value:
            from users.permissions import get_user_hospital_ids
            user_hospital_ids = get_user_hospital_ids(request.user)
            if value.id not in user_hospital_ids:
                raise serializers.ValidationError(
                    "You do not have access to this hospital."
                )
        return value

    def validate_patient(self, value):
        """Ensure patient belongs to the hospital."""
        hospital = self.initial_data.get("hospital")
        if hospital and value:
            from clinical.serializers import _patient_belongs_to_hospital
            if not _patient_belongs_to_hospital(value, hospital):
                raise serializers.ValidationError(
                    "This patient is not registered in this hospital."
                )
        return value

    def create(self, validated_data):
        # Set hospital from context if not provided
        if "hospital" not in validated_data:
            scoped_hospital = self.context.get("scoped_hospital")
            if scoped_hospital:
                validated_data["hospital"] = scoped_hospital
        return super().create(validated_data)