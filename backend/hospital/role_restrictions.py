"""
/api/hospital/role-restrictions/: an administrator narrows a built-in role
for one module at their hospital (hospital.RoleModuleRestriction). Every
staff member can read them, so the screens hide what the server will refuse.
"""

from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from users.module_access import RESTRICTABLE_MODULES, RESTRICTABLE_ROLES
from users.permissions import IsAdmin, IsHospitalMember, IsStaffUser
from users.viewsets import HospitalScopedViewSet

from .models import RoleModuleRestriction


class RoleModuleRestrictionSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=RESTRICTABLE_ROLES)
    module = serializers.ChoiceField(choices=RESTRICTABLE_MODULES)

    class Meta:
        model = RoleModuleRestriction
        fields = ["id", "hospital", "role", "module", "access", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {"hospital": {"required": False}}
        validators = []


class RoleModuleRestrictionViewSet(HospitalScopedViewSet):
    queryset = RoleModuleRestriction.objects.all()
    serializer_class = RoleModuleRestrictionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if getattr(self, "action", None) in ("list", "retrieve"):
            return [IsAuthenticated(), IsStaffUser(), IsHospitalMember()]
        return [IsAdmin()]

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                super().perform_create(serializer)
        except IntegrityError:
            raise ValidationError("This role already has a restriction for that module; change it instead.")

    def perform_destroy(self, instance):
        # Removing a restriction gives the built-in access back; nothing clinical is lost.
        self._audit("delete", instance, details={"role": instance.role, "module": instance.module,
                                                 "access": instance.access})
        instance.delete()
