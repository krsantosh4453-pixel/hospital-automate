"""Tests for notifications module."""

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from notifications.models import Notification, NotificationTemplate, ConsentRecord, OTPVerification

User = get_user_model()


class NotificationsAPITests(TestCase):
    """Tests for notifications API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="Admin")

        # Create staff user
        self.user = User.objects.create_user(
            username="admin_notif",
            email="admin_notif@hospital.com",
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

        # Create patient
        self.patient = Patient.objects.create(
            name="Notif Patient",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_notifications_url(self):
        return f"/api/notifications/?hospital={self.hospital_a.id}"

    def _get_templates_url(self):
        return f"/api/notifications/templates/?hospital={self.hospital_a.id}"

    def _get_consent_url(self):
        return f"/api/notifications/consent/?hospital={self.hospital_a.id}"

    def test_create_notification(self):
        """Test creating a notification."""
        response = self.client.post(
            self._get_notifications_url(),
            {
                "patient": self.patient.id,
                "channel": "SMS",
                "subject": "Appointment Reminder",
                "message": "Your appointment is tomorrow at 10 AM",
                "status": "Pending",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["channel"], "SMS")
        self.assertEqual(response.data["status"], "Pending")

    def test_notification_template(self):
        """Test notification template model."""
        template = NotificationTemplate.objects.create(
            hospital=self.hospital_a,
            name="Appointment Reminder",
            channel="SMS",
            subject="Appointment Reminder",
            template="Dear {{patient_name}}, your appointment is on {{date}} at {{time}}.",
            is_active=True,
        )
        self.assertEqual(template.hospital, self.hospital_a)
        self.assertEqual(template.channel, "SMS")

    def test_consent_record(self):
        """Test consent record model."""
        consent = ConsentRecord.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            consent_type="Treatment",
            status="Given",
            signed_by="Patient",
            version="1.0",
        )
        self.assertEqual(consent.patient, self.patient)
        self.assertEqual(consent.status, "Given")

    def test_otp_verification(self):
        """Test OTP verification model."""
        otp = OTPVerification.objects.create(
            phone="9876543210",
            otp="123456",
            purpose="Login",
            expires_at=date.today(),
        )
        self.assertEqual(otp.phone, "9876543210")
        self.assertEqual(otp.purpose, "Login")
        self.assertFalse(otp.is_verified)

    def test_list_notifications(self):
        """Test listing notifications."""
        Notification.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            channel="Email",
            subject="Test",
            message="Test message",
            status="Sent",
        )
        response = self.client.get(self._get_notifications_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
