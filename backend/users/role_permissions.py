"""
Hospital permission catalogue (Phase 3, decision P3-A): defined in code, never
in the database.

Who holds which role at which hospital is data (StaffHospitalMembership); what
a role may do is this table. It mirrors the web app's DEFAULT_ROLES
(src/assets/context/RoleContext.jsx); security_tests/test_tenant_context.py
fails if the two differ. A hospital can only narrow a role per module
(hospital.RoleModuleRestriction: view-only or off), never widen it, and the
Admin role cannot be narrowed. Platform permissions live apart, in
users/platform.py.

A permission is "<Module>.<Action>", e.g. "Patients.Add". Existing endpoints
keep their own permission classes; new endpoints use HasHospitalPermission.
"""

from rest_framework.permissions import BasePermission

from .models import StaffRole
from .permissions import get_request_hospital_id, get_user_roles, user_has_hospital_access

ALL_ACTIONS = frozenset({"View", "Add", "Edit", "Delete"})
ALL_MODULES = (
    "Dashboard", "Patients", "Appointments", "Queue", "Doctors", "Nurses", "Compounders", "Pharmacy",
    "Laboratory", "Billing", "Inventory", "Prescriptions", "Reports", "Emergency", "BloodBank", "IPD",
    "AIScribe", "Users", "Roles", "Hospitals", "Departments", "Permissions",
)


def _actions(*names):
    return frozenset(names)


V, VE, VA, VAE = _actions("View"), _actions("View", "Edit"), _actions("View", "Add"), _actions("View", "Add", "Edit")

ROLE_MODULE_ACTIONS = {
    StaffRole.ADMIN: {module: ALL_ACTIONS for module in ALL_MODULES},
    StaffRole.DOCTOR: {
        "Dashboard": V, "Patients": VE, "Appointments": VE, "Queue": V, "Doctors": V, "Prescriptions": VAE,
        "Laboratory": VA, "Reports": V, "IPD": VAE, "Emergency": VAE, "BloodBank": VA, "AIScribe": VAE,
    },
    StaffRole.NURSE: {
        "Dashboard": V, "Patients": VE, "Appointments": V, "Queue": VE, "Nurses": VE, "Prescriptions": V,
        "IPD": VE, "Reports": V, "Laboratory": VE, "Emergency": VAE, "BloodBank": V,
    },
    StaffRole.COMPOUNDER: {
        "Dashboard": V, "Compounders": VE, "Prescriptions": V, "Pharmacy": VAE, "Inventory": VE, "Reports": V,
    },
    StaffRole.RECEPTIONIST: {
        "Dashboard": V, "Patients": VAE, "Appointments": VAE, "Queue": VE, "Billing": VA, "Doctors": V,
        "Reports": V,
    },
    StaffRole.PHARMACIST: {
        "Dashboard": V, "Pharmacy": VAE, "Prescriptions": VE, "Compounders": V, "Inventory": VE, "Reports": V,
    },
    StaffRole.LAB_STAFF: {"Dashboard": V, "Laboratory": VAE, "Reports": V},
    StaffRole.BLOOD_BANK_STAFF: {"Dashboard": V, "BloodBank": VAE, "Reports": V},
    StaffRole.BILLING_STAFF: {"Dashboard": V, "Billing": VAE, "Reports": V},
    StaffRole.INVENTORY_STAFF: {"Dashboard": V, "Inventory": VAE, "Reports": V},
    StaffRole.HOSPITAL_MANAGER: {
        "Dashboard": V, "Patients": V, "Appointments": VAE, "Queue": V, "Doctors": VAE, "Nurses": VAE,
        "Compounders": V, "Pharmacy": VAE, "Laboratory": V, "Billing": VAE, "Inventory": VAE, "Reports": VAE,
        "Emergency": V, "BloodBank": VAE, "IPD": V, "Users": V, "Hospitals": V, "Departments": VAE,
    },
}

def permissions_for(user, hospital_id):
    """Every "<Module>.<Action>" the user holds at this hospital, after its restrictions."""
    from hospital.models import RoleModuleRestriction

    roles = get_user_roles(user, hospital_id)
    if not roles:
        return frozenset()
    restrictions = {}
    if StaffRole.ADMIN not in roles:
        for role, module, access in RoleModuleRestriction.objects.filter(
                hospital_id=hospital_id, role__in=roles).values_list("role", "module", "access"):
            restrictions[(role, module)] = access
    granted = set()
    for role in roles:
        for module, actions in ROLE_MODULE_ACTIONS.get(role, {}).items():
            access = restrictions.get((role, module))
            if access == RoleModuleRestriction.NONE:
                continue
            allowed = actions & {"View"} if access == RoleModuleRestriction.VIEW else actions
            granted.update(f"{module}.{action}" for action in allowed)
    return frozenset(granted)


def restricted_modules(user, hospital_id):
    """``{module: "view" | "none"}`` for the user's roles at this hospital (Admin: none)."""
    from hospital.models import RoleModuleRestriction

    roles = get_user_roles(user, hospital_id)
    if not roles or StaffRole.ADMIN in roles:
        return {}
    rows = RoleModuleRestriction.objects.filter(hospital_id=hospital_id, role__in=roles)
    return {module: access for module, access in rows.values_list("module", "access")}


def HasHospitalPermission(permission):  # noqa: N802 - used like a permission class
    """Permission class: the acting hospital (X-Hospital-ID etc.) grants ``permission`` to the user."""

    class _HasHospitalPermission(BasePermission):
        def has_permission(self, request, view):
            hospital_id = get_request_hospital_id(request, view)
            if hospital_id is None or not user_has_hospital_access(request.user, hospital_id):
                return False
            return permission in permissions_for(request.user, hospital_id)

    _HasHospitalPermission.__name__ = f"HasHospitalPermission[{permission}]"
    return _HasHospitalPermission
