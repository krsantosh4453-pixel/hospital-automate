"""Tests for emergency module."""

from datetime import date, time
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from emergency.models import EmergencyVisit, EmergencyTriage, EmergencyOrder, EmergencyMedication

User = get_user_model()


class EmergencyAPITests(TestCase):
    """Tests for emergency API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="Emergency")

        # Create doctor user for Hospital A
        self.user = User.objects.create_user(
            username="er_doctor",
            email="er_doctor@hospital.com",
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

        self.doctor = Doctor.objects.create(
            name="Dr. Emergency",
            specialization="Emergency Medicine",
            phone="9876543210",
            email="er@hospital.com",
            hospital=self.hospital_a,
            department=self.dept,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="ER Patient",
            age=35,
            gender="Female",
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

    def _get_visits_url(self):
        return f"/api/emergency/emergency-visits/?hospital={self.hospital_a.id}"

    def _get_triage_url(self):
        return f"/api/emergency/triage/?hospital={self.hospital_a.id}"

    def test_create_emergency_visit(self):
        """Test creating an emergency visit."""
        response = self.client.post(
            self._get_visits_url(),
            {
                "patient": self.patient.id,
                "attending_doctor": self.doctor.id,
                "triage_level": "Emergency",
                "remarks": "Chest pain",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertEqual(response.data["triage_level"], "Emergency")

    def test_create_triage(self):
        """Test creating triage assessment."""
        visit = EmergencyVisit.objects.create(
            patient=self.patient,
            attending_doctor=self.doctor,
            hospital=self.hospital_a,
            triage_level="Emergency",
            remarks="Abdominal pain",
        )
        response = self.client.post(
            self._get_triage_url(),
            {
                "visit": visit.id,
                "chief_complaint": "Abdominal pain",
                "vitals": {
                    "temperature": "38.5",
                    "heart_rate": 110,
                    "systolic_bp": 140,
                    "diastolic_bp": 90,
                    "respiratory_rate": 22,
                    "spo2": 95,
                },
                "pain_score": 7,
                "notes": "Severe abdominal pain",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["pain_score"], 7)

    def test_emergency_order(self):
        """Test emergency order model."""
        visit = EmergencyVisit.objects.create(
            patient=self.patient,
            attending_doctor=self.doctor,
            hospital=self.hospital_a,
            triage_level="Emergency",
            remarks="Test",
        )
        order = EmergencyOrder.objects.create(
            visit=visit,
            order_type="Lab",
            description="CBC, BMP",
            status="Ordered",
            ordered_by=self.doctor,
        )
        self.assertEqual(order.visit, visit)
        self.assertEqual(order.order_type, "Lab")

    def test_emergency_medication(self):
        """Test emergency medication model."""
        visit = EmergencyVisit.objects.create(
            patient=self.patient,
            attending_doctor=self.doctor,
            hospital=self.hospital_a,
            triage_level="Emergency",
            remarks="Test",
        )
        med = EmergencyMedication.objects.create(
            visit=visit,
            name="Aspirin",
            dose="325mg",
            route="Oral",
            frequency="Once",
            prescribed_by=self.doctor,
        )
        self.assertEqual(med.visit, visit)
        self.assertEqual(med.name, "Aspirin")