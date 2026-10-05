from rest_framework import serializers
from .models import (
    Nurse,
    NursingAssessment,
    NursingNote,
    CareTask,
    MAR,
    MARAdministration,
    PatientAssignment,
)


class NurseSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)

    class Meta:
        model = Nurse
        fields = [
            "id",
            "hospital",
            "hospital_name",
            "name",
            "phone",
            "email",
            "department",
            "shift",
            "qualification",
            "joining_date",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "hospital_name"]


class NursingAssessmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    nurse_name = serializers.CharField(source="nurse.name", read_only=True)

    class Meta:
        model = NursingAssessment
        fields = "__all__"
        read_only_fields = ["id", "assessed_at", "patient_name", "hospital_name", "nurse_name"]


class NursingNoteSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    nurse_name = serializers.CharField(source="nurse.name", read_only=True)

    class Meta:
        model = NursingNote
        fields = "__all__"
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "nurse_name"]


class CareTaskSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    assigned_nurse_name = serializers.CharField(source="assigned_nurse.name", read_only=True)
    completed_by_name = serializers.CharField(source="completed_by.name", read_only=True)

    class Meta:
        model = CareTask
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "started_at", "completed_at",
            "patient_name", "hospital_name", "assigned_nurse_name", "completed_by_name"
        ]


class MARAdministrationSerializer(serializers.ModelSerializer):
    administered_by_name = serializers.CharField(source="administered_by.name", read_only=True)

    class Meta:
        model = MARAdministration
        fields = "__all__"
        read_only_fields = ["id", "created_at", "administered_by_name"]


class MARSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    administrations = MARAdministrationSerializer(many=True, read_only=True)

    class Meta:
        model = MAR
        fields = "__all__"
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "administrations"]


class PatientAssignmentSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.name", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)

    class Meta:
        model = PatientAssignment
        fields = "__all__"
        read_only_fields = ["id", "assigned_at", "nurse_name", "patient_name", "hospital_name"]