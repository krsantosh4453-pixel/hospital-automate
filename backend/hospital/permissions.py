from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_hospitals(user):
    """Get list of hospital IDs the user has active membership in."""
    if not user.is_authenticated:
        return []
    try:
        staff_profile = user.staff_profile
        if not staff_profile.is_active_staff:
            return []
        return list(
            staff_profile.hospital_memberships.filter(is_active=True).values_list(
                "hospital_id", flat=True
            )
        )
    except User.staff_profile.RelatedObjectDoesNotExist:
        return []


def get_user_roles_for_hospital(user, hospital_id):
    """Get list of roles the user has for a specific hospital."""
    if not user.is_authenticated:
        return []
    try:
        staff_profile = user.staff_profile
        if not staff_profile.is_active_staff:
            return []
        return list(
            staff_profile.hospital_memberships.filter(
                hospital_id=hospital_id, is_active=True
            ).values_list("role", flat=True)
        )
    except User.staff_profile.RelatedObjectDoesNotExist:
        return []


class IsStaffUser(permissions.BasePermission):
    """Permission class that requires user to have a StaffProfile."""

    message = "User must have a staff profile."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            profile = request.user.staff_profile
            return profile.is_active_staff
        except User.staff_profile.RelatedObjectDoesNotExist:
            return False


class HospitalIsolationPermission(permissions.BasePermission):
    """
    Object-level permission to enforce hospital isolation.
    
    Users can only access objects that belong to hospitals they are members of.
    Works with models that have a 'hospital' FK field.
    """

    message = "You do not have access to this hospital's data."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        user_hospitals = get_user_hospitals(request.user)
        if not user_hospitals:
            return False

        obj_hospital_id = self._get_object_hospital_id(obj)
        if obj_hospital_id is None:
            return True

        return obj_hospital_id in user_hospitals

    def _get_object_hospital_id(self, obj):
        if hasattr(obj, "hospital_id"):
            return obj.hospital_id
        if hasattr(obj, "hospital"):
            return obj.hospital_id
        return None


class RoleBasedPermission(permissions.BasePermission):
    """
    Role-based access control for hospital staff.
    
    Expected roles:
    - Admin: Full access to all hospital data
    - Doctor: Clinical data, prescriptions, admissions, discharges
    - Nurse: Vitals, assessments, MAR, nursing notes, patient care
    - Lab Staff: Lab tests, samples, results
    - Blood Bank Staff: Blood inventory, requests, transactions
    - Pharmacist: Pharmacy, prescriptions, dispensing
    - Receptionist: Patients, appointments, queue, billing
    - Billing Staff: Billing, invoices, payments
    - Inventory Staff: Inventory, procurement
    - Hospital Manager: Reports, analytics, staff management
    """

    ROLE_PERMISSIONS = {
        "Admin": ["*"],
        "Doctor": [
            "view_patient", "change_patient",
            "view_visit", "add_visit", "change_visit",
            "view_clinicalnote", "add_clinicalnote", "change_clinicalnote",
            "view_diagnosis", "add_diagnosis", "change_diagnosis",
            "view_prescription", "add_prescription", "change_prescription",
            "view_vitalsign", "add_vitalsign", "change_vitalsign",
            "view_serviceorder", "add_serviceorder", "change_serviceorder",
            "view_admission", "add_admission", "change_admission",
            "view_dischargeplan", "add_dischargeplan", "change_dischargeplan",
            "view_dischargesummary", "add_dischargesummary", "change_dischargesummary",
            "view_emergencyvisit", "add_emergencyvisit", "change_emergencyvisit",
            "view_labtest", "change_labtest",
            "view_bloodrequest", "add_bloodrequest", "change_bloodrequest",
        ],
        "Nurse": [
            "view_patient",
            "view_visit",
            "view_vitalsign", "add_vitalsign", "change_vitalsign",
            "view_clinicalnote", "add_clinicalnote",
            "view_nursingassessment", "add_nursingassessment", "change_nursingassessment",
            "view_nursingnote", "add_nursingnote", "change_nursingnote",
            "view_caretask", "add_caretask", "change_caretask",
            "view_mar", "add_mar", "change_mar",
            "view_admission",
            "view_dischargeplan",
            "view_bloodrequest",
        ],
        "Lab Staff": [
            "view_patient",
            "view_visit",
            "view_labtest", "add_labtest", "change_labtest",
            "view_samplecollection", "add_samplecollection", "change_samplecollection",
            "view_sampledispatch", "add_sampledispatch", "change_sampledispatch",
            "view_labresult", "add_labresult", "change_labresult",
            "view_resultverification", "add_resultverification", "change_resultverification",
        ],
        "Blood Bank Staff": [
            "view_patient",
            "view_bloodinventory", "add_bloodinventory", "change_bloodinventory",
            "view_bloodrequest", "add_bloodrequest", "change_bloodrequest",
            "view_bloodtransaction", "add_bloodtransaction", "change_bloodtransaction",
        ],
        "Pharmacist": [
            "view_patient",
            "view_visit",
            "view_prescription", "change_prescription",
            "view_medicine", "add_medicine", "change_medicine",
            "view_sale", "add_sale", "change_sale",
        ],
        "Receptionist": [
            "view_patient", "add_patient", "change_patient",
            "view_appointment", "add_appointment", "change_appointment",
            "view_queue", "add_queue", "change_queue",
            "view_visit", "add_visit",
            "view_invoice", "add_invoice", "change_invoice",
            "view_payment", "add_payment",
        ],
        "Billing Staff": [
            "view_patient",
            "view_invoice", "add_invoice", "change_invoice",
            "view_payment", "add_payment", "change_payment",
            "view_insuranceclaim", "add_insuranceclaim", "change_insuranceclaim",
        ],
        "Inventory Staff": [
            "view_medicine", "add_medicine", "change_medicine",
            "view_purchaseorder", "add_purchaseorder", "change_purchaseorder",
            "view_grn", "add_grn", "change_grn",
        ],
        "Hospital Manager": [
            "view_patient", "change_patient",
            "view_staffprofile", "add_staffprofile", "change_staffprofile",
            "view_reports",
        ],
    }

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request.user, "staff_profile") or not request.user.staff_profile.is_active_staff:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        user_hospitals = get_user_hospitals(request.user)
        if not user_hospitals:
            return False

        obj_hospital_id = self._get_object_hospital_id(obj)
        if obj_hospital_id is None:
            return True

        if obj_hospital_id not in user_hospitals:
            return False

        return True

    def _get_object_hospital_id(self, obj):
        if hasattr(obj, "hospital_id"):
            return obj.hospital_id
        if hasattr(obj, "hospital"):
            return obj.hospital_id
        return None

    def user_has_perm(self, user, hospital_id, perm_codename):
        """Check if user has a specific permission for a hospital."""
        if user.is_superuser:
            return True

        roles = get_user_roles_for_hospital(user, hospital_id)
        if not roles:
            return False

        for role in roles:
            allowed_perms = self.ROLE_PERMISSIONS.get(role, [])
            if "*" in allowed_perms or perm_codename in allowed_perms:
                return True

        return False


