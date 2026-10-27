"""Dashboard statistics endpoints (synthetic data only)."""

from datetime import time

from django.test import TestCase
from rest_framework.test import APIClient

from config.hospital_time import hospital_today

from appointments.models import Appointment
from doctors.models import Doctor
from hospital.models import Hospital
from laboratory.models import LabTest
from patients.models import Patient
from users.models import StaffRole

from .test_tenant_isolation import make_staff


class HomeStatsTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Stats Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        self.user, _ = make_staff("stats_admin", self.hospital)
        Patient.objects.create(name="Synthetic Stats Patient", age=40, gender="Male", phone="9000000077", hospital=self.hospital)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)

    def test_summary_endpoint_returns_counts(self):
        # Regression: this view used Sum without importing it (NameError -> 500).
        response = self.client.get(f"/api/home/stats/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["patients"], 1)
        self.assertEqual(response.data["total_revenue"], 0.0)

    def test_detail_endpoint_used_by_dashboard(self):
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["statistics"]["patients"]["total"], 1)
        self.assertEqual(response.data["recent_patients"][0]["name"], "Synthetic Stats Patient")

    def test_lab_count_uses_the_test_hospital_not_the_patient_registration(self):
        # R-07: a shared patient's tests at another hospital are not this hospital's.
        patient = Patient.objects.get(hospital=self.hospital)
        LabTest.objects.create(name="Synthetic CBC here", patient=patient, hospital=self.hospital)
        LabTest.objects.create(name="Synthetic CBC elsewhere", patient=patient, hospital=self.other)
        response = self.client.get(f"/api/home/stats/detail/?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["statistics"]["laboratory"]["total"], 1)

    def test_other_hospital_is_refused(self):
        for url in ("/api/home/stats/", "/api/home/stats/detail/"):
            response = self.client.get(f"{url}?hospital={self.other.id}")
            self.assertEqual(response.status_code, 403, url)


class DoctorHomeStatsTests(TestCase):
    """A Doctor's home counts cover only the patients in their own care."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Doctor Stats", is_active=True)
        self.doctor_user, _ = make_staff("stats_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.admin_user, _ = make_staff("stats_admin_2", self.hospital)
        colleague_user, _ = make_staff("stats_colleague", self.hospital, role=StaffRole.DOCTOR)
        doctor = Doctor.objects.create(hospital=self.hospital, user=self.doctor_user, name="Dr Own",
                                       specialization="General", phone="9000000901")
        colleague = Doctor.objects.create(hospital=self.hospital, user=colleague_user, name="Dr Else",
                                          specialization="General", phone="9000000902")
        today = hospital_today()  # the dashboard counts the hospital's day
        for name, phone, who in (("Synthetic Own", "9000000903", doctor), ("Synthetic Else", "9000000904", colleague)):
            patient = Patient.objects.create(name=name, age=40, gender="Male", phone=phone, hospital=self.hospital)
            Appointment.objects.create(hospital=self.hospital, patient=patient, doctor=who,
                                       appointment_date=today, appointment_time=time(10, 0), status="Scheduled")

    def stats(self, user, url="/api/home/stats/detail/"):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        response = client.get(f"{url}?hospital={self.hospital.id}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.data

    def test_doctor_dashboard_counts_only_their_patients(self):
        data = self.stats(self.doctor_user)
        stats = data["statistics"]
        self.assertEqual(stats["patients"]["total"], 1)
        self.assertEqual(stats["appointments"]["today"], 1)
        self.assertEqual(stats["appointments"]["pending"], 1)
        self.assertEqual([p["name"] for p in data["recent_patients"]], ["Synthetic Own"])

    def test_doctor_summary_counts_only_their_patients(self):
        data = self.stats(self.doctor_user, "/api/home/stats/")
        self.assertEqual(data["patients"], 1)
        self.assertEqual(data["today_appointments"], 1)

    def test_admin_still_counts_the_whole_hospital(self):
        stats = self.stats(self.admin_user)["statistics"]
        self.assertEqual(stats["patients"]["total"], 2)
        self.assertEqual(stats["appointments"]["today"], 2)
