"""Tests for nurses module."""

from datetime import date, time
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from ipd.models import Admission
from nurses.models import Nurse, NursingAssessment, CareTask, MARAdministration

User = get_user_model()


class NursesAPITests(TestCase):
    """Tests for nurses API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="Nursing")

        # Create nurse user
        self.user = User.objects.create_user(
            username="nurse_a",
            email="nurse_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.NURSE,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.NURSE,
            is_active=True,
        )

        # Create doctor
        self.doctor = Doctor.objects.create(
            name="Dr. Nurse Test",
            specialization="Internal Medicine",
            phone="9876543210",
            email="doc@hospital.com",
            hospital=self.hospital_a,
            department=self.dept,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Nursing Patient",
            age=50,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Create admission
        self.admission = Admission.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital_a,
            admission_type="Emergency",
            admission_date=date.today(),
            diagnosis="Test diagnosis",
            status="Admitted",
        )

        # Create nurse
        self.nurse = Nurse.objects.create(
            name="Nurse Test",
            phone="9876543210",
            email="nurse@hospital.com",
            hospital=self.hospital_a,
            qualification="B.Sc Nursing",
            experience_years=3,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_nurses_url(self):
        return f"/api/nurses/nurses/?hospital={self.hospital_a.id}"

    def _get_assessments_url(self):
        return f"/api/nurses/assessments/?hospital={self.hospital_a.id}"

    def _get_care_tasks_url(self):
        return f"/api/nurses/care-tasks/?hospital={self.hospital_a.id}"

    def _get_mar_url(self):
        return f"/api/nurses/mar/?hospital={self.hospital_a.id}"

    def test_list_nurses(self):
        """Test listing nurses."""
        response = self.client.get(self._get_nurses_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Nurse Test")

    def test_create_nurse(self):
        """Test creating a nurse."""
        response = self.client.post(
            self._get_nurses_url(),
            {
                "name": "New Nurse",
                "phone": "9999999999",
                "email": "newnurse@hospital.com",
                "hospital": self.hospital_a.id,
                "qualification": "GNM",
                "experience_years": 2,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Nurse")

    def test_nursing_assessment(self):
        """Test nursing assessment model."""
        assessment = NursingAssessment.objects.create(
            admission=self.admission,
            nurse=self.nurse,
            assessment_date=date.today(),
            assessment_time=time(10, 0),
            pain_score=5,
            mobility="Limited",
            skin_condition="Intact",
            notes="Patient comfortable",
        )
        self.assertEqual(assessment.admission, self.admission)
        self.assertEqual(assessment.pain_score, 5)

    def test_care_task(self):
        """Test care task model."""
        task = CareTask.objects.create(
            admission=self.admission,
            nurse=self.nurse,
            task_name="Vital signs monitoring",
            frequency="Every 4 hours",
            start_date=date.today(),
            status="Pending",
        )
        self.assertEqual(task.admission, self.admission)
        self.assertEqual(task.status, "Pending")

    def test_mar_administration(self):
        """Test MAR administration model."""
        mar = MARAdministration.objects.create(
            admission=self.admission,
            nurse=self.nurse,
            medication="Paracetamol",
            dosage="500mg",
            route="Oral",
            scheduled_time=time(10, 0),
            administered_time=time(10, 5),
            status="Administered",
        )
        self.assertEqual(mar.admission, self.admission)
        self.assertEqual(mar.status, "Administered")
