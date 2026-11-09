"""Phase 3 platform staff: platform rights live apart from hospital roles (synthetic data only)."""

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from reports.models import ReportTemplate
from users.models import PlatformStaff, StaffRole
from users.platform import has_platform_permission

from .test_tenant_isolation import make_staff

User = get_user_model()


class PlatformStaffTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital_a = Hospital.objects.create(name="Synthetic Platform A", is_active=True)
        cls.hospital_b = Hospital.objects.create(name="Synthetic Platform B", is_active=True)
        cls.patient = Patient.objects.create(name="Synthetic Platform Patient", age=40, gender="Male",
                                             phone="9000000040", hospital=cls.hospital_a)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital_a, uhid="PLAT-1")
        cls.root = User.objects.create_superuser("platform_root", password="x-Synthetic-1")
        cls.support = User.objects.create_user("platform_support", password="x-Synthetic-1")
        PlatformStaff.objects.create(user=cls.support, role=PlatformStaff.Role.SUPPORT)
        cls.hospital_admin, _ = make_staff("platform_hadmin", cls.hospital_a, role=StaffRole.ADMIN)
        cls.template = ReportTemplate.objects.create(name="Monthly", report_type="financial", is_system=True)

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        if hospital is not None:
            client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def test_a_new_superuser_gets_a_platform_admin_row(self):
        staff = PlatformStaff.objects.get(user=self.root)
        self.assertEqual((staff.role, staff.is_active), (PlatformStaff.Role.ADMIN, True))

    def test_platform_admin_sees_every_hospital_but_no_patients(self):
        client = self.client_for(self.root)

        hospitals = client.get("/api/v1/hospital/hospitals/").json()
        rows = hospitals.get("results", hospitals)
        self.assertTrue({self.hospital_a.id, self.hospital_b.id} <= {row["id"] for row in rows})

        for hospital in (None, self.hospital_a):
            patients = self.client_for(self.root, hospital).get("/api/v1/patients/")
            body = patients.json() if patients.status_code == 200 else {}
            self.assertNotIn(self.patient.id, [row["id"] for row in body.get("results", [])], patients.status_code)
        self.assertIn(self.client_for(self.root, self.hospital_a).get(f"/api/v1/patients/{self.patient.id}/")
                      .status_code, (403, 404))

    def test_platform_support_views_hospitals_but_cannot_delete_or_edit_templates(self):
        client = self.client_for(self.support)

        self.assertEqual(client.get("/api/v1/hospital/hospitals/").status_code, 200)
        self.assertEqual(client.delete(f"/api/v1/hospital/hospitals/{self.hospital_b.id}/").status_code, 403)
        self.assertEqual(client.patch(f"/api/v1/reports/templates/{self.template.id}/", {"name": "x"},
                                      format="json").status_code, 403)
        self.assertTrue(Hospital.objects.filter(pk=self.hospital_b.pk).exists())

    def test_a_hospital_admin_cannot_reach_platform_actions(self):
        client = self.client_for(self.hospital_admin, self.hospital_a)

        self.assertEqual(client.delete(f"/api/v1/hospital/hospitals/{self.hospital_a.id}/").status_code, 403)
        self.assertEqual(client.get("/api/v1/notifications/otp-verifications/").status_code, 403)
        self.assertEqual(client.patch(f"/api/v1/reports/templates/{self.template.id}/", {"name": "x"},
                                      format="json").status_code, 403)
        hospitals = client.get("/api/v1/hospital/hospitals/").json()
        self.assertEqual([row["id"] for row in hospitals.get("results", hospitals)], [self.hospital_a.id])
        self.assertFalse(has_platform_permission(self.hospital_admin, "platform.hospitals.view"))

    def test_an_inactive_platform_row_grants_nothing(self):
        PlatformStaff.objects.filter(user=self.root).update(is_active=False)

        self.assertEqual(self.client_for(self.root).get("/api/v1/notifications/otp-verifications/").status_code, 403)
        self.assertFalse(has_platform_permission(self.root, "platform.hospitals.delete"))

    def test_platform_permissions_are_not_hospital_permissions(self):
        from users.platform import PLATFORM_PERMISSIONS

        self.assertTrue(all(name.startswith("platform.") for names in PLATFORM_PERMISSIONS.values()
                            for name in names))


class PlatformStaffMigrationTests(TransactionTestCase):
    """users/0006 copies every active superuser into PlatformStaff and reverses cleanly."""

    BEFORE = [("users", "0005_device_session")]
    AFTER = [("users", "0006_platform_staff")]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        self.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_superusers_keep_platform_access_and_the_migration_reverses(self):
        old = self.migrate(self.BEFORE)
        OldUser = old.get_model("auth", "User")
        root = OldUser.objects.create(username="legacy_root", is_superuser=True, is_staff=True, is_active=True)
        OldUser.objects.create(username="legacy_off", is_superuser=True, is_active=False)
        OldUser.objects.create(username="legacy_plain", is_active=True)

        new = self.migrate(self.AFTER)

        rows = new.get_model("users", "PlatformStaff").objects.values_list("user__username", "role", "is_active")
        self.assertEqual(list(rows), [("legacy_root", "platform_admin", True)])

        back = self.migrate(self.BEFORE)
        self.assertTrue(back.get_model("auth", "User").objects.filter(pk=root.pk, is_superuser=True).exists())
