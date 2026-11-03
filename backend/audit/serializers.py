from rest_framework import serializers
from .models import AuditLog, AIInteraction


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "username",
            "ip_address",
            "action",
            "model_name",
            "object_id",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AIInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInteraction
        fields = [
            "id",
            "patient",
            "input_text",
            "ai_output",
            "status",
            "reviewed_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]