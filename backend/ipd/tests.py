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
from ipd.models import Admission, BedAllocation, DischargePlan, DischargeSummary
from ipd import discharge as discharge_service
from billing.services import record_payment

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
            room_number="101",
            room_type="General",
        )
        self.bed = Bed.objects.create(
            room=self.room,
            bed_number="A",
            status="Available",
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
            user=self.user,
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
                "admitting_doctor": self.doctor.id,
                "reason": "Acute appendicitis",
                "hospital": self.hospital_a.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertEqual(response.data["status"], "Admitted")

    def _get_admission_action_url(self, pk, action):
        return f"/api/ipd/admissions/{pk}/{action}/?hospital={self.hospital_a.id}"

    def test_bed_allocation(self):
        """Test bed allocation via admission action."""
        admission = Admission.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            admitting_doctor=self.doctor,
            reason="Test diagnosis",
            status="Admitted",
        )
        response = self.client.post(
            self._get_admission_action_url(admission.id, "allocate_bed"),
            {
                "bed_id": self.bed.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, "Occupied")

    def test_discharge_summary(self):
        """Test discharge summary."""
        admission = Admission.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            admitting_doctor=self.doctor,
            reason="Test diagnosis",
            status="Admitted",
        )
        BedAllocation.objects.create(
            admission=admission,
            bed=self.bed,
            allocated_at=time(10, 0),
        )
        self.bed.status = "Occupied"
        self.bed.save()

        summary = DischargeSummary.objects.create(
            admission=admission,
            summary="Patient recovered well",
            authorized_doctor=self.doctor,
        )
        self.assertEqual(summary.admission, admission)
        self.assertFalse(summary.finalized)
        
        # Test initiate discharge action
        response = self.client.post(
            self._get_admission_action_url(admission.id, "initiate_discharge"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        admission.refresh_from_db()
        self.assertEqual(admission.status, "Discharge Initiated")
        
        # Discharge cannot complete until the summary is finalized.
        response = self.client.post(
            self._get_admission_action_url(admission.id, "complete_discharge"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        summary.finalized = True
        summary.save()

        # Still refused: the checklist and the final bill are outstanding.
        response = self.client.post(
            self._get_admission_action_url(admission.id, "complete_discharge"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        DischargePlan.objects.create(
            admission=admission,
            medications_reconciled=True,
            patient_counselled=True,
            follow_up_arranged=True,
            documents_handed_over=True,
        )
        invoice = discharge_service.create_final_bill(admission, "1500")
        record_payment(invoice, invoice.total_amount)

        # Test complete discharge action
        response = self.client.post(
            self._get_admission_action_url(admission.id, "complete_discharge"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        admission.refresh_from_db()
        self.assertEqual(admission.status, "Discharged")
        self.bed.refresh_from_db()
        self.assertEqual(self.bed.status, "Available")
