from rest_framework import serializers
from .models import (
    Notification,
    Consent,
    OTPVerification,
)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consent
        fields = "__all__"


class OTPVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPVerification
        fields = ["id", "phone", "is_verified", "attempts", "expires_at", "created_at"]
        read_only_fields = fields