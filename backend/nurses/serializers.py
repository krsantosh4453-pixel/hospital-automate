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


class NursingAssessmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    nurse_name = serializers.CharField(source="nurse.name", read_only=True)

    class Meta:
        model = NursingAssessment
        fields = [
            "id",
            "patient",
            "admission",
            "hospital",
            "nurse",
            "assessment_type",
            "vitals",
            "pain_score",
            "level_of_consciousness",
            "skin_condition",
            "respiratory_assessment",
            "cardiovascular_assessment",
            "gastrointestinal_assessment",
            "neurological_assessment",
            "mobility_status",
            "nutritional_status",
            "elimination_status",
            "psychosocial_assessment",
            "plan_of_care",
            "assessed_at",
            "patient_name",
            "hospital_name",
            "nurse_name",
        ]
        read_only_fields = ["id", "assessed_at", "patient_name", "hospital_name", "nurse_name"]


class NursingNoteSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    nurse_name = serializers.CharField(source="nurse.name", read_only=True)

    class Meta:
        model = NursingNote
        fields = [
            "id",
            "patient",
            "admission",
            "hospital",
            "nurse",
            "note_type",
            "note",
            "created_at",
            "patient_name",
            "hospital_name",
            "nurse_name",
        ]
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "nurse_name"]


class CareTaskSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    assigned_nurse_name = serializers.CharField(source="assigned_nurse.name", read_only=True)
    completed_by_name = serializers.CharField(source="completed_by.name", read_only=True)

    class Meta:
        model = CareTask
        fields = [
            "id",
            "patient",
            "admission",
            "hospital",
            "assigned_nurse",
            "task_type",
            "description",
            "priority",
            "status",
            "scheduled_at",
            "started_at",
            "completed_at",
            "completed_by",
            "notes",
            "created_at",
            "patient_name",
            "hospital_name",
            "assigned_nurse_name",
            "completed_by_name",
        ]
        read_only_fields = [
            "id", "created_at", "started_at", "completed_at",
            "patient_name", "hospital_name", "assigned_nurse_name", "completed_by_name"
        ]


class MARAdministrationSerializer(serializers.ModelSerializer):
    administered_by_name = serializers.CharField(source="administered_by.name", read_only=True)
    is_delayed = serializers.SerializerMethodField()

    def get_is_delayed(self, obj):
        """A due dose more than 30 minutes past its scheduled time."""
        from datetime import timedelta
        from django.utils import timezone
        return obj.status == "Scheduled" and obj.scheduled_time < timezone.now() - timedelta(minutes=30)

    class Meta:
        model = MARAdministration
        fields = [
            "id",
            "mar",
            "scheduled_time",
            "administered_time",
            "status",
            "administered_by",
            "dose_given",
            "route_given",
            "site",
            "reason_held",
            "reason_refused",
            "notes",
            "is_prn",
            "is_delayed",
            "recorded_by",
            "created_at",
            "administered_by_name",
        ]
        # Outcomes are recorded through the dose actions, never by editing fields.
        read_only_fields = ["id", "created_at", "administered_by_name", "status", "administered_time",
                            "administered_by", "recorded_by", "is_prn", "is_delayed"]


class MARSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    administrations = MARAdministrationSerializer(many=True, read_only=True)

    class Meta:
        model = MAR
        fields = [
            "id",
            "patient",
            "admission",
            "hospital",
            "prescription",
            "prescription_item",
            "medicine_name",
            "dose",
            "route",
            "frequency",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "patient_name",
            "hospital_name",
            "administrations",
        ]
        read_only_fields = ["id", "created_at", "patient_name", "hospital_name", "administrations"]


class PatientAssignmentSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.name", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)

    class Meta:
        model = PatientAssignment
        fields = [
            "id",
            "nurse",
            "patient",
            "admission",
            "hospital",
            "shift",
            "shift_date",
            "assigned_at",
            "is_active",
            "nurse_name",
            "patient_name",
            "hospital_name",
        ]
        read_only_fields = ["id", "assigned_at", "nurse_name", "patient_name", "hospital_name"]