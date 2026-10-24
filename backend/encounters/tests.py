"""Tests for encounters module."""

from datetime import date, time
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from encounters.models import Visit, DoctorSchedule, QueueToken

User = get_user_model()


class EncountersAPITests(TestCase):
    """Tests for encounters API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="OPD")

        # Create receptionist user
        self.user = User.objects.create_user(
            username="receptionist_enc",
            email="receptionist_enc@hospital.com",
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
            name="Dr. Encounter",
            specialization="General Medicine",
            phone="9876543210",
            email="enc_doc@hospital.com",
            hospital=self.hospital_a,
            department=self.dept,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Encounter Patient",
            age=28,
            gender="Female",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Create doctor schedule
        self.schedule = DoctorSchedule.objects.create(
            doctor=self.doctor,
            day="Monday",
            start_time=time(9, 0),
            end_time=time(13, 0),
            is_available=True,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_visits_url(self):
        return f"/api/encounters/visits/?hospital={self.hospital_a.id}"

    def _get_queue_url(self):
        return f"/api/encounters/queue-tokens/?hospital={self.hospital_a.id}"

    def _get_schedules_url(self):
        return f"/api/encounters/schedules/?hospital={self.hospital_a.id}"

    def test_create_visit(self):
        """Test creating a visit."""
        response = self.client.post(
            self._get_visits_url(),
            {
                "patient": self.patient.id,
                "doctor": self.doctor.id,
                "hospital": self.hospital_a.id,
                "visit_type": "OPD",
                "chief_complaint": "Fever",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertEqual(response.data["visit_type"], "OPD")

    def test_queue_token(self):
        """Test queue token model."""
        visit = Visit.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            visit_type="OPD",
            chief_complaint="Test",
            status="Waiting",
        )
        token = QueueToken.objects.create(
            visit=visit,
            token_number=1,
            hospital=self.hospital_a,
            patient=self.patient,
            doctor=self.doctor,
            status="Waiting",
        )
        self.assertEqual(token.visit, visit)
        self.assertEqual(token.token_number, 1)
        self.assertEqual(token.status, "Waiting")

    def test_doctor_schedule(self):
        """Test doctor schedule model."""
        self.assertEqual(self.schedule.doctor, self.doctor)
        self.assertEqual(self.schedule.day, "Monday")
        self.assertEqual(self.schedule.is_available, True)

    def test_list_visits(self):
        """Test listing visits."""
        Visit.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            visit_type="OPD",
            chief_complaint="Test",
            status="Completed",
        )
        response = self.client.get(self._get_visits_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)