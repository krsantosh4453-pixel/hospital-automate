from rest_framework import serializers
from .models import Patient, PatientHospital


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "phone",
            "doctor",
            "condition",
            "hospital",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Patient name is required."
            )
        return value.strip()

    def validate_age(self, value):
        if value is None or value < 0 or value > 130:
            raise serializers.ValidationError(
                "Age must be between 0 and 130."
            )
        return value

    def validate_phone(self, value):
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        if len(digits) < 10:
            raise serializers.ValidationError(
                "Phone number must have at least 10 digits."
            )
        return digits


class PatientHospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientHospital
        fields = "__all__"