class IsHospitalMember(permissions.BasePermission):
    """
    Permission that requires user to be a member of the hospital
    specified in the request (via query param, URL, or object).
    """

    message = "You are not a member of this hospital."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        hospital_id = self._get_hospital_id_from_request(request)
        if hospital_id is None:
            return True

        user_hospitals = get_user_hospitals(request.user)
        return hospital_id in user_hospitals

    def _get_hospital_id_from_request(self, request):
        hospital_id = request.query_params.get("hospital")
        if hospital_id:
            try:
                return int(hospital_id)
            except (ValueError, TypeError):
                return None

        if hasattr(view, "get_object"):
            try:
                obj = view.get_object()
                if hasattr(obj, "hospital_id"):
                    return obj.hospital_id
                if hasattr(obj, "hospital"):
                    return obj.hospital_id
            except Exception:
                pass

        return None


class IsOwnerOrHospitalAdmin(permissions.BasePermission):
    """
    Object-level permission:
    - Owner (creator) of the object can access
    - Hospital Admin can access
    - Other hospital members can only view (if safe method)
    """

    message = "You do not have permission to perform this action."

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        user_hospitals = get_user_hospitals(request.user)
        obj_hospital_id = self._get_object_hospital_id(obj)

        if obj_hospital_id and obj_hospital_id not in user_hospitals:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if self._is_owner(request.user, obj):
            return True

        if self._is_hospital_admin(request.user, obj_hospital_id):
            return True

        return False

    def _get_object_hospital_id(self, obj):
        if hasattr(obj, "hospital_id"):
            return obj.hospital_id
        if hasattr(obj, "hospital"):
            return obj.hospital_id
        return None

    def _is_owner(self, user, obj):
        if hasattr(obj, "created_by") and obj.created_by == user:
            return True
        if hasattr(obj, "doctor") and hasattr(obj.doctor, "user") and obj.doctor.user == user:
            return True
        if hasattr(obj, "nurse") and hasattr(obj.nurse, "user") and obj.nurse.user == user:
            return True
        return False

    def _is_hospital_admin(self, user, hospital_id):
        if not hospital_id:
            return False
        roles = get_user_roles_for_hospital(user, hospital_id)
        return "Admin" in roles or "Hospital Manager" in roles


class ReadOnlyOrHospitalAdmin(permissions.BasePermission):
    """Allow read-only access to hospital members, write only for hospital admins."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        hospital_id = request.query_params.get("hospital")
        if hospital_id:
            try:
                hospital_id = int(hospital_id)
            except (ValueError, TypeError):
                return False

            roles = get_user_roles_for_hospital(request.user, hospital_id)
            return "Admin" in roles or "Hospital Manager" in roles

        return False