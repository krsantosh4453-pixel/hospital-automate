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
        if user is None and hospital is not None:
            # A Doctor sees only their own patients, which needs this profile
            # linked to their login: link it by the login's email.
            email = attrs.get("email", getattr(self.instance, "email", ""))
            user = self._doctor_login_by_email(email, hospital)
            if user is not None:
                attrs["user"] = user
        if user is not None:
            from users.models import StaffHospitalMembership, StaffRole
            if hospital is None or not StaffHospitalMembership.objects.filter(
                staff__user=user, hospital=hospital, role=StaffRole.DOCTOR, is_active=True
            ).exists():
                raise serializers.ValidationError(
                    {"user": "The login must belong to an active Doctor of this hospital."}
                )
        return attrs

    def _doctor_login_by_email(self, email, hospital):
        """The one active Doctor login of ``hospital`` with this email and no profile there yet."""
        if not email:
            return None
        from django.contrib.auth import get_user_model
        from users.models import StaffRole

        candidates = list(
            get_user_model().objects.filter(
                email__iexact=email,
                is_active=True,
                staff_profile__hospital_memberships__hospital=hospital,
                staff_profile__hospital_memberships__role=StaffRole.DOCTOR,
                staff_profile__hospital_memberships__is_active=True,
            ).exclude(doctor_profiles__hospital=hospital).distinct()[:2]
        )
        return candidates[0] if len(candidates) == 1 else None
