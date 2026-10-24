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
        fields = [
            "id",
            "lab_test",
            "sample_type",
            "container_type",
            "sample_id",
            "collected_by",
            "collected_at",
            "collection_notes",
            "barcoded",
            "collected_by_name",
        ]
        read_only_fields = ["id", "collected_at", "collected_by_name"]


class SampleDispatchSerializer(serializers.ModelSerializer):
    dispatched_by_name = serializers.CharField(source="dispatched_by.get_full_name", read_only=True)
    received_by_name = serializers.CharField(source="received_by.get_full_name", read_only=True)

    class Meta:
        model = SampleDispatch
        fields = [
            "id",
            "lab_test",
            "dispatched_by",
            "dispatched_at",
            "received_by",
            "received_at",
            "status",
            "dispatch_notes",
            "external_lab",
            "dispatched_by_name",
            "received_by_name",
        ]
        read_only_fields = ["id", "dispatched_at", "received_at", "dispatched_by_name", "received_by_name"]


class LabResultSerializer(serializers.ModelSerializer):
    entered_by_name = serializers.CharField(source="entered_by.get_full_name", read_only=True)
    verified_by_name = serializers.CharField(source="verified_by.get_full_name", read_only=True)

    class Meta:
        model = LabResult
        fields = [
            "id",
            "lab_test",
            "result_data",
            "result_text",
            "reference_ranges",
            "abnormal_flags",
            "entered_by",
            "entered_at",
            "verified_by",
            "verified_at",
            "released_at",
            "is_verified",
            "is_released",
            "entered_by_name",
            "verified_by_name",
        ]
        read_only_fields = ["id", "entered_at", "verified_at", "released_at", "entered_by_name", "verified_by_name"]


class ResultVerificationSerializer(serializers.ModelSerializer):
    verified_by_name = serializers.CharField(source="verified_by.get_full_name", read_only=True)

    class Meta:
        model = ResultVerification
        fields = [
            "id",
            "lab_result",
            "verified_by",
            "verified_at",
            "comments",
            "action",
            "verified_by_name",
        ]
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
        fields = [
            "id",
            "hospital",
            "name",
            "patient",
            "doctor",
            "visit",
            "priority",
            "result",
            "status",
            "test_date",
            "collected_at",
            "dispatched_at",
            "received_at",
            "processed_at",
            "verified_at",
            "released_at",
            "patient_name",
            "hospital_name",
            "doctor_name",
            "sample_collection",
            "sample_dispatch",
            "lab_result",
        ]
        # status and result move only through the collect/dispatch/receive/
        # process/enter/verify/release actions.
        read_only_fields = [
            "id", "result", "status", "test_date", "collected_at", "dispatched_at", "received_at",
            "processed_at", "verified_at", "released_at",
            "patient_name", "hospital_name", "doctor_name",
            "sample_collection", "sample_dispatch", "lab_result"
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


class LabTestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = [
            "id", "name", "patient", "doctor", "visit", "hospital", "priority", "status"
        ]
        read_only_fields = ["id", "status"]