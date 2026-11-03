from rest_framework import serializers
from .models import (
    Admission,
    BedAllocation,
    DischargePlan,
    DischargeSummary,
    DischargeNote,
)


class BedAllocationSerializer(serializers.ModelSerializer):
    bed_number = serializers.CharField(source="bed.bed_number", read_only=True)
    room_number = serializers.CharField(source="bed.room.room_number", read_only=True)
    ward_name = serializers.CharField(source="bed.room.ward.name", read_only=True)
    patient_name = serializers.CharField(source="admission.patient.name", read_only=True)

    class Meta:
        model = BedAllocation
        fields = [
            "id",
            "admission",
            "bed",
            "allocated_at",
            "released_at",
            "is_active",
            "bed_number",
            "room_number",
            "ward_name",
            "patient_name",
        ]
        read_only_fields = ["id", "allocated_at", "released_at", "bed_number", "room_number", "ward_name", "patient_name"]


class AdmissionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    admitting_doctor_name = serializers.CharField(source="admitting_doctor.name", read_only=True)
    bed_allocations = BedAllocationSerializer(many=True, read_only=True)
    current_bed = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = [
            "id",
            "patient",
            "hospital",
            "admission_date",
            "discharge_date",
            "status",
            "reason",
            "admitting_doctor",
            "bed_allocations",
            "current_bed",
            "patient_name",
            "hospital_name",
            "admitting_doctor_name",
        ]
        read_only_fields = ["id", "admission_date", "discharge_date", "patient_name", "hospital_name", "admitting_doctor_name", "bed_allocations", "current_bed"]

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
        hospital_id = self.initial_data.get("hospital")
        if hospital_id and value:
            from clinical.serializers import _patient_belongs_to_hospital
            from hospital.models import Hospital
            try:
                hospital = Hospital.objects.get(pk=hospital_id)
            except Hospital.DoesNotExist:
                raise serializers.ValidationError("Invalid hospital.")
            if not _patient_belongs_to_hospital(value, hospital):
                raise serializers.ValidationError(
                    "This patient is not registered in this hospital."
                )
        return value

    def get_current_bed(self, obj):
        active = obj.bed_allocations.filter(is_active=True).first()
        if active:
            return BedAllocationSerializer(active).data
        return None


class DischargePlanSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="admission.patient.name", read_only=True)
    hospital_name = serializers.CharField(source="admission.hospital.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = DischargePlan
        fields = [
            "id",
            "admission",
            "instructions",
            "pending_tasks",
            "medications_reconciled",
            "patient_counselled",
            "follow_up_arranged",
            "documents_handed_over",
            "created_by",
            "created_at",
            "patient_name",
            "hospital_name",
            "created_by_name",
        ]
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "created_by_name"]


class DischargeSummarySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="admission.patient.name", read_only=True)
    hospital_name = serializers.CharField(source="admission.hospital.name", read_only=True)
    authorized_doctor_name = serializers.CharField(source="authorized_doctor.name", read_only=True)

    class Meta:
        model = DischargeSummary
        fields = [
            "id",
            "admission",
            "summary",
            "authorized_doctor",
            "finalized",
            "finalized_at",
            "created_at",
            "patient_name",
            "hospital_name",
            "authorized_doctor_name",
        ]
        # Finalization goes through POST discharge-summaries/{id}/finalize/.
        read_only_fields = ["id", "created_at", "finalized", "finalized_at", "authorized_doctor",
                            "patient_name", "hospital_name", "authorized_doctor_name"]


class DischargeNoteSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="admission.patient.name", read_only=True)
    hospital_name = serializers.CharField(source="admission.hospital.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = DischargeNote
        fields = [
            "id",
            "admission",
            "note",
            "created_by",
            "created_at",
            "patient_name",
            "hospital_name",
            "created_by_name",
        ]
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "created_by_name"]