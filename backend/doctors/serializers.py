from rest_framework import serializers
from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = [
            "id",
            "hospital",
            "user",
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

    def validate(self, attrs):
        """A linked login must be an active Doctor member of the same hospital."""
        attrs = super().validate(attrs)
        user = attrs.get("user", getattr(self.instance, "user", None))
        hospital = attrs.get("hospital", getattr(self.instance, "hospital", None))
        if user is not None:
            from users.models import StaffHospitalMembership, StaffRole
            if hospital is None or not StaffHospitalMembership.objects.filter(
                staff__user=user, hospital=hospital, role=StaffRole.DOCTOR, is_active=True
            ).exists():
                raise serializers.ValidationError(
                    {"user": "The login must belong to an active Doctor of this hospital."}
                )
        return attrs
