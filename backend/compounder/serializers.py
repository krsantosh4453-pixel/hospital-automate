from rest_framework import serializers
from .models import Compounder


class CompounderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compounder
        fields = [
            "id",
            "hospital",
            "name",
            "phone",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

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