"""Tests for hospital module."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department, Ward, Room, Bed
from users.models import StaffProfile, StaffHospitalMembership, StaffRole

User = get_user_model()


class HospitalAPITests(TestCase):
    """Tests for hospital API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(
            name="Hospital A",
            address="123 Main St",
            city="City A",
            phone="1234567890",
            email="hospital_a@test.com",
            is_active=True,
        )
        self.hospital_b = Hospital.objects.create(
            name="Hospital B",
            address="456 Oak Ave",
            city="City B",
            phone="0987654321",
            email="hospital_b@test.com",
            is_active=True,
        )

        # Create superuser for hospital management
        self.user = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@test.com",
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

        self.client.force_authenticate(user=self.user)

    def _get_hospitals_url(self):
        return "/api/hospital/hospitals/"

    def _get_departments_url(self):
        return f"/api/hospital/departments/?hospital={self.hospital_a.id}"

    def _get_wards_url(self):
        return f"/api/hospital/wards/?hospital={self.hospital_a.id}"

    def test_list_hospitals(self):
        """Test listing hospitals (superuser sees all)."""
        response = self.client.get(self._get_hospitals_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        names = [h["name"] for h in data]
        self.assertIn("Hospital A", names)
        self.assertIn("Hospital B", names)

    def test_create_hospital(self):
        """Test creating a hospital."""
        response = self.client.post(
            self._get_hospitals_url(),
            {
                "name": "New Hospital",
                "address": "789 New St",
                "city": "New City",
                "phone": "1112223333",
                "email": "new@hospital.com",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Hospital")

    def test_create_department(self):
        """Test creating a department."""
        response = self.client.post(
            self._get_departments_url(),
            {
                "name": "New Department",
                "hospital": self.hospital_a.id,
                "description": "Test department",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Department")
        self.assertEqual(response.data["hospital"], self.hospital_a.id)

    def test_create_ward(self):
        """Test creating a ward."""
        response = self.client.post(
            self._get_wards_url(),
            {
                "name": "New Ward",
                "hospital": self.hospital_a.id,
                "ward_type": "ICU",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Ward")
        self.assertEqual(response.data["ward_type"], "ICU")

    def test_bed_management(self):
        """Test bed model and management."""
        dept = Department.objects.create(hospital=self.hospital_a, name="ICU")
        ward = Ward.objects.create(hospital=self.hospital_a, name="ICU Ward", ward_type="ICU")
        room = Room.objects.create(ward=ward, name="ICU-1", room_type="ICU")
        bed = Bed.objects.create(room=room, number="1", bed_type="ICU", is_occupied=False)
        
        self.assertEqual(bed.room, room)
        self.assertFalse(bed.is_occupied)
        
        # Occupy bed
        bed.is_occupied = True
        bed.save()
        bed.refresh_from_db()
        self.assertTrue(bed.is_occupied)
