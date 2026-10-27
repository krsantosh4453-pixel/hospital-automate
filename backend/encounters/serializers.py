from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Visit, QueueToken, DoctorSchedule


def _patient_belongs_to_hospital(patient, hospital):
    """
    A patient counts as "belonging" to a hospital either via the legacy
    PatientHospital membership OR the direct Patient.hospital foreign key
    added by the Patients module. Both are honoured so the queue flow works
    with the way patients are actually created today.

    (This mirrors the fix applied to the Appointment serializer in the
    Appointments module so the two modules stay consistent.)
    """
    if not (patient and hospital):
        return True

    has_membership = patient.hospital_memberships.filter(
        hospital=hospital,
        is_active=True
    ).exists()

    has_direct_link = (
        getattr(patient, "hospital_id", None) == hospital.id
    )

    return has_membership or has_direct_link


def next_token_number(hospital_id, token_date=None):
    """
    Return the next token number for a hospital on a given day.

    The token sequence is scoped per hospital per calendar day. We read the
    current maximum and add one; the database level
    UniqueConstraint(hospital, token_date, token_number) is the final guard
    against duplicates created by concurrent requests.
    """
    token_date = token_date or timezone.localdate()

    current_max = (
        QueueToken.objects
        .filter(hospital_id=hospital_id, token_date=token_date)
        .aggregate(max_token=serializers.models.Max("token_number"))
        .get("max_token")
    )

    return (current_max or 0) + 1


class VisitSerializer(serializers.ModelSerializer):
    # Read-only display helpers so the flat React queue table can show the
    # patient/doctor name without extra round trips.
    patient_name = serializers.CharField(
        source="patient.name",
        read_only=True
    )
    doctor_name = serializers.CharField(
        source="doctor.name",
        read_only=True
    )
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )

    class Meta:
        model = Visit
        fields = [
            "id",
            "patient",
            "doctor",
            "hospital",
            "visit_type",
            "chief_complaint",
            "status",
            "visit_date",
            "patient_name",
            "doctor_name",
            "hospital_name",
        ]
        read_only_fields = ["id", "visit_date"]

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
            from hospital.models import Hospital
            try:
                hospital = Hospital.objects.get(pk=hospital_id)
            except Hospital.DoesNotExist:
                raise serializers.ValidationError({
                    "hospital": "Invalid hospital."
                })
            if not _patient_belongs_to_hospital(value, hospital):
                raise serializers.ValidationError(
                    "This patient is not registered in this hospital."
                )
        return value

    def validate(self, attrs):
        hospital = attrs.get("hospital")
        patient = attrs.get("patient")
        doctor = attrs.get("doctor")

        # Patient must belong to the selected hospital
        if hospital and patient:
            if not _patient_belongs_to_hospital(patient, hospital):
                raise serializers.ValidationError({
                    "patient": "This patient is not registered in this hospital."
                })

        # Doctor must belong to the selected hospital
        if hospital and doctor:
            if doctor.hospital_id != hospital.id:
                raise serializers.ValidationError({
                    "doctor": "This doctor does not belong to this hospital."
                })

        return attrs

    def create(self, validated_data):
        # Set hospital from context if not provided
        if "hospital" not in validated_data:
            scoped_hospital = self.context.get("scoped_hospital")
            if scoped_hospital:
                validated_data["hospital"] = scoped_hospital
        return super().create(validated_data)


