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
from laboratory.models import LabTest, SampleCollection, LabResult, ResultVerification
from nurses.models import Nurse

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

        # Create lab test
        self.test = LabTest.objects.create(
            hospital=self.hospital_a,
            patient=self.patient,
            doctor=self.doctor,
            visit=self.visit,
            name="CBC",
            priority="Normal",
            status="Ordered",
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_tests_url(self):
        return f"/api/laboratory/?hospital={self.hospital_a.id}"

    def test_list_lab_tests(self):
        """Test listing lab tests."""
        response = self.client.get(self._get_tests_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "CBC")

    def test_create_lab_test(self):
        """Test creating a lab test."""
        response = self.client.post(
            self._get_tests_url(),
            {
                "patient": self.patient.id,
                "doctor": self.doctor.id,
                "visit": self.visit.id,
                "name": "Blood Glucose",
                "priority": "Normal",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Blood Glucose")

    def test_sample_collection(self):
        """Test sample collection."""
        # Create a nurse for sample collection
        nurse = Nurse.objects.create(
            hospital=self.hospital_a,
            name="Lab Nurse",
            phone="9876543210",
            email="lab.nurse@hospital.com",
            department="Laboratory",
            shift="Morning",
            qualification="BSc Nursing",
            status="Active"
        )
        response = self.client.post(
            f"/api/laboratory/{self.test.id}/collect_sample/",
            {
                "sample_type": "Blood",
                "container_type": "EDTA",
                "sample_id": "SAMP001",
                "collected_by": nurse.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.test.refresh_from_db()
        self.assertEqual(self.test.status, "Collected")

    def test_lab_result(self):
        """Test lab result model."""
        result = LabResult.objects.create(
            lab_test=self.test,
            result_data={"hb": 14.5, "wbc": 8000},
            result_text="Hb: 14.5, WBC: 8000",
            reference_ranges={"hb": "13-17", "wbc": "4000-11000"},
            entered_by=self.user,
        )
        self.assertEqual(result.lab_test, self.test)
        self.assertEqual(result.result_text, "Hb: 14.5, WBC: 8000")