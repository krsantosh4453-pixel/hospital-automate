from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.conf import settings
from users.models import StaffProfile, StaffHospitalMembership, StaffRole

HOSPITAL_HEADER = "HTTP_X_HOSPITAL_ID"
_UNSET = object()


def parse_hospital_id(value):
    """Return an int hospital id, or raise a 400 for malformed input."""
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    if hasattr(value, "pk"):
        return value.pk
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError({"hospital": "Hospital must be a numeric id."})


def get_request_hospital_id(request, view=None):
    """
    The hospital the request is acting in, from (in order) the ``hospital``
    query parameter, the ``hospital`` body field, a ``hospital_pk`` /
    ``hospital_id`` URL kwarg, or the ``X-Hospital-ID`` header that the
    frontend sends for the selected hospital. None when no context is given.
    """
    cached = getattr(request, "_hms_hospital_id", _UNSET)
    if cached is not _UNSET:
        return cached
    value = None
    query = getattr(request, "query_params", None) or getattr(request, "GET", {})
    value = query.get("hospital") if hasattr(query, "get") else None
    if value in (None, ""):
        data = getattr(request, "data", None)
        if hasattr(data, "get"):
            value = data.get("hospital")
            if isinstance(value, list):
                value = value[0] if value else None
    if value in (None, "") and view is not None:
        kwargs = getattr(view, "kwargs", {}) or {}
        value = kwargs.get("hospital_pk") or kwargs.get("hospital_id")
    if value in (None, ""):
        meta = getattr(request, "META", {})
        value = meta.get(HOSPITAL_HEADER)
    hospital_id = parse_hospital_id(value)
    try:
        request._hms_hospital_id = hospital_id
    except AttributeError:
        pass
    return hospital_id


class IsHL7Authenticated(permissions.BasePermission):
    """
    Permission class for HL7 endpoints.
    Allows access if:
    - Request comes from whitelisted IP (HL7_IP_WHITELIST setting)
    - Request includes valid API key in header (HL7_API_KEY setting)
    """

    def has_permission(self, request, view):
        # Check IP whitelist
        client_ip = self._get_client_ip(request)
        whitelist = getattr(settings, 'HL7_IP_WHITELIST', [])
        if whitelist and client_ip in whitelist:
            return True

        # Check API key
        api_key = request.headers.get('X-HL7-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        expected_key = getattr(settings, 'HL7_API_KEY', None)
        if expected_key and api_key == expected_key:
            return True

        # In development, allow if DEBUG=True
        if getattr(settings, 'DEBUG', False):
            return True

        return False

    def _get_client_ip(self, request):
        from config.client_ip import client_ip

        return client_ip(request) or 'unknown'


def get_user_staff_profile(user):
    """Get the staff profile for a user, or None if not staff."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.staff_profile
    except StaffProfile.DoesNotExist:
        return None


def get_user_active_hospital_memberships(user):
    """Get active hospital memberships for a staff user."""
    staff_profile = get_user_staff_profile(user)
    if not staff_profile:
        return StaffHospitalMembership.objects.none()

    return StaffHospitalMembership.objects.filter(
        staff=staff_profile,
        is_active=True
    ).select_related("hospital", "department")


def get_user_hospital_ids(user):
    """Get list of active hospital IDs the user has active membership in."""
    memberships = get_user_active_hospital_memberships(user).filter(hospital__is_active=True)
    return list(memberships.values_list("hospital_id", flat=True))


def get_user_roles(user, hospital_id=None):
    """
    Roles the user holds. With ``hospital_id`` only the role of the active
    membership in that hospital counts, so an Admin of Hospital A who is a
    Receptionist in Hospital B is only a Receptionist when acting in B.
    Without a hospital, the roles of all active memberships are returned.
    The StaffProfile role is a display default and grants nothing by itself.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return []
    staff_profile = get_user_staff_profile(user)
    if not staff_profile or not staff_profile.is_active_staff:
        return []

    memberships = get_user_active_hospital_memberships(user)
    if hospital_id is not None:
        memberships = memberships.filter(hospital_id=hospital_id, hospital__is_active=True)
    roles = []
    for membership in memberships:
        if membership.role not in roles:
            roles.append(membership.role)
    return roles


def user_has_role(user, role_name):
    """Check if user has a specific role."""
    return role_name in get_user_roles(user)


def user_has_hospital_access(user, hospital_id):
    """Check if user has active membership in a specific hospital."""
    try:
        hospital_id = parse_hospital_id(hospital_id)
    except ValidationError:
        return False
    return hospital_id in get_user_hospital_ids(user)


def user_has_any_role(user, role_names):
    """Check if user has any of the given roles."""
    user_roles = get_user_roles(user)
    return any(role in user_roles for role in role_names)


def get_linked_patient(user):
    """Return the Patient row linked to this login, if any."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.patient_account
    except Exception:
        return None


def is_active_staff(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    staff_profile = get_user_staff_profile(user)
    return bool(staff_profile and staff_profile.is_active_staff)


class IsStaffUser(permissions.BasePermission):
    """
    Permission class to check if user is an authenticated staff member.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and get_user_staff_profile(request.user) is not None
            and get_user_staff_profile(request.user).is_active_staff
        )


