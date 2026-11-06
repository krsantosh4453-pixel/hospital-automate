"""
Hospital-level narrowing of built-in roles (hospital.RoleModuleRestriction).

Each hospital-scoped API belongs to one module of the Permissions page, from
the view's ``access_module`` or its model's app. A restriction for the
caller's role in an acting hospital turns that module into read-only
("view") or off ("none") for them. It never adds access, and the Admin role
is never restricted, so an administrator cannot lock everyone out.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS

from users.models import StaffRole
from users.permissions import get_user_roles

# App label -> module name used by the frontend (RoleContext.ALL_MODULES).
APP_MODULES = {
    "patients": "Patients", "appointments": "Appointments", "encounters": "Queue", "doctors": "Doctors",
    "nurses": "Nurses", "compounder": "Compounders", "pharmacy": "Pharmacy", "laboratory": "Laboratory",
    "billing": "Billing", "procurement": "Inventory", "emergency": "Emergency", "bloodbank": "BloodBank",
    "ipd": "IPD", "ai_scribe": "AIScribe",
}
RESTRICTABLE_MODULES = sorted(set(APP_MODULES.values()) | {"Prescriptions"})
RESTRICTABLE_ROLES = sorted(role for role in StaffRole.values if role != StaffRole.ADMIN)


def module_of(view):
    explicit = getattr(view, "access_module", None)
    if explicit:
        return explicit
    queryset = getattr(view, "queryset", None)
    model = getattr(queryset, "model", None)
    return APP_MODULES.get(model._meta.app_label) if model is not None else None


def check_module_access(view, request, hospital_ids):
    """Raise PermissionDenied when a restriction in ``hospital_ids`` covers this request."""
    from hospital.models import RoleModuleRestriction

    module = module_of(view)
    if not module or not hospital_ids or not request.user.is_authenticated:
        return
    # One query in the usual case: no restriction for this module at these hospitals.
    rules_by_hospital = {}
    for hospital_id, role, access in RoleModuleRestriction.objects.filter(
            hospital_id__in=list(hospital_ids), module=module).values_list("hospital_id", "role", "access"):
        rules_by_hospital.setdefault(hospital_id, []).append((role, access))
    for hospital_id, hospital_rules in rules_by_hospital.items():
        roles = set(get_user_roles(request.user, hospital_id))
        if StaffRole.ADMIN in roles:
            continue
        rules = {access for role, access in hospital_rules if role in roles}
        if RoleModuleRestriction.NONE in rules:
            raise PermissionDenied(f"{module} is turned off for your role at this hospital.")
        if RoleModuleRestriction.VIEW in rules and request.method not in SAFE_METHODS:
            raise PermissionDenied(f"{module} is view-only for your role at this hospital.")


class ModuleAccessMixin:
    """Applies check_module_access after authentication and permission checks."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        check_module_access(self, request, self.get_acting_hospital_ids())
