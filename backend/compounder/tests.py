"""Tests for compounder module."""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from compounder.models import Compounder

User = get_user_model()


class CompounderAPITests(TestCase):
    """Tests for compounder API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="Pharmacy")

        # Create compounder user
        self.user = User.objects.create_user(
            username="compounder_a",
            email="compounder_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.PHARMACIST,  # Compounder uses pharmacist role
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.PHARMACIST,
            is_active=True,
        )

        # Create compounder
        self.compounder = Compounder.objects.create(
            name="Mr. Compounder",
            phone="9876543210",
            hospital=self.hospital_a,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_compounders_url(self):
        return f"/api/compounder/?hospital={self.hospital_a.id}"

    def test_list_compounders(self):
        """Test listing compounders."""
        response = self.client.get(self._get_compounders_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Mr. Compounder")

    def test_create_compounder(self):
        """Test creating a compounder."""
        response = self.client.post(
            self._get_compounders_url(),
            {
                "name": "New Compounder",
                "phone": "9999999999",
                "hospital": self.hospital_a.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Compounder")