class IsHospitalMember(permissions.BasePermission):
    """
    Permission class to check if user is a member of the requested hospital.
    The hospital_id can be passed via:
    - query_params['hospital']
    - request.data['hospital']
    - view.kwargs['hospital_pk'] or view.kwargs['hospital_id']
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        staff_profile = get_user_staff_profile(request.user)
        if not staff_profile or not staff_profile.is_active_staff:
            return False

        # Try to get hospital_id from various sources
        hospital_id = self._get_hospital_id(request, view)

        if hospital_id is None:
            # If no hospital context provided, allow if user has any hospital membership
            return get_user_active_hospital_memberships(request.user).exists()

        return user_has_hospital_access(request.user, hospital_id)

    def _get_hospital_id(self, request, view):
        return get_request_hospital_id(request, view)


class RoleBasedPermission(permissions.BasePermission):
    """
    Base class for role-based permissions.
    """

    required_roles = []
    require_hospital_membership = True

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        staff_profile = get_user_staff_profile(request.user)
        if not staff_profile or not staff_profile.is_active_staff:
            return False

        hospital_id = self._get_hospital_id(request, view)

        # Check hospital membership if required
        if self.require_hospital_membership and hospital_id is not None:
            if not user_has_hospital_access(request.user, hospital_id):
                return False

        # Check the role held in the hospital being acted in
        user_roles = get_user_roles(request.user, hospital_id)
        return any(role in user_roles for role in self.required_roles)

    def has_object_permission(self, request, view, obj):
        """The role must be held in the hospital that owns the object."""
        resolver = getattr(view, "get_object_hospital_id", None)
        if resolver is None:
            return True
        hospital_id = resolver(obj)
        if hospital_id is None:
            return True
        user_roles = get_user_roles(request.user, hospital_id)
        return any(role in user_roles for role in self.required_roles)

    def _get_hospital_id(self, request, view):
        return get_request_hospital_id(request, view)


class IsAdmin(RoleBasedPermission):
    """Admin: Full access to hospital administration."""
    required_roles = [StaffRole.ADMIN]


class IsDoctor(RoleBasedPermission):
    """Doctor: Clinical workflows, consultations, prescriptions."""
    required_roles = [StaffRole.DOCTOR, StaffRole.ADMIN]


class IsNurse(RoleBasedPermission):
    """Nurse: Nursing/vitals/MAR workflows."""
    required_roles = [StaffRole.NURSE, StaffRole.ADMIN]


class IsReceptionist(RoleBasedPermission):
    """Reception: Patient registration, appointments, queue, basic billing."""
    required_roles = [StaffRole.RECEPTIONIST, StaffRole.ADMIN]


class IsPharmacist(RoleBasedPermission):
    """Pharmacist: Medicine, stock, sales/dispensing."""
    required_roles = [StaffRole.PHARMACIST, StaffRole.ADMIN]


class IsLabStaff(RoleBasedPermission):
    """Lab Staff: Laboratory tests and results."""
    required_roles = [StaffRole.LAB_STAFF, StaffRole.ADMIN]


class IsBillingStaff(RoleBasedPermission):
    """Billing Staff: Invoices, payments, insurance/financial workflows."""
    required_roles = [StaffRole.BILLING_STAFF, StaffRole.ADMIN]


class IsInventoryStaff(RoleBasedPermission):
    """Inventory/Procurement Staff: Procurement, stock management."""
    required_roles = [StaffRole.INVENTORY_STAFF, StaffRole.ADMIN]


class IsBloodBankStaff(RoleBasedPermission):
    """Blood Bank Staff: Blood inventory, requests, transactions."""
    required_roles = [StaffRole.BLOOD_BANK_STAFF, StaffRole.ADMIN]


class IsHospitalManager(RoleBasedPermission):
    """Hospital Manager: Hospital-level administration."""
    required_roles = [StaffRole.HOSPITAL_MANAGER, StaffRole.ADMIN]


class IsCompounder(RoleBasedPermission):
    """Compounder: Medicine preparation and dispensing."""
    required_roles = [StaffRole.COMPOUNDER, StaffRole.PHARMACIST, StaffRole.ADMIN]


class IsClinicalStaff(RoleBasedPermission):
    """Clinical staff: Doctors and Nurses."""
    required_roles = [StaffRole.DOCTOR, StaffRole.NURSE, StaffRole.ADMIN]


class IsAdminOrManager(RoleBasedPermission):
    """Admin or Hospital Manager."""
    required_roles = [StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER]


def read_only(permission_class):
    """``permission_class`` granted for reading (safe methods) only."""

    class ReadOnly(permission_class):
        def has_permission(self, request, view):
            return request.method in permissions.SAFE_METHODS and super().has_permission(request, view)

        def has_object_permission(self, request, view, obj):
            return request.method in permissions.SAFE_METHODS and super().has_object_permission(request, view, obj)

    ReadOnly.__name__ = ReadOnly.__qualname__ = f"{permission_class.__name__}ReadOnly"
    return ReadOnly


IsNurseReadOnly = read_only(IsNurse)
IsReceptionistReadOnly = read_only(IsReceptionist)
IsCompounderReadOnly = read_only(IsCompounder)
# A Hospital Manager oversees clinical work without changing it.
IsHospitalManagerReadOnly = read_only(IsHospitalManager)


# Object-level permissions

class IsOwnerOrHospitalAdmin(permissions.BasePermission):
    """
    Object-level permission: Allow access if user is the owner of the object
    or has Admin/HospitalManager role in the same hospital.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        staff_profile = get_user_staff_profile(request.user)
        if not staff_profile or not staff_profile.is_active_staff:
            return False

        # Check if user is the owner (e.g., obj.doctor == user or obj.created_by == user)
        if hasattr(obj, "doctor") and obj.doctor:
            if hasattr(obj.doctor, "user") and obj.doctor.user == request.user:
                return True
            if obj.doctor == request.user:
                return True

        if hasattr(obj, "created_by") and obj.created_by == request.user:
            return True

        if hasattr(obj, "user") and obj.user == request.user:
            return True

        # Check if user has admin/manager role in the object's hospital
        hospital = self._get_object_hospital(obj)
        if hospital:
            # The role must be held in the object's hospital, not in any hospital.
            user_roles = get_user_roles(request.user, hospital.id)
            if StaffRole.ADMIN in user_roles or StaffRole.HOSPITAL_MANAGER in user_roles:
                return True

        return False

    def _get_object_hospital(self, obj):
        """Extract hospital from various object types."""
        if hasattr(obj, "hospital"):
            return obj.hospital
        if hasattr(obj, "visit") and hasattr(obj.visit, "hospital"):
            return obj.visit.hospital
        if hasattr(obj, "patient"):
            # Try to get hospital from patient membership
            membership = obj.patient.hospital_memberships.filter(is_active=True).first()
            if membership:
                return membership.hospital
        return None


