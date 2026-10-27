from rest_framework import serializers
from hospital.models import Hospital
from .models import (
    BloodInventory,
    BloodRequest,
    BloodTransaction,
)


class BloodInventorySerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)

    class Meta:
        model = BloodInventory
        fields = [
            "id",
            "hospital",
            "blood_group",
            "component",
            "units",
            "expiry_date",
            "hospital_name",
        ]
        read_only_fields = ["id", "hospital_name"]


class BloodRequestSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.user.get_full_name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.user.get_full_name", read_only=True)

    hospital = serializers.PrimaryKeyRelatedField(
        queryset=Hospital.objects.none(), required=False, allow_null=True
    )

    class Meta:
        model = BloodRequest
        fields = [
            "id",
            "hospital",
            "patient",
            "blood_group",
            "component",
            "units",
            "status",
            "requested_by",
            "approved_by",
            "created_at",
            "updated_at",
            "hospital_name",
            "patient_name",
            "requested_by_name",
            "approved_by_name",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "hospital_name",
            "patient_name",
            "requested_by_name",
            "approved_by_name",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set hospital queryset based on user permissions
        request = self.context.get("request")
        if request:
            from users.permissions import get_user_hospital_ids
            user_hospital_ids = get_user_hospital_ids(request.user)
            self.fields["hospital"].queryset = Hospital.objects.filter(id__in=user_hospital_ids)

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

    def create(self, validated_data):
        # Set hospital from context if not provided
        if "hospital" not in validated_data:
            scoped_hospital = self.context.get("scoped_hospital")
            if scoped_hospital:
                validated_data["hospital"] = scoped_hospital
        # Set requested_by from user if available
        request = self.context.get("request")
        if request:
            # Try to get the Doctor associated with this user by email
            from doctors.models import Doctor
            doctor = Doctor.objects.filter(
                email=request.user.email,
                hospital=validated_data.get("hospital")
            ).first()
            if doctor:
                validated_data["requested_by"] = doctor
        return super().create(validated_data)


class BloodTransactionSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    request_patient_name = serializers.CharField(source="request.patient.name", read_only=True)
    inventory_display = serializers.CharField(source="inventory.__str__", read_only=True)
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True)

    class Meta:
        model = BloodTransaction
        fields = [
            "id",
            "hospital",
            "request",
            "inventory",
            "transaction_type",
            "units",
            "performed_by",
            "created_at",
            "remarks",
            "hospital_name",
            "request_patient_name",
            "inventory_display",
            "performed_by_name",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "hospital_name",
            "request_patient_name",
            "inventory_display",
            "performed_by_name",
        ]