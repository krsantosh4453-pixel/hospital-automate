"""Tests for IPD (Inpatient Department) module."""

from datetime import date, time
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department, Ward, Room, Bed
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from ipd.models import Admission, BedAllocation, DischargeSummary

User = get_user_model()


class IPDAPITests(TestCase):
    """Tests for IPD API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="General")

        self.ward = Ward.objects.create(
            hospital=self.hospital_a,
            name="General Ward",
            ward_type="General",
        )
        self.room = Room.objects.create(
            ward=self.ward,
            number="101",
            room_type="General",
        )
        self.bed = Bed.objects.create(
            room=self.room,
            number="A",
            bed_type="General",
            is_occupied=False,
        )

        # Create doctor
        self.user = User.objects.create_user(
            username="doctor_ipd",
            email="doctor_ipd@hospital.com",
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
            name="Dr. IPD",
            specialization="Internal Medicine",
            phone="9876543210",
            email="doctor@hospital.com",
            hospital=self.hospital_a,
            department=self.dept,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="IPD Patient",
            age=45,
            gender="Male",
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

    def _get_admissions_url(self):
        return f"/api/ipd/admissions/?hospital={self.hospital_a.id}"

    def _get_bed_allocations_url(self):
        return f"/api/ipd/bed-allocations/?hospital={self.hospital_a.id}"

    def test_create_admission(self):
        """Test creating an admission."""
        response = self.client.post(
            self._get_admissions_url(),
            {
                "patient": self.patient.id,
                "doctor": self.doctor.id,
                "admission_type": "Emergency",
                "admission_date": date.today().isoformat(),
                "diagnosis": "Acute appendicitis",
                "ward": self.ward.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertEqual(response.data["status"], "Admitted")

    def test_bed_allocation(self):
        """Test bed allocation."""
        admission = Admission.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            admission_type="Emergency",
            admission_date=date.today(),
            diagnosis="Test diagnosis",
            ward=self.ward,
            status="Admitted",
        )
        response = self.client.post(
            self._get_bed_allocations_url(),
            {
                "admission": admission.id,
                "bed": self.bed.id,
                "allocated_at": time(10, 0).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.bed.refresh_from_db()
        self.assertTrue(self.bed.is_occupied)

    def test_discharge_summary(self):
        """Test discharge summary."""
        admission = Admission.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            admission_type="Planned",
            admission_date=date.today(),
            diagnosis="Test diagnosis",
            ward=self.ward,
            status="Admitted",
        )
        BedAllocation.objects.create(
            admission=admission,
            bed=self.bed,
            allocated_at=time(10, 0),
        )
        self.bed.is_occupied = True
        self.bed.save()

        summary = DischargeSummary.objects.create(
            admission=admission,
            discharge_date=date.today(),
            discharge_time=time(14, 0),
            discharge_type="Recovered",
            summary="Patient recovered well",
            follow_up_instructions="Follow up in 1 week",
            created_by=self.user,
        )
        self.assertEqual(summary.admission, admission)
        self.assertEqual(summary.discharge_type, "Recovered")
        admission.refresh_from_db()
        self.assertEqual(admission.status, "Discharged")
        self.bed.refresh_from_db()
        self.assertFalse(self.bed.is_occupied)
