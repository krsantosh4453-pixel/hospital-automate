"""Tests for blood bank module."""

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from bloodbank.models import BloodInventory, BloodRequest, BloodTransfusion

User = get_user_model()


class BloodBankAPITests(TestCase):
    """Tests for blood bank API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="Blood Bank")

        # Create blood bank staff user
        self.user = User.objects.create_user(
            username="bloodbank_a",
            email="bloodbank_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.BLOOD_BANK_STAFF,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.BLOOD_BANK_STAFF,
            is_active=True,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Blood Patient",
            age=30,
            gender="Male",
            phone="9876543210",
            blood_group="A+",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Create blood inventory
        self.inventory = BloodInventory.objects.create(
            hospital=self.hospital_a,
            blood_group="A+",
            component="Whole Blood",
            units_available=10,
            expiry_date=date.today(),
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_inventory_url(self):
        return f"/api/bloodbank/inventory/?hospital={self.hospital_a.id}"

    def _get_requests_url(self):
        return f"/api/bloodbank/requests/?hospital={self.hospital_a.id}"

    def test_list_inventory(self):
        """Test listing blood inventory."""
        response = self.client.get(self._get_inventory_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["blood_group"], "A+")

    def test_create_blood_request(self):
        """Test creating a blood request."""
        response = self.client.post(
            self._get_requests_url(),
            {
                "patient": self.patient.id,
                "blood_group": "A+",
                "component": "Packed Red Cells",
                "units_requested": 2,
                "urgency": "Urgent",
                "reason": "Surgery",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["units_requested"], 2)

    def test_blood_transfusion(self):
        """Test blood transfusion model."""
        request = BloodRequest.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            blood_group="A+",
            component="Packed Red Cells",
            units_requested=2,
            urgency="Urgent",
            status="Approved",
        )
        transfusion = BloodTransfusion.objects.create(
            request=request,
            units_transfused=2,
            transfusion_date=date.today(),
            reaction="None",
        )
        self.assertEqual(transfusion.request, request)
        self.assertEqual(transfusion.units_transfused, 2)
        # Check inventory updated
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.units_available, 8)
