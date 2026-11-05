from rest_framework import serializers

from .models import (
    Ambulance,
    AmbulanceTrip,
    LaundryBatch,
    LeaveRequest,
    MortuaryRecord,
    OperatingTheatre,
    OTBooking,
    PatientFeedback,
    SterileSet,
    SterilizationCycle,
    TextTemplate,
)


def _name(user):
    return (user.get_full_name() or user.username) if user else ""


class _Base(serializers.ModelSerializer):
    """Hospital comes from the acting hospital; status only changes through actions."""

    def get_fields(self):
        fields = super().get_fields()
        if "hospital" in fields:
            fields["hospital"].required = False
        return fields


class OperatingTheatreSerializer(_Base):
    class Meta:
        model = OperatingTheatre
        fields = ["id", "hospital", "name", "is_active"]
        # Uniqueness per hospital is the database constraint; the hospital is set server-side.
        validators = []


class OTBookingSerializer(_Base):
    theatre_name = serializers.CharField(source="theatre.name", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    surgeon_name = serializers.CharField(source="surgeon.name", read_only=True)

    class Meta:
        model = OTBooking
        fields = ["id", "hospital", "theatre", "theatre_name", "patient", "patient_name", "surgeon", "surgeon_name",
                  "procedure_name", "anaesthesia", "scheduled_start", "scheduled_end", "status", "started_at",
                  "ended_at", "notes", "cancel_reason", "created_at"]
        read_only_fields = ["status", "started_at", "ended_at", "cancel_reason", "created_at"]

    def validate(self, attrs):
        start = attrs.get("scheduled_start", getattr(self.instance, "scheduled_start", None))
        end = attrs.get("scheduled_end", getattr(self.instance, "scheduled_end", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"scheduled_end": "The case must end after it starts."})
        return attrs


class AmbulanceSerializer(_Base):
    class Meta:
        model = Ambulance
        fields = ["id", "hospital", "vehicle_number", "kind", "status"]
        # Uniqueness per hospital is the database constraint; the hospital is set server-side.
        validators = []

    def validate_status(self, value):
        # Only the trip workflow puts an ambulance on or off a trip.
        if value == Ambulance.ON_TRIP or (self.instance and self.instance.status == Ambulance.ON_TRIP and value != Ambulance.ON_TRIP):
            raise serializers.ValidationError("Dispatch or complete a trip to change this.")
        return value


class AmbulanceTripSerializer(_Base):
    vehicle_number = serializers.CharField(source="ambulance.vehicle_number", read_only=True, default="")
    patient_name = serializers.CharField(source="patient.name", read_only=True, default="")

    class Meta:
        model = AmbulanceTrip
        fields = ["id", "hospital", "ambulance", "vehicle_number", "patient", "patient_name", "caller_name",
                  "caller_phone", "pickup", "destination", "crew", "status", "requested_at", "dispatched_at",
                  "completed_at"]
        read_only_fields = ["ambulance", "crew", "status", "requested_at", "dispatched_at", "completed_at"]


class MortuaryRecordSerializer(_Base):
    release_authorised_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MortuaryRecord
        fields = ["id", "hospital", "patient", "deceased_name", "time_of_death", "certified_cause", "storage_unit",
                  "police_case", "police_reference", "status", "received_at", "released_at", "released_to_name",
                  "released_to_relation", "released_to_id_last4", "release_authorised_by",
                  "release_authorised_by_name"]
        read_only_fields = ["status", "received_at", "released_at", "released_to_name", "released_to_relation",
                            "released_to_id_last4", "release_authorised_by"]

    def get_release_authorised_by_name(self, obj) -> str:
        return _name(obj.release_authorised_by)


class SterileSetSerializer(_Base):
    class Meta:
        model = SterileSet
        fields = ["id", "hospital", "name", "code"]
        # Uniqueness per hospital is the database constraint; the hospital is set server-side.
        validators = []


class SterilizationCycleSerializer(_Base):
    set_name = serializers.CharField(source="sterile_set.name", read_only=True)
    set_code = serializers.CharField(source="sterile_set.code", read_only=True)
    issued_to_name = serializers.CharField(source="issued_to.name", read_only=True, default="")

    class Meta:
        model = SterilizationCycle
        fields = ["id", "hospital", "sterile_set", "set_name", "set_code", "method", "load_number", "sterilized_at",
                  "expires_at", "indicator_passed", "status", "issued_to", "issued_to_name", "issued_at", "returned_at"]
        read_only_fields = ["status", "issued_to", "issued_at", "returned_at"]

    def validate(self, attrs):
        if attrs["expires_at"] <= attrs["sterilized_at"]:
            raise serializers.ValidationError({"expires_at": "Sterility must expire after the cycle."})
        return attrs


class LaundryBatchSerializer(_Base):
    department_name = serializers.CharField(source="department.name", read_only=True)
    shortfall = serializers.IntegerField(read_only=True)

    class Meta:
        model = LaundryBatch
        fields = ["id", "hospital", "department", "department_name", "item_type", "quantity_sent",
                  "quantity_returned", "shortfall", "status", "sent_at", "returned_at", "note"]
        read_only_fields = ["quantity_returned", "status", "sent_at", "returned_at"]
        extra_kwargs = {"quantity_sent": {"min_value": 1}}


class LeaveRequestSerializer(_Base):
    staff_name = serializers.SerializerMethodField()
    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = ["id", "hospital", "staff", "staff_name", "kind", "start_date", "end_date", "reason", "status",
                  "decided_by", "decided_by_name", "decided_at", "decision_note", "created_at"]
        read_only_fields = ["staff", "status", "decided_by", "decided_at", "decision_note", "created_at"]

    def get_staff_name(self, obj) -> str:
        return _name(obj.staff)

    def get_decided_by_name(self, obj) -> str:
        return _name(obj.decided_by)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "Leave must end on or after its first day."})
        return attrs


class PatientFeedbackSerializer(_Base):
    patient_name = serializers.CharField(source="patient.name", read_only=True, default="")
    department_name = serializers.CharField(source="department.name", read_only=True, default="")

    class Meta:
        model = PatientFeedback
        fields = ["id", "hospital", "patient", "patient_name", "department", "department_name", "rating", "category",
                  "comments", "status", "response", "created_at"]
        read_only_fields = ["status", "response", "created_at"]
        extra_kwargs = {"rating": {"min_value": 1, "max_value": 5}}


class TextTemplateSerializer(_Base):
    class Meta:
        model = TextTemplate
        fields = ["id", "hospital", "name", "kind", "body", "is_active", "updated_at"]
        read_only_fields = ["updated_at"]
        validators = []
