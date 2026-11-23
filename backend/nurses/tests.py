"""Tests for nurses module."""

from datetime import date, time, timedelta
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from doctors.models import Doctor
from ipd.models import Admission
from nurses.models import Nurse, NursingAssessment, CareTask, MAR, MARAdministration
from clinical.models import Prescription, PrescriptionItem

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
            hospital=self.hospital_a,
            experience="5 years",
            availability="Full time",
            status="Available",
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
            admitting_doctor=self.doctor,
            hospital=self.hospital_a,
            reason="Emergency admission",
            status="Admitted",
        )

        # Create nurse
        self.nurse = Nurse.objects.create(
            name="Nurse Test",
            phone="9876543210",
            email="nurse@hospital.com",
            hospital=self.hospital_a,
            qualification="B.Sc Nursing",
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
            hospital=self.hospital_a,
            patient=self.patient,
            assessment_type="Shift",
            pain_score=5,
            mobility_status="Limited",
            skin_condition="Intact",
            plan_of_care="Patient comfortable",
        )
        self.assertEqual(assessment.admission, self.admission)
        self.assertEqual(assessment.pain_score, 5)

    def test_care_task(self):
        """Test care task model."""
        task = CareTask.objects.create(
            admission=self.admission,
            assigned_nurse=self.nurse,
            hospital=self.hospital_a,
            patient=self.patient,
            task_type="Vitals",
            description="Vital signs monitoring",
            priority="Routine",
            status="Pending",
            scheduled_at=timezone.now(),
        )
        self.assertEqual(task.admission, self.admission)
        self.assertEqual(task.status, "Pending")

    def test_mar_administration(self):
        """A MAR line holds scheduled doses, due until a nurse records the outcome."""
        prescription = Prescription.objects.create(hospital=self.hospital_a, patient=self.patient)
        item = PrescriptionItem.objects.create(prescription=prescription, name="Ceftriaxone", quantity=2)
        mar = MAR.objects.create(
            patient=self.patient, admission=self.admission, hospital=self.hospital_a,
            prescription=prescription, prescription_item=item, medicine_name="Ceftriaxone",
            dose="1 g", route="IV", frequency="BD", start_date=date.today(),
        )
        now = timezone.now()
        evening = MARAdministration.objects.create(mar=mar, scheduled_time=now + timedelta(hours=12))
        morning = MARAdministration.objects.create(mar=mar, scheduled_time=now)

        self.assertEqual(morning.status, MARAdministration.SCHEDULED)
        self.assertIsNone(morning.administered_time)
        self.assertEqual(list(mar.administrations.all()), [morning, evening])
        self.assertEqual(list(item.mar_records.all()), [mar])

        morning.status = MARAdministration.ADMINISTERED
        morning.administered_time = now
        morning.administered_by = self.nurse
        morning.recorded_by = self.user
        morning.dose_given, morning.route_given = "1 g", "IV"
        morning.save()
        morning.refresh_from_db()
        self.assertEqual(morning.status, "Administered")
        self.assertEqual(morning.administered_by, self.nurse)
        self.assertEqual(list(self.nurse.mar_administrations.all()), [morning])
        self.assertEqual(str(mar), f"MAR: Ceftriaxone for {self.patient.name}")


