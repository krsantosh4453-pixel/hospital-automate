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
        return f"/api/audit/logs/?hospital={self.hospital_a.id}"

    def _get_ai_logs_url(self):
        return f"/api/audit/ai-logs/?hospital={self.hospital_a.id}"

    def test_audit_log_creation(self):
        """Test audit log model."""
        log = AuditLog.objects.create(
            user=self.user,
            hospital=self.hospital_a,
            action="CREATE",
            resource_type="Patient",
            resource_id="1",
            details={"name": "Test Patient"},
            ip_address="127.0.0.1",
            user_agent="Test Agent",
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.resource_type, "Patient")

    def test_ai_interaction_log(self):
        """Test AI interaction log model."""
        ai_log = AIInteraction.objects.create(
            user=self.user,
            hospital=self.hospital_a,
            interaction_type="Transcription",
            input_data={"audio_length": 120},
            output_data={"text": "Patient says..."},
            model_used="whisper-1",
            tokens_used=150,
            cost_usd="0.001",
            status="Success",
        )
        self.assertEqual(ai_log.user, self.user)
        self.assertEqual(ai_log.interaction_type, "Transcription")
        self.assertEqual(ai_log.status, "Success")

    def test_list_audit_logs(self):
        """Test listing audit logs."""
        AuditLog.objects.create(
            user=self.user,
            hospital=self.hospital_a,
            action="UPDATE",
            resource_type="Patient",
            resource_id="1",
            details={"field": "age"},
        )
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
