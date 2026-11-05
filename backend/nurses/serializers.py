from rest_framework import serializers

from users.models import StaffRole
from users.staff_links import link_profile_login
from .models import (
    Nurse,
    NurseWardAssignment,
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
            "user",
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

    def validate(self, attrs):
        """A linked login must be an active Nurse member of the same hospital."""
        attrs = super().validate(attrs)
        return link_profile_login(attrs, self.instance, StaffRole.NURSE, "nurse_profiles")

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
    medicine_name = serializers.CharField(source="mar.medicine_name", read_only=True)
    dose = serializers.CharField(source="mar.dose", read_only=True)
    route = serializers.CharField(source="mar.route", read_only=True)
    frequency = serializers.CharField(source="mar.frequency", read_only=True)
    patient = serializers.IntegerField(source="mar.patient_id", read_only=True)
    patient_name = serializers.CharField(source="mar.patient.name", read_only=True)
    hospital = serializers.IntegerField(source="mar.hospital_id", read_only=True)
    admission = serializers.IntegerField(source="mar.admission_id", read_only=True)
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
            "medicine_name",
            "dose",
            "route",
            "frequency",
            "patient",
            "patient_name",
            "hospital",
            "admission",
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
    ordered_by_name = serializers.SerializerMethodField()

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
            "ordered_by",
            "ordered_by_name",
            "created_at",
            "patient_name",
            "hospital_name",
            "administrations",
        ]
        read_only_fields = ["id", "ordered_by", "ordered_by_name", "created_at", "patient_name", "hospital_name",
                            "administrations"]

    def get_ordered_by_name(self, obj):
        user = obj.ordered_by
        return (user.get_full_name() or user.username) if user else ""

    def validate(self, attrs):
        # The order must come from that patient's own prescription.
        get = lambda name: attrs.get(name, getattr(self.instance, name, None))  # noqa: E731
        patient, prescription, item, admission = get("patient"), get("prescription"), get("prescription_item"), get("admission")
        if prescription is not None and patient is not None and prescription.patient_id != patient.id:
            raise serializers.ValidationError({"prescription": "This prescription is for another patient."})
        if item is not None and prescription is not None and item.prescription_id != prescription.id:
            raise serializers.ValidationError({"prescription_item": "This medicine is not on that prescription."})
        if admission is not None and patient is not None and admission.patient_id != patient.id:
            raise serializers.ValidationError({"admission": "This admission is for another patient."})
        return attrs


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

class NurseWardAssignmentSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.name", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)

    class Meta:
        model = NurseWardAssignment
        fields = [
            "id",
            "nurse",
            "ward",
            "hospital",
            "shift",
            "shift_date",
            "is_active",
            "assigned_at",
            "nurse_name",
            "ward_name",
        ]
        read_only_fields = ["id", "assigned_at", "nurse_name", "ward_name"]