class IsPatientReadOnly(permissions.BasePermission):
    """
    A linked patient may read, and only read, records the queryset
    has already limited to their own patient id.
    """

    def has_permission(self, request, view):
        if request.method not in permissions.SAFE_METHODS:
            return False
        if is_active_staff(request.user):
            return False
        return get_linked_patient(request.user) is not None


class IsLinkedPatient(permissions.BasePermission):
    """A non-staff account that is linked to exactly one patient."""

    def has_permission(self, request, view):
        if is_active_staff(request.user):
            return False
        return get_linked_patient(request.user) is not None


class IsHospitalScoped(permissions.BasePermission):
    """
    Object-level permission: Ensure object belongs to a hospital the user has access to.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        staff_profile = get_user_staff_profile(request.user)
        if not staff_profile or not staff_profile.is_active_staff:
            return False

        hospital = self._get_object_hospital(obj)
        if not hospital:
            # If object has no hospital, deny access
            return False

        return user_has_hospital_access(request.user, hospital.id)

    def _get_object_hospital(self, obj):
        """Extract hospital from various object types."""
        if hasattr(obj, "hospital"):
            return obj.hospital
        if hasattr(obj, "visit") and hasattr(obj.visit, "hospital"):
            return obj.visit.hospital
        if hasattr(obj, "patient"):
            membership = obj.patient.hospital_memberships.filter(is_active=True).first()
            if membership:
                return membership.hospital
        return None