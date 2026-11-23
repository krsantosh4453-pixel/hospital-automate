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

    def validate_vitals(self, value):
        """
        Ward vitals ({"bp", "pulse", "respiratory_rate", "temperature",
        "spo2"}) get the same structural limits as an OPD reading
        (clinical.models.VitalSign): whole numbers where that model stores
        integers, at most two decimals for temperature, nothing negative,
        SpO2 at most 100. No "normal range" is applied. Values are stored as
        sent, so "37.1" stays "37.1"; an empty value means "not measured".
        """
        return check_ward_vitals(value)


WARD_VITAL_KEYS = ("bp", "pulse", "respiratory_rate", "temperature", "spo2")


def _ward_number(key, raw, whole, max_value=None):
    from decimal import Decimal, InvalidOperation

    text = str(raw).strip()
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise serializers.ValidationError({key: "Enter a number."})
    if not number.is_finite():
        raise serializers.ValidationError({key: "Enter a number."})
    if number < 0:
        raise serializers.ValidationError({key: "Cannot be negative."})
    if whole and number != number.to_integral_value():
        raise serializers.ValidationError({key: "Enter a whole number."})
    if not whole and number.as_tuple().exponent < -2:
        raise serializers.ValidationError({key: "Use at most two decimals."})
    if max_value is not None and number > max_value:
        raise serializers.ValidationError({key: f"Cannot be more than {max_value}."})


def check_ward_vitals(value):
    """The validated ward ``vitals`` JSON (unchanged), or ValidationError."""
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise serializers.ValidationError("Vitals must be an object.")
    unknown = sorted(set(value) - set(WARD_VITAL_KEYS))
    if unknown:
        raise serializers.ValidationError(
            f"Unknown vitals: {', '.join(unknown)}. Use {', '.join(WARD_VITAL_KEYS)}.")
    for key, raw in value.items():
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue  # not measured
        if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
            raise serializers.ValidationError({key: "Enter a number."})
        if key == "bp":
            parts = str(raw).split("/")
            if len(parts) != 2 or not all(p.strip() for p in parts):
                raise serializers.ValidationError({"bp": "Give both numbers, e.g. 120/80."})
            for part in parts:
                _ward_number("bp", part, whole=True)
        elif key == "temperature":
            # DecimalField(max_digits=5, decimal_places=2) on VitalSign.
            _ward_number(key, raw, whole=False, max_value=999.99)
        elif key == "spo2":
            _ward_number(key, raw, whole=True, max_value=100)
        else:
            _ward_number(key, raw, whole=True)
    return value


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
        """A due dose past its scheduled time plus the configured grace (default 30 minutes)."""
        from django.utils import timezone

        from .scheduling import overdue_grace
        return obj.status == "Scheduled" and obj.scheduled_time < timezone.now() - overdue_grace()

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
    # Optional on create: schedule the doses with the order (nurses/scheduling.py).
    first_dose = serializers.ChoiceField(choices=["now", "at", "next_round"], write_only=True, required=False,
                                         allow_null=True)
    first_dose_at = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
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
            "instructions",
            "prn_min_interval_minutes",
            "prn_max_doses_per_24h",
            "ordered_by",
            "ordered_by_name",
            "created_at",
            "patient_name",
            "hospital_name",
            "administrations",
            "first_dose",
            "first_dose_at",
        ]
        read_only_fields = ["id", "ordered_by", "ordered_by_name", "created_at", "patient_name", "hospital_name",
                            "administrations"]

    def get_ordered_by_name(self, obj) -> str:
        """
        The ordering doctor as staff and patients know them: the Doctor
        profile name at the order's hospital ("Dr Asha Mehta"), then the
        account's full name, then the username (the codebase convention).
        The list view annotates the profile name to avoid a query per row.
        """
        user = obj.ordered_by
        if user is None:
            return ""
        doctor_name = getattr(obj, "ordered_by_doctor_name", None)
        if doctor_name is None and not hasattr(obj, "ordered_by_doctor_name"):
            from users.staff_links import staff_display_name

            return staff_display_name(user, obj.hospital_id, self.context)
        return (doctor_name or "").strip() or user.get_full_name() or user.username

    def validate_frequency(self, value):
        # H-01: refused here, so the doctor fixes it before any dose is scheduled.
        from .frequency import FrequencyError, parse_frequency

        try:
            parse_frequency(value)
        except FrequencyError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value.strip()

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
        self._check_prn_limits(attrs, get)
        return attrs

    @staticmethod
    def _check_prn_limits(attrs, get):
        # H-10: limits belong to as-needed orders only, within sane bounds.
        from .frequency import PRN, FrequencyError, parse_frequency
        from .prn_limits import MAX_DOSES_PER_24H, MAX_INTERVAL_MINUTES, MIN_INTERVAL_MINUTES

        interval, max_doses = get("prn_min_interval_minutes"), get("prn_max_doses_per_24h")
        if interval is None and max_doses is None:
            return
        try:
            prn = parse_frequency(get("frequency")).kind == PRN
        except FrequencyError:
            prn = False
        sent_limits = "prn_min_interval_minutes" in attrs or "prn_max_doses_per_24h" in attrs
        if not prn and not sent_limits:
            # The order stops being as-needed: its stored limits no longer apply.
            attrs["prn_min_interval_minutes"] = None
            attrs["prn_max_doses_per_24h"] = None
            return
        if not prn:
            raise serializers.ValidationError(
                {"prn_min_interval_minutes": "Dose limits apply only to an as-needed (PRN/SOS) order."})
        if interval is not None and not MIN_INTERVAL_MINUTES <= interval <= MAX_INTERVAL_MINUTES:
            raise serializers.ValidationError({"prn_min_interval_minutes": (
                f"Enter {MIN_INTERVAL_MINUTES} to {MAX_INTERVAL_MINUTES} minutes between doses.")})
        if max_doses is not None and not 1 <= max_doses <= MAX_DOSES_PER_24H:
            raise serializers.ValidationError(
                {"prn_max_doses_per_24h": f"Enter 1 to {MAX_DOSES_PER_24H} doses in 24 hours."})


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


class MedicationRoundSerializer(serializers.ModelSerializer):
    """A hospital's configured medication round (e.g. 08:00 Morning)."""

    class Meta:
        from .models import MedicationRound

        model = MedicationRound
        fields = ["id", "hospital", "label", "time", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
