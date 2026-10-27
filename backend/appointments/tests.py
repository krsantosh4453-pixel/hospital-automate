"""Tests for appointments module."""

from datetime import date, time, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from appointments.models import Appointment

User = get_user_model()


class AppointmentAPITests(TestCase):
    """Tests for appointment API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="General")

        # Create staff user for Hospital A
        self.user = User.objects.create_user(
            username="receptionist_a",
            email="receptionist_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.RECEPTIONIST,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.RECEPTIONIST,
            is_active=True,
        )

        # Create doctor
        self.doctor = Doctor.objects.create(
            name="Dr. Test",
            specialization="General",
            phone="9876543210",
            email="doctor@hospital.com",
            hospital=self.hospital_a,
            department=self.dept,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Test Patient",
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

        # Create appointment
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 0),
            hospital=self.hospital_a,
            status="Scheduled",
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_list_url(self):
        return f"/api/appointments/?hospital={self.hospital_a.id}"

    def _get_detail_url(self, pk):
        return f"/api/appointments/{pk}/"

    def _get_action_url(self, pk, action):
        return f"/api/appointments/{pk}/{action}/?hospital={self.hospital_a.id}"

    def test_list_appointments_scoped_to_hospital(self):
        """Test appointment list is scoped to user's hospital."""
        response = self.client.get(self._get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.appointment.id)

    def test_create_appointment(self):
        """Test creating an appointment."""
        response = self.client.post(
            self._get_list_url(),
            {
                "patient": self.patient.id,
                "doctor": self.doctor.id,
                "appointment_date": str(date.today() + timedelta(days=2)),
                "appointment_time": "11:00",
                "hospital": self.hospital_a.id,
                "reason": "Follow-up",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "Scheduled")

    def test_cancel_appointment(self):
        """Test cancelling an appointment."""
        response = self.client.post(
            self._get_action_url(self.appointment.id, "cancel"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "Cancelled")

    def test_reschedule_appointment(self):
        """Test rescheduling an appointment."""
        response = self.client.post(
            self._get_action_url(self.appointment.id, "reschedule"),
            {
                "appointment_date": str(date.today() + timedelta(days=3)),
                "appointment_time": "14:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(str(self.appointment.appointment_date), str(date.today() + timedelta(days=3)))
        self.assertEqual(str(self.appointment.appointment_time), "14:00:00")


class AppointmentModelTests(TestCase):
    """Tests for appointment model methods and constraints."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Test Hospital", is_active=True)
        self.dept = Department.objects.create(hospital=self.hospital, name="General")
        self.doctor = Doctor.objects.create(
            name="Dr. Test",
            specialization="General",
            phone="9876543210",
            email="doctor@hospital.com",
            hospital=self.hospital,
            department=self.dept,
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital,
        )

    def test_appointment_str(self):
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            hospital=self.hospital,
        )
        self.assertIn("Test Patient", str(appt))
        self.assertIn("Dr. Test", str(appt))