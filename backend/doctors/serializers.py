from rest_framework import serializers
from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = [
            "id",
            "hospital",
            "name",
            "specialization",
            "email",
            "phone",
            "department",
            "experience",
            "availability",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_hospital(self, value):
        user = self.context["request"].user
        from users.permissions import get_user_hospital_ids
        hospital_ids = get_user_hospital_ids(user)
        if value.id not in hospital_ids:
            raise serializers.ValidationError("You can only create doctors in your authorized hospitals.")
        return value