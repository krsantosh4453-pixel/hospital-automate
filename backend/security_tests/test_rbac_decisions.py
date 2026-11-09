"""
Owner's RBAC decisions of 2026-11-09 (docs/architecture/phase-3-rbac-decisions-plan.md),
with the recommended answers to Q1-Q6. Synthetic data only.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from doctors.models import Doctor
from hospital.models import Hospital
from users.models import StaffRole
from users.permissions import get_user_roles

from .test_tenant_isolation import make_staff

User = get_user_model()


def client_for(user, hospital):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
    return client


class ManagerRoleAssignmentTests(TestCase):
    """Decision 1 and Q1: what a Hospital Manager may hand out, always audited."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic RBAC", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic RBAC Other", is_active=True)
        cls.admin, _ = make_staff("rbac_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.manager, _ = make_staff("rbac_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.peer, _ = make_staff("rbac_peer_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.staff, _ = make_staff("rbac_staff", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.outsider, _ = make_staff("rbac_outsider", cls.other, role=StaffRole.RECEPTIONIST)

    def assign(self, actor, target, role, hospital=None):
        return client_for(actor, hospital or self.hospital).patch(
            f"/api/v1/users/{target.id}/membership/", {"role": role}, format="json")

    def test_a_manager_assigns_clinical_and_operational_roles(self):
        for role in (StaffRole.DOCTOR, StaffRole.NURSE, StaffRole.PHARMACIST, StaffRole.COMPOUNDER,
                     StaffRole.LAB_STAFF, StaffRole.BILLING_STAFF, StaffRole.INVENTORY_STAFF,
                     StaffRole.BLOOD_BANK_STAFF, StaffRole.RECEPTIONIST):
            self.assertEqual(self.assign(self.manager, self.staff, role).status_code, 200, role)

    def test_a_manager_cannot_create_admins_or_managers(self):
        for role in (StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER):
            self.assertEqual(self.assign(self.manager, self.staff, role).status_code, 403, role)
        self.assertEqual(get_user_roles(self.staff, self.hospital.id), [StaffRole.RECEPTIONIST])

    def test_a_manager_cannot_change_another_manager(self):
        self.assertEqual(self.assign(self.manager, self.peer, StaffRole.RECEPTIONIST).status_code, 403)
        self.assertEqual(get_user_roles(self.peer, self.hospital.id), [StaffRole.HOSPITAL_MANAGER])

    def test_an_admin_assigns_hospital_manager(self):
        self.assertEqual(self.assign(self.admin, self.staff, StaffRole.HOSPITAL_MANAGER).status_code, 200)

    def test_a_manager_cannot_assign_at_another_hospital(self):
        response = self.assign(self.manager, self.outsider, StaffRole.DOCTOR, hospital=self.other)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(get_user_roles(self.outsider, self.other.id), [StaffRole.RECEPTIONIST])

    def test_a_manager_cannot_invite_an_admin_or_manager(self):
        for role in (StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER):
            response = client_for(self.manager, self.hospital).post(
                "/api/v1/users/invite/", {"name": "X", "email": f"{role[:3].lower()}@example.test", "role": role},
                format="json")
            self.assertEqual(response.status_code, 403, role)

    def test_invitations_and_role_changes_are_audited(self):
        invited = client_for(self.manager, self.hospital).post(
            "/api/v1/users/invite/", {"name": "Synthetic Nurse", "email": "nurse@example.test", "role": "Nurse",
                                     "phone": "9000000082"},
            format="json")
        self.assertEqual(invited.status_code, 201, invited.content)
        self.assign(self.manager, self.staff, StaffRole.BILLING_STAFF)

        actions = set(AuditLog.objects.filter(hospital=self.hospital).values_list("action", flat=True))
        self.assertTrue({"users.staff.invited", "users.staff.membership_changed"} <= actions, actions)


class DoctorVerificationTests(TestCase):
    """Decision 1 and Q2: the hospital Admin records a doctor's registration check."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Verify", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Verify Other", is_active=True)
        cls.admin, _ = make_staff("verify_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.manager, _ = make_staff("verify_manager", cls.hospital, role=StaffRole.HOSPITAL_MANAGER)
        cls.other_admin, _ = make_staff("verify_other_admin", cls.other, role=StaffRole.ADMIN)
        cls.doctor = Doctor.objects.create(hospital=cls.hospital, name="Dr Verify", specialization="General",
                                           phone="9000000080", registration_number="KMC-12345")

    def verify(self, actor, hospital=None, doctor=None, body=None):
        doctor = doctor or self.doctor
        return client_for(actor, hospital or self.hospital).post(
            f"/api/v1/doctors/{doctor.id}/verify-registration/", body or {"registration_council": "KMC"}, format="json")

    def test_the_admin_verifies_and_it_is_audited(self):
        response = self.verify(self.admin)

        self.assertEqual(response.status_code, 200, response.content)
        self.doctor.refresh_from_db()
        self.assertEqual((self.doctor.registration_verified_by, self.doctor.registration_council), (self.admin, "KMC"))
        self.assertIsNotNone(self.doctor.registration_verified_at)
        self.assertTrue(AuditLog.objects.filter(action="doctors.registration_verified", hospital=self.hospital).exists())

    def test_a_manager_or_another_hospitals_admin_cannot_verify(self):
        self.assertEqual(self.verify(self.manager).status_code, 403)
        self.assertIn(self.verify(self.other_admin, hospital=self.other).status_code, (403, 404))
        self.assertIn(self.verify(self.other_admin, hospital=self.hospital).status_code, (403, 404))
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.registration_verified_at)

    def test_a_doctor_without_a_registration_number_cannot_be_verified(self):
        unregistered = Doctor.objects.create(hospital=self.hospital, name="Dr None", specialization="General",
                                             phone="9000000081")
        self.assertEqual(self.verify(self.admin, doctor=unregistered).status_code, 400)

    def test_changing_the_registration_number_clears_the_verification(self):
        self.verify(self.admin)

        response = client_for(self.admin, self.hospital).patch(f"/api/v1/doctors/{self.doctor.id}/",
                                                               {"registration_number": "KMC-99999"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.registration_verified_at)

    def test_verification_fields_cannot_be_set_through_the_doctor_form(self):
        client_for(self.admin, self.hospital).patch(f"/api/v1/doctors/{self.doctor.id}/",
                                                    {"registration_verified_at": "2026-01-01T00:00:00Z"}, format="json")
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.registration_verified_at)

    def test_only_the_admin_switches_the_verified_doctors_rule(self):
        url = f"/api/v1/hospital/hospitals/{self.hospital.id}/"
        self.assertEqual(client_for(self.manager, self.hospital).patch(
            url, {"require_verified_doctors": True}, format="json").status_code, 403)
        self.assertEqual(client_for(self.admin, self.hospital).patch(
            url, {"require_verified_doctors": True}, format="json").status_code, 200)
        self.hospital.refresh_from_db()
        self.assertTrue(self.hospital.require_verified_doctors)
