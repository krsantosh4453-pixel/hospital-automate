"""
Platform (SaaS operator) permissions, kept apart from hospital roles (Phase 3).

Hospital roles live in StaffHospitalMembership and are checked per hospital
(users/permissions.py). Platform rights come only from an active PlatformStaff
row and never include patient, clinical or billing data: reading those needs
a hospital membership like anyone else. Every name here starts with
"platform." so it cannot be mistaken for a hospital permission.
"""

from django.db.models.signals import post_save
from rest_framework.permissions import BasePermission

from .models import PlatformStaff

PLATFORM_PERMISSIONS = {
    PlatformStaff.Role.ADMIN: frozenset({
        "platform.hospitals.view",
        "platform.hospitals.create",
        "platform.hospitals.edit",
        "platform.hospitals.delete",
        "platform.otp_log.view",
        "platform.report_templates.edit",
    }),
    PlatformStaff.Role.SUPPORT: frozenset({
        "platform.hospitals.view",
    }),
}


def platform_role(user):
    """The user's active platform role, or None."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    staff = PlatformStaff.objects.filter(user=user, is_active=True).values_list("role", flat=True).first()
    return staff


def has_platform_permission(user, permission):
    role = platform_role(user)
    return role is not None and permission in PLATFORM_PERMISSIONS.get(role, ())


def platform_permission(permission):
    """A DRF permission class granted by one platform permission, e.g. ``IsStaffUser | platform_permission(...)``."""

    class HasPlatformPermission(BasePermission):
        def has_permission(self, request, view):
            return has_platform_permission(request.user, permission)

    HasPlatformPermission.__name__ = f"HasPlatformPermission[{permission}]"
    return HasPlatformPermission


def _superusers_are_platform_admins(sender, instance, **kwargs):
    # Keeps `createsuperuser` and the Django admin working as before: a
    # superuser gets a platform-admin row. Taking the flag away later does not
    # remove the row; deactivate it in the admin to end platform access.
    if instance.is_superuser and instance.is_active:
        PlatformStaff.objects.get_or_create(user=instance, defaults={"role": PlatformStaff.Role.ADMIN})


def connect_signals():
    from django.contrib.auth import get_user_model

    post_save.connect(_superusers_are_platform_admins, sender=get_user_model(),
                      dispatch_uid="users.platform.superusers_are_platform_admins")