class MAROrderedByNameTests(TestCase):
    """Final E2E finding 1: the ward MAR showed "Ordered by: demo.doctor1" (the login)."""

    def setUp(self):
        from security_tests.test_tenant_isolation import make_staff, put_in_care

        self.hospital = Hospital.objects.create(name="Synthetic MAR Name Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        self.doctor_user, _ = make_staff("mar.name.doctor", self.hospital, role=StaffRole.DOCTOR)
        self.nurse_user, _ = make_staff("mar.name.nurse", self.hospital, role=StaffRole.NURSE)
        self.patient = Patient.objects.create(name="Synthetic MAR Patient", age=50, gender="Male",
                                              phone="9000004401", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="MN-1")
        put_in_care(self.doctor_user, self.hospital, self.patient)
        self.admission = Admission.objects.create(patient=self.patient, hospital=self.hospital, status="Admitted")
        self.rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        self.item = PrescriptionItem.objects.create(prescription=self.rx, name="Synthetic", quantity=1)
        self.client = APIClient()
        self.client.force_authenticate(self.nurse_user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def order(self, ordered_by):
        return MAR.objects.create(patient=self.patient, admission=self.admission, hospital=self.hospital,
                                  prescription=self.rx, prescription_item=self.item, medicine_name="Synthetic",
                                  dose="1", route="Oral", frequency="OD", start_date=date.today(),
                                  ordered_by=ordered_by)

    def names(self):
        rows = self.client.get(f"/api/nurses/mar/?admission={self.admission.id}").json()
        rows = rows.get("results", rows) if isinstance(rows, dict) else rows
        return [r["ordered_by_name"] for r in rows]

    def test_doctor_profile_name_is_shown_not_the_login(self):
        # make_staff gives a doctor a profile; name it as the hospital records it.
        Doctor.objects.filter(user=self.doctor_user, hospital=self.hospital).update(name="Dr Synthetic Mehta")
        Doctor.objects.create(user=self.doctor_user, hospital=self.other, name="Dr Elsewhere Name",
                              specialization="", phone="")
        self.order(self.doctor_user)
        self.assertEqual(self.names(), ["Dr Synthetic Mehta"])  # this hospital's profile

    def test_without_a_doctor_profile_the_account_name_then_username(self):
        Doctor.objects.filter(user=self.doctor_user).delete()
        self.order(self.doctor_user)
        self.assertEqual(self.names(), ["mar.name.doctor"])
        self.doctor_user.first_name, self.doctor_user.last_name = "Synthetic", "Account"
        self.doctor_user.save()
        self.assertEqual(self.names(), ["Synthetic Account"])

    def test_an_order_without_an_orderer_does_not_fail(self):
        self.order(None)
        self.assertEqual(self.names(), [""])


class WardVitalsValidationTests(TestCase):
    """Ward vitals had no server-side checks; the app was the only guard."""

    def setUp(self):
        from security_tests.test_tenant_isolation import make_staff, put_in_care

        self.hospital = Hospital.objects.create(name="Synthetic Ward Vitals Hospital", is_active=True)
        self.nurse_user, _ = make_staff("ward.vitals.nurse", self.hospital, role=StaffRole.NURSE)
        Nurse.objects.filter(user=self.nurse_user).update(name="Nurse Synthetic") if Nurse.objects.filter(
            user=self.nurse_user).exists() else None
        self.patient = Patient.objects.create(name="Synthetic Vitals Patient", age=50, gender="Male",
                                              phone="9000004501", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="WV-1")
        put_in_care(self.nurse_user, self.hospital, self.patient)
        self.admission = Admission.objects.create(patient=self.patient, hospital=self.hospital, status="Admitted")
        self.client = APIClient()
        self.client.force_authenticate(self.nurse_user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def post(self, vitals):
        return self.client.post("/api/nurses/assessments/", {
            "hospital": self.hospital.id, "patient": self.patient.id, "admission": self.admission.id,
            "assessment_type": "Focused", "vitals": vitals}, format="json")

    def test_valid_readings_are_stored_exactly_as_sent(self):
        for temperature in ("37.1", "36.9", "38.5", "37"):
            with self.subTest(temperature=temperature):
                response = self.post({"temperature": temperature, "bp": "120/80", "pulse": "72",
                                      "spo2": "98", "respiratory_rate": "16"})
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
                self.assertEqual(NursingAssessment.objects.latest("id").vitals["temperature"], temperature)

    def test_empty_values_mean_not_measured(self):
        response = self.post({"temperature": "37.2", "bp": "", "pulse": "", "spo2": "", "respiratory_rate": ""})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

    def test_invalid_readings_are_refused_and_nothing_is_saved(self):
        for vitals in ({"temperature": "abc"}, {"temperature": "-1"}, {"temperature": "37.123"},
                       {"temperature": "1000"}, {"pulse": "72.5"}, {"spo2": "101"}, {"bp": "120/"},
                       {"bp": "120"}, {"bp": "120/80.5"}, {"pulse": True}, {"heart_rate": "80"}):
            with self.subTest(vitals=vitals):
                response = self.post(vitals)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertFalse(NursingAssessment.objects.exists())

