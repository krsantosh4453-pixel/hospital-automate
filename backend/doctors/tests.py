"""Tests for doctors module."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from doctors.models import Doctor

User = get_user_model()


class DoctorAPITests(TestCase):
    """Tests for doctor API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept_a = Department.objects.create(hospital=self.hospital_a, name="Cardiology")
        self.dept_b = Department.objects.create(hospital=self.hospital_b, name="Neurology")

        # Create staff user for Hospital A
        self.user = User.objects.create_user(
            username="admin_a",
            email="admin_a@hospital.com",
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

        # Create doctor in Hospital A
        self.doctor_a = Doctor.objects.create(
            name="Dr. Alice",
            specialization="Cardiology",
            phone="9876543210",
            email="alice@hospital.com",
            hospital=self.hospital_a,
            department=self.dept_a,
        )

        # Create doctor in Hospital B
        self.doctor_b = Doctor.objects.create(
            name="Dr. Bob",
            specialization="Neurology",
            phone="9876543211",
            email="bob@hospital.com",
            hospital=self.hospital_b,
            department=self.dept_b,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_list_url(self):
        return f"/api/doctors/?hospital={self.hospital_a.id}"

    def _get_detail_url(self, pk):
        return f"/api/doctors/{pk}/?hospital={self.hospital_a.id}"

    def test_list_doctors_scoped_to_hospital(self):
        """Test doctor list is scoped to user's hospital."""
        response = self.client.get(self._get_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        names = [d["name"] for d in data]
        self.assertIn("Dr. Alice", names)
        self.assertNotIn("Dr. Bob", names)

    def test_create_doctor_in_hospital(self):
        """Test creating a doctor in the user's hospital."""
        response = self.client.post(
            self._get_list_url(),
            {
                "name": "Dr. Charlie",
                "specialization": "Cardiology",
                "phone": "9999999999",
                "email": "charlie@hospital.com",
                "hospital": self.hospital_a.id,
                "department": self.dept_a.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Dr. Charlie")
        self.assertEqual(response.data["hospital"], self.hospital_a.id)

    def test_cannot_create_doctor_in_other_hospital(self):
        """Test cannot create doctor in hospital user doesn't belong to."""
        response = self.client.post(
            self._get_list_url(),
            {
                "name": "Dr. Cross",
                "specialization": "Neurology",
                "phone": "8888888888",
                "email": "cross@hospital.com",
                "hospital": self.hospital_b.id,
                "department": self.dept_b.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_doctor_in_hospital(self):
        """Test retrieving a doctor in the user's hospital."""
        response = self.client.get(self._get_detail_url(self.doctor_a.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Dr. Alice")

    def test_update_doctor(self):
        """Test updating a doctor."""
        response = self.client.patch(
            self._get_detail_url(self.doctor_a.id),
            {"specialization": "Interventional Cardiology"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["specialization"], "Interventional Cardiology")
        self.doctor_a.refresh_from_db()
        self.assertEqual(self.doctor_a.specialization, "Interventional Cardiology")

    def test_doctor_availability(self):
        """Test doctor availability model."""
        avail = # DoctorAvailability.objects.create(
            doctor=self.doctor_a,
            day_of_week=1,  # Monday
            start_time="09:00",
            end_time="17:00",
            is_active=True,
        )
        self.assertEqual(avail.doctor, self.doctor_a)
        self.assertEqual(avail.day_of_week, 1)

    def test_doctor_schedule(self):
        """Test doctor schedule model."""
        schedule = # DoctorSchedule.objects.create(
            doctor=self.doctor_a,
            date="2026-10-05",
            start_time="09:00",
            end_time="12:00",
            is_available=True,
        )
        self.assertEqual(schedule.doctor, self.doctor_a)
        self.assertTrue(schedule.is_available)
