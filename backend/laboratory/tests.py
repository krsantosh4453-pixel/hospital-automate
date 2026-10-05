"""Tests for laboratory module."""

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from encounters.models import Visit
from laboratory.models import LabTest, LabTestCategory, SampleCollection, LabResult

User = get_user_model()


class LaboratoryAPITests(TestCase):
    """Tests for laboratory API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="Laboratory")

        # Create lab staff user
        self.user = User.objects.create_user(
            username="lab_staff",
            email="lab_staff@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.LAB_STAFF,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.LAB_STAFF,
            is_active=True,
        )

        # Create doctor
        self.doctor = Doctor.objects.create(
            name="Dr. Lab",
            specialization="Pathology",
            phone="9876543210",
            email="lab_doc@hospital.com",
            hospital=self.hospital_a,
            department=self.dept,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Lab Patient",
            age=25,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Create visit
        self.visit = Visit.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            status="In Progress",
        )

        # Create test category
        self.category = LabTestCategory.objects.create(
            hospital=self.hospital_a,
            name="Hematology",
        )

        # Create lab test
        self.test = LabTest.objects.create(
            hospital=self.hospital_a,
            category=self.category,
            name="CBC",
            code="CBC001",
            description="Complete Blood Count",
            price="100.00",
            turnaround_hours=2,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_tests_url(self):
        return f"/api/laboratory/tests/?hospital={self.hospital_a.id}"

    def _get_orders_url(self):
        return f"/api/laboratory/orders/?hospital={self.hospital_a.id}"

    def _get_results_url(self):
        return f"/api/laboratory/results/?hospital={self.hospital_a.id}"

    def test_list_lab_tests(self):
        """Test listing lab tests."""
        response = self.client.get(self._get_tests_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "CBC")

    def test_create_lab_order(self):
        """Test creating a lab test order."""
        response = self.client.post(
            self._get_orders_url(),
            {
                "visit": self.visit.id,
                "tests": [self.test.id],
                "priority": "Routine",
                "clinical_notes": "Routine checkup",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["tests"]), 1)

    def test_sample_collection(self):
        """Test sample collection."""
        # First create an order
        order_response = self.client.post(
            self._get_orders_url(),
            {
                "visit": self.visit.id,
                "tests": [self.test.id],
                "priority": "Routine",
            },
            format="json",
        )
        order_id = order_response.data["id"]

        response = self.client.post(
            f"/api/laboratory/orders/{order_id}/collect/",
            {
                "collected_by": "Lab Tech",
                "collection_time": "10:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_lab_result(self):
        """Test lab result model."""
        order_response = self.client.post(
            self._get_orders_url(),
            {
                "visit": self.visit.id,
                "tests": [self.test.id],
                "priority": "Routine",
            },
            format="json",
        )
        order_id = order_response.data["id"]

        result = LabResult.objects.create(
            order_id=order_id,
            test=self.test,
            value="Hb: 14.5, WBC: 8000",
            reference_range="Hb: 13-17, WBC: 4000-11000",
            unit="g/dL, /mm3",
            status="Normal",
            verified_by=self.user,
        )
        self.assertEqual(result.test, self.test)
        self.assertEqual(result.status, "Normal")