class QueueTokenSerializer(serializers.ModelSerializer):
    # ------------------------------------------------------------------
    # Read-only display helpers.
    # The React queue table is flat and shows patient/doctor/type as plain
    # values. These expose the related object's data so the existing UI
    # columns keep working without changing the model relationships.
    # read_only=True => they never participate in validation or writes.
    # ------------------------------------------------------------------
    patient_name = serializers.CharField(
        source="patient.name",
        read_only=True
    )
    patient_phone = serializers.CharField(
        source="patient.phone",
        read_only=True
    )
    doctor_name = serializers.CharField(
        source="doctor.name",
        read_only=True
    )
    department = serializers.CharField(
        source="doctor.specialization",
        read_only=True
    )
    visit_type = serializers.CharField(
        source="visit.visit_type",
        read_only=True
    )
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )
    # Derived "waiting" figure used by the queue UI. Only meaningful while
    # the token is still waiting; otherwise it reports 0.
    waiting_minutes = serializers.SerializerMethodField()

    # Queue estimation fields
    queue_position = serializers.IntegerField(read_only=True)
    estimated_start_time = serializers.DateTimeField(read_only=True)
    last_updated = serializers.DateTimeField(read_only=True)

    # Timestamp fields
    called_at = serializers.DateTimeField(read_only=True)
    acknowledged_at = serializers.DateTimeField(read_only=True)
    ready_at = serializers.DateTimeField(read_only=True)
    consultation_started_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)

    # The token number is normally assigned server-side (see create()),
    # so the client is not required to send one.
    token_number = serializers.IntegerField(required=False)
    token_date = serializers.DateField(required=False)

    class Meta:
        model = QueueToken
        fields = [
            "id",
            "visit",
            "appointment",
            "hospital",
            "patient",
            "doctor",
            "token_number",
            "token_date",
            "status",
            "estimated_wait_minutes",
            "queue_position",
            "estimated_start_time",
            "last_updated",
            "acknowledged_at",
            "called_at",
            "ready_at",
            "consultation_started_at",
            "completed_at",
            "created_at",
            "patient_name",
            "patient_phone",
            "doctor_name",
            "department",
            "visit_type",
            "hospital_name",
            "waiting_minutes",
        ]
        read_only_fields = ["id", "created_at", "last_updated"]
        # The model's UniqueConstraint on (hospital, token_date, token_number)
        # makes DRF auto-generate a UniqueTogetherValidator. We intentionally
        # remove it: token_number is allocated server-side in create(), so the
        # auto validator would wrongly require the client to send it (and then
        # re-run its own uniqueness query). Uniqueness is enforced atomically
        # by the DB constraint plus the retry loop in create() instead.
        validators = []

    def get_waiting_minutes(self, obj):
        if obj.status and obj.status != QueueToken.Status.WAITING:
            return 0

        if not obj.created_at:
            return 0

        delta = timezone.now() - obj.created_at
        return max(0, int(delta.total_seconds() // 60))

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

    def validate(self, attrs):
        # On updates Django passes the existing instance fields, so fall
        # back to the instance value when a field is absent from the payload.
        instance = getattr(self, "instance", None)

        def current(field):
            if field in attrs:
                return attrs.get(field)
            return getattr(instance, field, None) if instance else None

        visit = current("visit")
        hospital = current("hospital")
        patient = current("patient")
        doctor = current("doctor")

        # Visit must belong to the same hospital
        if visit and hospital:
            if visit.hospital_id != hospital.id:
                raise serializers.ValidationError({
                    "hospital": "This visit does not belong to this hospital."
                })

        # Patient must belong to the hospital
        if hospital and patient:
            if not _patient_belongs_to_hospital(patient, hospital):
                raise serializers.ValidationError({
                    "patient": "This patient is not registered in this hospital."
                })

        # Doctor must belong to the hospital
        if hospital and doctor:
            if doctor.hospital_id != hospital.id:
                raise serializers.ValidationError({
                    "doctor": "This doctor does not belong to this hospital."
                })

        # Patient/doctor should match the Visit
        if visit and patient:
            if visit.patient_id != patient.id:
                raise serializers.ValidationError({
                    "patient": "Patient does not match the selected visit."
                })

        if visit and doctor:
            if visit.doctor_id != doctor.id:
                raise serializers.ValidationError({
                    "doctor": "Doctor does not match the selected visit."
                })

        return attrs

    def create(self, validated_data):
        """
        Persist the token. When the caller does not supply a token_number we
        generate the next number server-side, scoped per hospital per day.
        A short retry loop plus the database UniqueConstraint protects
        against concurrent requests racing for the same number.
        """
        hospital = validated_data.get("hospital")
        token_date = validated_data.get("token_date") or timezone.localdate()
        validated_data["token_date"] = token_date

        if not validated_data.get("token_number"):
            for _ in range(5):
                validated_data["token_number"] = next_token_number(
                    hospital.id,
                    token_date
                )
                try:
                    # Inner atomic creates a savepoint so an IntegrityError
                    # (e.g. a concurrent request grabbed the number first)
                    # only rolls back this attempt, not the whole request.
                    with transaction.atomic():
                        return super().create(validated_data)
                except IntegrityError:
                    continue

            raise serializers.ValidationError({
                "token_number": (
                    "Could not allocate a unique token number. "
                    "Please try again."
                )
            })

        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                "token_number": (
                    "A token with this number already exists for this "
                    "hospital today."
                )
            })


class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor",
            "day",
            "start_time",
            "end_time",
            "is_available",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        doctor = attrs.get("doctor")

        if doctor and not doctor.hospital_id:
            raise serializers.ValidationError({
                "doctor": "Doctor must belong to a hospital."
            })

        return attrs
