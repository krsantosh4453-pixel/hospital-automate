from rest_framework import serializers
from .models import (
    Notification,
    Consent,
    OTPVerification,
)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "hospital",
            "patient",
            "title",
            "message",
            "notification_type",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "hospital", "created_at"]

    def create(self, validated_data):
        if "hospital" not in validated_data:
            scoped_hospital = self.context.get("scoped_hospital")
            if scoped_hospital:
                validated_data["hospital"] = scoped_hospital
        return super().create(validated_data)


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        fields = [
            "id",
            "patient",
            "purpose",
            "granted",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class OTPVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPVerification
        fields = ["id", "phone", "email", "channel", "purpose", "is_verified", "attempts", "expires_at", "created_at"]
        read_only_fields = fields