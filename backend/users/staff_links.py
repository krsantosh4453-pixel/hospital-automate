"""
Linking a Doctor or Nurse profile to the staff login it belongs to.

The care scope shows a Doctor or Nurse only their own patients, which needs
the profile linked to their login. A profile is linked explicitly through its
``user`` field, or by the login's email when exactly one active login of the
hospital with that role has it and no profile there yet.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.models import StaffHospitalMembership


def _login_by_email(email, hospital, role, profiles_related_name):
    if not email:
        return None
    candidates = list(
        get_user_model().objects.filter(
            email__iexact=email,
            is_active=True,
            staff_profile__hospital_memberships__hospital=hospital,
            staff_profile__hospital_memberships__role=role,
            staff_profile__hospital_memberships__is_active=True,
        ).exclude(**{f"{profiles_related_name}__hospital": hospital}).distinct()[:2]
    )
    return candidates[0] if len(candidates) == 1 else None


def link_profile_login(attrs, instance, role, profiles_related_name):
    """
    Validate (or fill in by email) the ``user`` of a profile being saved.
    Returns ``attrs``; raises a ValidationError when the login given does not
    belong to an active member of the profile's hospital with ``role``.
    """
    user = attrs.get("user", getattr(instance, "user", None))
    hospital = attrs.get("hospital", getattr(instance, "hospital", None))
    if user is None and hospital is not None:
        email = attrs.get("email", getattr(instance, "email", ""))
        user = _login_by_email(email, hospital, role, profiles_related_name)
        if user is not None:
            attrs["user"] = user
    if user is not None and (
        hospital is None
        or not StaffHospitalMembership.objects.filter(
            staff__user=user, hospital=hospital, role=role, is_active=True
        ).exists()
    ):
        raise serializers.ValidationError(
            {"user": f"The login must belong to an active {role} of this hospital."}
        )
    return attrs
