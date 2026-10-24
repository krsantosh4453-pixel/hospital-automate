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
            "address",
            "date_of_birth",
            "doctor",
            "condition",
            "hospital",
            "status",
            "email_verified",
            "phone_verified",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "email_verified", "phone_verified"]

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


class PatientHospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientHospital
        fields = [
            "id",
            "patient",
            "hospital",
            "uhid",
            "is_active",
            "joined_at",
        ]
        read_only_fields = ["id", "joined_at"]
