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
        fields = "__all__"
        read_only_fields = ["id", "allocated_at", "released_at", "bed_number", "room_number", "ward_name", "patient_name"]


class AdmissionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    admitting_doctor_name = serializers.CharField(source="admitting_doctor.name", read_only=True)
    bed_allocations = BedAllocationSerializer(many=True, read_only=True)
    current_bed = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = "__all__"
        read_only_fields = ["id", "admission_date", "discharge_date", "patient_name", "hospital_name", "admitting_doctor_name", "bed_allocations", "current_bed"]

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
        fields = "__all__"
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "created_by_name"]


class DischargeSummarySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="admission.patient.name", read_only=True)
    hospital_name = serializers.CharField(source="admission.hospital.name", read_only=True)
    authorized_doctor_name = serializers.CharField(source="authorized_doctor.name", read_only=True)

    class Meta:
        model = DischargeSummary
        fields = "__all__"
        read_only_fields = ["id", "created_at", "finalized_at", "patient_name", "hospital_name", "authorized_doctor_name"]


class DischargeNoteSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="admission.patient.name", read_only=True)
    hospital_name = serializers.CharField(source="admission.hospital.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = DischargeNote
        fields = "__all__"
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "created_by_name"]