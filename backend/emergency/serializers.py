from rest_framework import serializers
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
        fields = "__all__"
        read_only_fields = ["id", "triaged_at", "triaged_by_name"]


class EmergencyVitalsSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.name", read_only=True)

    class Meta:
        model = EmergencyVitals
        fields = "__all__"
        read_only_fields = ["id", "recorded_at", "recorded_by_name"]


class EmergencyOrderSerializer(serializers.ModelSerializer):
    ordered_by_name = serializers.CharField(source="ordered_by.name", read_only=True)

    class Meta:
        model = EmergencyOrder
        fields = "__all__"
        read_only_fields = ["id", "ordered_at", "completed_at", "ordered_by_name"]


class EmergencyMedicationSerializer(serializers.ModelSerializer):
    prescribed_by_name = serializers.CharField(source="prescribed_by.name", read_only=True)
    administered_by_name = serializers.CharField(source="administered_by.name", read_only=True)

    class Meta:
        model = EmergencyMedication
        fields = "__all__"
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
        fields = "__all__"
        read_only_fields = [
            "id", "arrival_time", "triage_time", "consultation_start_time",
            "discharge_time", "patient_name", "hospital_name",
            "attending_doctor_name", "triage", "vitals_records", "orders", "medications"
        ]


class EmergencyVisitCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyVisit
        fields = [
            "patient", "hospital", "triage_level", "remarks", "attending_doctor"
        ]