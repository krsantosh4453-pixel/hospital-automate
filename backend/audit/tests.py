"""Tests for audit module."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from audit.models import AuditLog, AIInteraction

User = get_user_model()


class AuditAPITests(TestCase):
    """Tests for audit API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="Admin")

        # Create admin user
        self.user = User.objects.create_user(
            username="admin_audit",
            email="admin_audit@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.ADMIN,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.ADMIN,
            is_active=True,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_audit_logs_url(self):
        return f"/api/audit/audit-logs/?hospital={self.hospital_a.id}"

    def _get_ai_logs_url(self):
        return f"/api/audit/ai-interactions/?hospital={self.hospital_a.id}"

    def test_audit_log_creation(self):
        """Test audit log model."""
        log = AuditLog.objects.create(
            user=self.user,
            action="CREATE",
            model_name="Patient",
            object_id="1",
            details="Created patient",
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.model_name, "Patient")

    def test_ai_interaction_log(self):
        """Test AI interaction log model."""
        from patients.models import Patient, PatientHospital
        patient = Patient.objects.create(
            name="AI Patient",
            age=40,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=patient,
            hospital=self.hospital_a,
            is_active=True,
        )
        ai_log = AIInteraction.objects.create(
            patient=patient,
            input_text="Patient says...",
            ai_output="Transcribed text",
            status="Draft",
        )
        self.assertEqual(ai_log.patient, patient)
        self.assertEqual(ai_log.status, "Draft")

    def test_list_audit_logs(self):
        """Test listing audit logs."""
        AuditLog.objects.create(
            user=self.user,
            hospital=self.hospital_a,
            action="UPDATE",
            model_name="Patient",
            object_id="1",
            details="Updated age",
        )
        # A platform-level row with no hospital is not shown to hospital admins.
        AuditLog.objects.create(user=self.user, action="PLATFORM", model_name="Hospital")
        response = self.client.get(self._get_audit_logs_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["action"], "UPDATE")

    def test_audit_logs_read_only(self):
        """Test audit logs are read-only."""
        response = self.client.post(
            self._get_audit_logs_url(),
            {"action": "TEST"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AuditLogFilterTests(TestCase):
    """The audit viewer page (A15) filters the trail on the server."""

    _get_audit_logs_url = AuditAPITests._get_audit_logs_url

    def setUp(self):
        AuditAPITests.setUp(self)
        self.nurse = User.objects.create_user(username="nurse_meera", password="testpass123")
        self.old = AuditLog.objects.create(
            user=self.user, hospital=self.hospital_a, action="patients.patient.create", model_name="Patient", object_id="1"
        )
        AuditLog.objects.filter(pk=self.old.pk).update(created_at="2026-10-01T09:00:00Z")
        self.new = AuditLog.objects.create(
            user=self.nurse, hospital=self.hospital_a, action="clinical.vitalsign.update", model_name="VitalSign", object_id="9"
        )
        AuditLog.objects.create(
            user=self.user, hospital=self.hospital_b, action="patients.patient.create", model_name="Patient", object_id="2"
        )

    def ids(self, query=""):
        response = self.client.get(f"{self._get_audit_logs_url()}{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return [row["id"] for row in response.data.get("results", response.data)]

    def test_newest_first_and_only_this_hospital(self):
        self.assertEqual(self.ids(), [self.new.id, self.old.id])

    def test_filters_by_action_record_type_and_user(self):
        self.assertEqual(self.ids("&action=vitalsign"), [self.new.id])
        self.assertEqual(self.ids("&model=patient"), [self.old.id])
        self.assertEqual(self.ids("&user=meera"), [self.new.id])

    def test_filters_by_date_range(self):
        self.assertEqual(self.ids("&from=2026-09-30&to=2026-10-02"), [self.old.id])

    def test_rejects_a_malformed_date(self):
        response = self.client.get(f"{self._get_audit_logs_url()}&from=01/10/2026")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_shows_who_acted(self):
        response = self.client.get(f"{self._get_audit_logs_url()}&user=meera")

        self.assertEqual(response.data["results"][0]["username"], "nurse_meera")
