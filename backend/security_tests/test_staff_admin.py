"""Staff administration: approval, role grants, isolation between hospitals."""

from django.contrib.auth import get_user_model
from django.test import TestCase
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
        applicant = User.objects.create_user(username="applicant", password="Synthetic-Pass-123")
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
        self.assertEqual([p["username"] for p in data["pending"]], ["applicant"])

    def test_non_admin_cannot_manage(self):
        self.assertEqual(self.api(self.nurse_b, self.b).get("/api/users/").status_code, 403)
        self.assertEqual(self.api(self.admin_a, self.b).get("/api/users/").status_code, 403)

    def test_approve_and_change_role(self):
        resp = self.api(self.manager_a, self.a).post(f"/api/users/{self.applicant.id}/approve/", {"role": "Admin"}, format="json")
        self.assertEqual(resp.status_code, 403)  # manager cannot grant Admin
        resp = self.api(self.manager_a, self.a).post(f"/api/users/{self.applicant.id}/approve/", {"role": "Nurse"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(StaffHospitalMembership.objects.filter(staff__user=self.applicant, hospital=self.a, role="Nurse").exists())
        resp = self.api(self.admin_a, self.a).patch(f"/api/users/{self.applicant.id}/membership/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(StaffHospitalMembership.objects.get(staff__user=self.applicant).is_active)
        self.assertTrue(AuditLog.objects.filter(action="users.staff.approved").exists())

    def test_cannot_change_staff_of_other_hospital(self):
        resp = self.api(self.admin_a, self.a).patch(f"/api/users/{self.nurse_b.id}/membership/", {"role": "Admin"}, format="json")
        self.assertEqual(resp.status_code, 404)
