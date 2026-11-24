from rest_framework import serializers
from .models import (
    LabTest,
    SampleCollection,
    SampleDispatch,
    LabReferenceRange,
    LabResult,
    ResultVerification,
    ImagingStudy,
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
    critical_acknowledged_by_name = serializers.CharField(source="critical_acknowledged_by.get_full_name",
                                                          read_only=True)

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
            "flag_details",
            "has_critical",
            "critical_acknowledged_by",
            "critical_acknowledged_by_name",
            "critical_acknowledged_at",
            "critical_acknowledgement_note",
        ]
        # BUG-06: every field is written by the enter/verify/release actions only.
        read_only_fields = fields


class LabReferenceRangeSerializer(serializers.ModelSerializer):
    """H-14: one parameter's limits. The limits must be ordered: critical low <= low < high <= critical high."""

    class Meta:
        model = LabReferenceRange
        fields = ["id", "hospital", "test_name", "parameter", "unit", "sex", "low", "high",
                  "critical_low", "critical_high", "is_active", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]
        extra_kwargs = {"hospital": {"required": False}}

    def validate(self, attrs):
        def value(name):
            return attrs[name] if name in attrs else getattr(self.instance, name, None)

        for name in ("test_name", "parameter"):
            text = str(value(name) or "").strip()
            if not text:
                raise serializers.ValidationError({name: "This field is required."})
            if name in attrs:
                attrs[name] = text
        low, high = value("low"), value("high")
        critical_low, critical_high = value("critical_low"), value("critical_high")
        if all(v is None for v in (low, high, critical_low, critical_high)):
            raise serializers.ValidationError("Enter at least one limit.")
        ordered = [v for v in (critical_low, low, high, critical_high) if v is not None]
        if ordered != sorted(ordered):
            raise serializers.ValidationError(
                "Limits must be in order: critical low, low, high, critical high.")
        if low is not None and high is not None and low == high:
            raise serializers.ValidationError({"high": "High must be above low."})
        return attrs


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
            "self_verified",
            "verified_by_name",
        ]
        read_only_fields = ["id", "verified_at", "verified_by_name", "self_verified"]


class LabTestSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    sample_collection = SampleCollectionSerializer(read_only=True)
    sample_dispatch = SampleDispatchSerializer(read_only=True)
    lab_result = LabResultSerializer(read_only=True)
    # L-1: how often a result was sent back, and the latest reason. The rejected
    # values themselves stay in LabResultRejection and the audit log.
    rejection_count = serializers.SerializerMethodField()
    last_rejection_reason = serializers.SerializerMethodField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return check_visit_of_patient(attrs, self.instance)

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
            "rejection_count",
            "last_rejection_reason",
        ]
        # status and result move only through the collect/dispatch/receive/
        # process/enter/verify/release actions.
        read_only_fields = [
            "id", "result", "status", "test_date", "collected_at", "dispatched_at", "received_at",
            "processed_at", "verified_at", "released_at",
            "patient_name", "hospital_name", "doctor_name",
            "sample_collection", "sample_dispatch", "lab_result"
        ]

    # The list view annotates both (no extra query); a single test read
    # after an action falls back to one small query.
    def get_rejection_count(self, obj) -> int:
        total = getattr(obj, "rejection_total", None)
        return total if total is not None else obj.rejections.count()

    def get_last_rejection_reason(self, obj) -> str:
        if hasattr(obj, "latest_rejection_reason"):
            return obj.latest_rejection_reason or ""
        latest = obj.rejections.order_by("-rejected_at", "-pk").values_list("reason", flat=True).first()
        return latest or ""

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


def check_visit_of_patient(attrs, instance=None):
    """INT-002 (Prompt 5): an order's visit must be a visit of the same patient."""
    visit = attrs.get("visit", getattr(instance, "visit", None))
    patient = attrs.get("patient", getattr(instance, "patient", None))
    if visit is not None and patient is not None and visit.patient_id != patient.pk:
        raise serializers.ValidationError({"visit": "This visit belongs to another patient."})
    return attrs


class LabTestCreateSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        return check_visit_of_patient(attrs, self.instance)

    class Meta:
        model = LabTest
        fields = [
            "id", "name", "patient", "doctor", "visit", "hospital", "priority", "status"
        ]
        read_only_fields = ["id", "status"]

class ImagingStudySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    patient_age = serializers.IntegerField(source="patient.age", read_only=True)
    patient_gender = serializers.CharField(source="patient.gender", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    ordered_by_name = serializers.CharField(source="ordered_by.name", read_only=True)
    reported_by_name = serializers.CharField(source="reported_by.name", read_only=True, default="")

    class Meta:
        model = ImagingStudy
        fields = [
            "id", "hospital", "patient", "visit", "accession_number", "modality", "body_part", "indication",
            "priority", "status", "ordered_by", "ordered_at", "scheduled_for", "performed_at", "performed_by",
            "technician_notes", "findings", "impression", "reported_by", "reported_at",
            "patient_name", "patient_age", "patient_gender", "hospital_name", "ordered_by_name", "reported_by_name",
        ]
        # Only the order itself is written through create; every later field
        # moves through the schedule / perform / report actions.
        read_only_fields = [
            "id", "accession_number", "status", "ordered_by", "ordered_at", "scheduled_for", "performed_at",
            "performed_by", "technician_notes", "findings", "impression", "reported_by", "reported_at",
        ]
        extra_kwargs = {"hospital": {"required": False}}

    def validate(self, attrs):
        return check_visit_of_patient(attrs, self.instance)

    def validate_body_part(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name the body part or region.")
        return value.strip()

    def validate_indication(self, value):
        if not value.strip():
            raise serializers.ValidationError("Give the clinical question for the radiologist.")
        return value.strip()
