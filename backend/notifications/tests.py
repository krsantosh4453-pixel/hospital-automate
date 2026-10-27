"""Tests for notifications module."""

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from notifications.models import Notification, Consent, OTPVerification

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
        return f"/api/notifications/notifications/?hospital={self.hospital_a.id}"

    def _get_consent_url(self):
        return f"/api/notifications/consents/?hospital={self.hospital_a.id}"

    def test_create_notification(self):
        """Test creating a notification."""
        response = self.client.post(
            self._get_notifications_url(),
            {
                "patient": self.patient.id,
                "title": "Appointment Reminder",
                "message": "Your appointment is tomorrow at 10 AM",
                "notification_type": "Appointment",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Appointment Reminder")
        self.assertEqual(response.data["notification_type"], "Appointment")

    def test_consent_record(self):
        """Test consent record model."""
        consent = Consent.objects.create(
            patient=self.patient,
            purpose="Treatment",
            granted=True,
        )
        self.assertEqual(consent.patient, self.patient)
        self.assertTrue(consent.granted)

    def test_otp_verification(self):
        """Test OTP verification model."""
        from django.utils import timezone
        from datetime import timedelta
        otp = OTPVerification.objects.create(
            phone="9876543210",
            otp="123456",
            purpose="Login",
            channel="sms",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertEqual(otp.phone, "9876543210")
        self.assertEqual(otp.purpose, "Login")
        self.assertFalse(otp.is_verified)

    def test_list_notifications(self):
        """Test listing notifications."""
        Notification.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            title="Test",
            message="Test message",
            notification_type="General",
        )
        response = self.client.get(self._get_notifications_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)