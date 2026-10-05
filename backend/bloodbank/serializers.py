from rest_framework import serializers
from .models import (
    BloodInventory,
    BloodRequest,
    BloodTransaction,
)


class BloodInventorySerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)

    class Meta:
        model = BloodInventory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "hospital_name"]


class BloodRequestSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.user.get_full_name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.user.get_full_name", read_only=True)

    class Meta:
        model = BloodRequest
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "hospital_name",
            "patient_name",
            "requested_by_name",
            "approved_by_name",
        ]


class BloodTransactionSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    request_patient_name = serializers.CharField(source="request.patient.name", read_only=True)
    inventory_display = serializers.CharField(source="inventory.__str__", read_only=True)
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True)

    class Meta:
        model = BloodTransaction
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "hospital_name",
            "request_patient_name",
            "inventory_display",
            "performed_by_name",
        ]