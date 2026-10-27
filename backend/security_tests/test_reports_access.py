"""Report templates, saved reports and schedules: who may read and write them."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient
from reports.models import ReportTemplate, SavedReport, ScheduledReport
from users.models import StaffRole

from .test_tenant_isolation import make_staff

User = get_user_model()


class ReportAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital_a = Hospital.objects.create(name="Synthetic A", is_active=True)
        cls.hospital_b = Hospital.objects.create(name="Synthetic B", is_active=True)
        cls.admin_a, _ = make_staff("rep_admin_a", cls.hospital_a, role=StaffRole.ADMIN)
        cls.staff_b, _ = make_staff("rep_staff_b", cls.hospital_b, role=StaffRole.ADMIN)
        cls.patient_user = User.objects.create_user(username="rep_patient", password="x-Synthetic-1")
        Patient.objects.create(
            user=cls.patient_user, name="Synthetic Patient", age=30, gender="Male",
            phone="9000000031", hospital=cls.hospital_a,
        )
        cls.template = ReportTemplate.objects.create(name="Monthly", report_type="financial", is_system=True)
        cls.platform_admin = User.objects.create_superuser("rep_root", password="x-Synthetic-1")

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        if hospital is not None:
            client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def test_patient_account_cannot_read_or_write_templates(self):
        client = self.client_for(self.patient_user)
        self.assertEqual(client.get("/api/reports/templates/").status_code, 403)
        resp = client.patch(f"/api/reports/templates/{self.template.id}/", {"name": "Hacked"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Monthly")

    def test_hospital_staff_read_templates_but_cannot_change_shared_ones(self):
        client = self.client_for(self.admin_a, self.hospital_a)
        self.assertEqual(client.get("/api/reports/templates/").status_code, 200)
        resp = client.delete(f"/api/reports/templates/{self.template.id}/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ReportTemplate.objects.filter(pk=self.template.pk).exists())

    def test_platform_admin_can_change_templates(self):
        resp = self.client_for(self.platform_admin).patch(
            f"/api/reports/templates/{self.template.id}/", {"name": "Monthly v2"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_saved_report_without_hospital_is_a_validation_error(self):
        resp = self.client_for(self.admin_a).post(
            "/api/reports/saved/", {"name": "Mine", "report_type": "financial", "period": "today"}, format="json"
        )
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_saved_report_for_foreign_hospital_is_refused(self):
        resp = self.client_for(self.admin_a).post(
            "/api/reports/saved/",
            {"name": "Theirs", "report_type": "financial", "period": "today", "hospital": self.hospital_b.id},
            format="json",
        )
        self.assertIn(resp.status_code, (400, 403), resp.content)
        self.assertFalse(SavedReport.objects.filter(hospital=self.hospital_b).exists())

    def test_schedule_cannot_be_moved_to_foreign_hospital(self):
        schedule = ScheduledReport.objects.create(
            name="Daily", template=self.template, hospital=self.hospital_a, frequency="daily",
        )
        resp = self.client_for(self.admin_a, self.hospital_a).patch(
            f"/api/reports/scheduled/{schedule.id}/", {"hospital": self.hospital_b.id}, format="json"
        )
        self.assertIn(resp.status_code, (400, 403), resp.content)
        schedule.refresh_from_db()
        self.assertEqual(schedule.hospital_id, self.hospital_a.id)

    def test_schedule_recipients_must_be_staff_of_that_hospital(self):
        resp = self.client_for(self.admin_a, self.hospital_a).post(
            "/api/reports/scheduled/",
            {
                "name": "Leak", "template": self.template.id, "hospital": self.hospital_a.id,
                "frequency": "daily", "recipients": [self.staff_b.id],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(ScheduledReport.objects.filter(name="Leak").exists())
