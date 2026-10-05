from rest_framework import serializers
from .models import (
    LabTest,
    SampleCollection,
    SampleDispatch,
    LabResult,
    ResultVerification,
)


class SampleCollectionSerializer(serializers.ModelSerializer):
    collected_by_name = serializers.CharField(source="collected_by.name", read_only=True)

    class Meta:
        model = SampleCollection
        fields = "__all__"
        read_only_fields = ["id", "collected_at", "collected_by_name"]


class SampleDispatchSerializer(serializers.ModelSerializer):
    dispatched_by_name = serializers.CharField(source="dispatched_by.get_full_name", read_only=True)
    received_by_name = serializers.CharField(source="received_by.get_full_name", read_only=True)

    class Meta:
        model = SampleDispatch
        fields = "__all__"
        read_only_fields = ["id", "dispatched_at", "received_at", "dispatched_by_name", "received_by_name"]


class LabResultSerializer(serializers.ModelSerializer):
    entered_by_name = serializers.CharField(source="entered_by.get_full_name", read_only=True)
    verified_by_name = serializers.CharField(source="verified_by.get_full_name", read_only=True)

    class Meta:
        model = LabResult
        fields = "__all__"
        read_only_fields = ["id", "entered_at", "verified_at", "released_at", "entered_by_name", "verified_by_name"]


class ResultVerificationSerializer(serializers.ModelSerializer):
    verified_by_name = serializers.CharField(source="verified_by.get_full_name", read_only=True)

    class Meta:
        model = ResultVerification
        fields = "__all__"
        read_only_fields = ["id", "verified_at", "verified_by_name"]


class LabTestSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    sample_collection = SampleCollectionSerializer(read_only=True)
    sample_dispatch = SampleDispatchSerializer(read_only=True)
    lab_result = LabResultSerializer(read_only=True)

    class Meta:
        model = LabTest
        fields = "__all__"
        read_only_fields = [
            "id", "test_date", "collected_at", "dispatched_at", "received_at",
            "processed_at", "verified_at", "released_at",
            "patient_name", "hospital_name", "doctor_name",
            "sample_collection", "sample_dispatch", "lab_result"
        ]


class LabTestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = [
            "name", "patient", "doctor", "visit", "hospital", "priority"
        ]