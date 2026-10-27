"""Tests for clinical module."""

from datetime import date, time
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from encounters.models import Visit
from clinical.models import (
    VitalSign, ClinicalNote, Diagnosis, Prescription, PrescriptionItem,
    ServiceOrder, Procedure
)

User = get_user_model()


class ClinicalAPITests(TestCase):
    """Tests for clinical API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="General")

        # Create doctor user for Hospital A
        self.user = User.objects.create_user(
            username="doctor_a",
            email="doctor_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.DOCTOR,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.DOCTOR,
            department=self.dept,
            is_active=True,
        )

        # Create doctor
        self.doctor = Doctor.objects.create(
            user=self.user,
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

        # Create visit
        self.visit = Visit.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            status="In Progress",
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_vitals_url(self):
        return f"/api/clinical/vitals/?hospital={self.hospital_a.id}"

    def _get_notes_url(self):
        return f"/api/clinical/clinical-notes/?hospital={self.hospital_a.id}"

    def _get_diagnoses_url(self):
        return f"/api/clinical/diagnoses/?hospital={self.hospital_a.id}"

    def _get_prescriptions_url(self):
        return f"/api/clinical/prescriptions/?hospital={self.hospital_a.id}"

    def test_create_vital_signs(self):
        """Test creating vital signs."""
        response = self.client.post(
            self._get_vitals_url(),
            {
                "visit": self.visit.id,
                "temperature": "37.0",
                "heart_rate": 72,
                "systolic_bp": 120,
                "diastolic_bp": 80,
                "respiratory_rate": 16,
                "spo2": 98,
                "weight": "70.5",
                "height": "175.0",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["visit"], self.visit.id)
        self.assertEqual(Decimal(response.data["temperature"]), Decimal("37.0"))

    def test_create_clinical_note(self):
        """Test creating a clinical note."""
        response = self.client.post(
            self._get_notes_url(),
            {
                "visit": self.visit.id,
                "note": "Patient presents with...",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["note"], "Patient presents with...")

    def test_create_diagnosis(self):
        """Test creating a diagnosis."""
        response = self.client.post(
            self._get_diagnoses_url(),
            {
                "visit": self.visit.id,
                "name": "Essential hypertension",
                "icd10_code": "I10",
                "diagnosis_type": "Provisional",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Essential hypertension")

    def test_create_prescription(self):
        """Test creating a prescription."""
        response = self.client.post(
            self._get_prescriptions_url(),
            {
                "visit": self.visit.id,
                "patient": self.patient.id,
                "doctor": self.doctor.id,
                "hospital": self.hospital_a.id,
                "status": "Confirmed",
                "items": [
                    {
                        "name": "Amlodipine",
                        "dosage": "5mg",
                        "frequency": "Once daily",
                        "duration": "30 days",
                        "quantity": 30,
                        "instructions": "Take in morning",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "Confirmed")

    def test_list_prescriptions(self):
        """Test listing prescriptions."""
        prescription = Prescription.objects.create(
            visit=self.visit,
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            status="Active",
        )
        PrescriptionItem.objects.create(
            prescription=prescription,
            name="Test Med",
            dosage="10mg",
            frequency="Daily",
            duration="7 days",
            quantity=7,
        )
        response = self.client.get(self._get_prescriptions_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)

    def test_service_order(self):
        """Test service order model."""
        order = ServiceOrder.objects.create(
            visit=self.visit,
            service_name="X-Ray Chest",
            quantity=1,
            status="Pending",
        )
        self.assertEqual(order.visit, self.visit)
        self.assertEqual(order.status, "Pending")

    def test_procedure(self):
        """Test procedure model."""
        proc = Procedure.objects.create(
            visit=self.visit,
            name="Wound Dressing",
            description="Clean and dress wound",
            status="Completed",
        )
        self.assertEqual(proc.visit, self.visit)
        self.assertEqual(proc.status, "Completed")