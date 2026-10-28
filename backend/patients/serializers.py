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
            "emergency_contact_name",
            "emergency_contact_relation",
            "emergency_contact_phone",
            "marital_status",
            "address_line",
            "city",
            "district",
            "state",
            "pincode",
            "id_type",
            "id_last4",
            "payer_type",
            "payer_name",
            "policy_number",
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

    def validate_pincode(self, value):
        value = (value or "").strip()
        if value and not (len(value) == 6 and value.isdigit()):
            raise serializers.ValidationError("A PIN code has 6 digits.")
        return value

    def validate_id_last4(self, value):
        value = (value or "").strip().upper()
        if value and not (len(value) == 4 and value.isalnum()):
            raise serializers.ValidationError("Enter only the last 4 characters of the ID.")
        return value

    def validate_date_of_birth(self, value):
        from config.hospital_time import hospital_today

        if value and value > hospital_today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate_emergency_contact_phone(self, value):
        if not value:
            return ""
        return self.validate_phone(value)

    def validate(self, attrs):
        # A contact without a number cannot be called. On a partial update
        # the stored value stands in for a field that was not sent.
        def current(field):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, "") if self.instance else ""

        if current("emergency_contact_name").strip() and not current("emergency_contact_phone"):
            raise serializers.ValidationError(
                {"emergency_contact_phone": "Add a phone number for the emergency contact."}
            )
        if current("id_last4") and not current("id_type"):
            raise serializers.ValidationError({"id_type": "Choose the type of ID."})
        if current("payer_type") in ("Insurance", "Government scheme", "Corporate") and not current("payer_name").strip():
            raise serializers.ValidationError({"payer_name": "Name the insurer, scheme or company."})
        return attrs

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
