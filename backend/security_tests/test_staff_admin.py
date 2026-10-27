"""Staff administration: approval, role grants, isolation between hospitals."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from audit.models import AuditLog
from hospital.models import Hospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

from .test_tenant_isolation import make_staff

User = get_user_model()


class StaffAdminTests(TestCase):
    def setUp(self):
        self.a = Hospital.objects.create(name="Synthetic Admin A", is_active=True)
        self.b = Hospital.objects.create(name="Synthetic Admin B", is_active=True)
        self.admin_a, _ = make_staff("staff_admin_a", self.a, role=StaffRole.ADMIN)
        self.manager_a, _ = make_staff("staff_manager_a", self.a, role=StaffRole.HOSPITAL_MANAGER)
        self.nurse_b, _ = make_staff("staff_nurse_b", self.b, role=StaffRole.NURSE)
        # Signed up before staff self-registration was closed; belongs to no hospital.
        applicant = User.objects.create_user(username="applicant", email="applicant@example.com",
                                             password="Synthetic-Pass-123")
        StaffProfile.objects.create(user=applicant, role=StaffRole.NURSE, employee_id="EMP-APP", is_active_staff=False)
        self.applicant = applicant

    def api(self, user, hospital):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def test_list_only_own_hospital_staff(self):
        data = self.api(self.admin_a, self.a).get("/api/users/").json()
        usernames = {row["username"] for row in data["staff"]}
        self.assertIn("staff_manager_a", usernames)
        self.assertNotIn("staff_nurse_b", usernames)

    def test_unattached_applicants_are_not_shown_to_any_hospital(self):
        data = self.api(self.admin_a, self.a).get("/api/users/").json()
        self.assertNotIn("pending", data)
        self.assertNotIn("applicant", {row["username"] for row in data["staff"]})

    def test_applicant_cannot_be_approved_by_id(self):
        resp = self.api(self.admin_a, self.a).post(f"/api/users/{self.applicant.id}/approve/", {"role": "Nurse"},
                                                   format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(StaffHospitalMembership.objects.filter(staff__user=self.applicant).exists())

    def test_non_admin_cannot_manage(self):
        self.assertEqual(self.api(self.nurse_b, self.b).get("/api/users/").status_code, 403)
        self.assertEqual(self.api(self.admin_a, self.b).get("/api/users/").status_code, 403)

    def test_invite_admits_an_earlier_applicant_and_role_can_change(self):
        body = {"name": "Synthetic Applicant", "phone": "9876500010", "email": "applicant@example.com"}
        resp = self.api(self.manager_a, self.a).post("/api/users/invite/", {**body, "role": "Admin"}, format="json")
        self.assertEqual(resp.status_code, 403)  # manager cannot grant Admin
        resp = self.api(self.manager_a, self.a).post("/api/users/invite/", {**body, "role": "Nurse"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(StaffHospitalMembership.objects.filter(staff__user=self.applicant, hospital=self.a, role="Nurse").exists())
        self.assertTrue(StaffProfile.objects.get(user=self.applicant).is_active_staff)
        resp = self.api(self.admin_a, self.a).patch(f"/api/users/{self.applicant.id}/membership/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(StaffHospitalMembership.objects.get(staff__user=self.applicant).is_active)
        self.assertTrue(AuditLog.objects.filter(action="users.staff.invited").exists())

    def test_staff_roles_cannot_self_register(self):
        client = APIClient(raise_request_exception=False)
        for index, role in enumerate(("Doctor", "Nurse", "Compounder", "Receptionist")):
            resp = client.post("/api/auth/register/", {
                "role": role, "full_name": "Synthetic Signup", "phone": f"98765000{20 + index}",
                "email": f"signup{index}@example.com", "password": "correct-horse", "confirm_password": "correct-horse",
            }, format="json")
            self.assertEqual(resp.status_code, 403, (role, resp.content))
            self.assertFalse(User.objects.filter(email=f"signup{index}@example.com").exists())

    @override_settings(ADMIN_INVITE_CODE="synthetic-admin-code")
    def test_admin_can_still_register_with_the_invite_code(self):
        resp = APIClient().post("/api/auth/register/", {
            "role": "Admin", "full_name": "Synthetic Owner", "phone": "9876500030", "email": "owner@example.com",
            "password": "correct-horse", "confirm_password": "correct-horse", "invite_code": "synthetic-admin-code",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(StaffProfile.objects.get(user__email="owner@example.com").is_active_staff)

    def test_cannot_change_staff_of_other_hospital(self):
        resp = self.api(self.admin_a, self.a).patch(f"/api/users/{self.nurse_b.id}/membership/", {"role": "Admin"}, format="json")
        self.assertEqual(resp.status_code, 404)
