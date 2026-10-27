"""Department staff see only their department's OPD queue (synthetic data only)."""

from django.test import TestCase
from rest_framework.test import APIClient

from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import QueueToken, Visit
from hospital.models import Department, Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffHospitalMembership, StaffRole

from .test_tenant_isolation import make_staff

TOKENS = "/api/encounters/queue-tokens/"
CALL_NEXT = "/api/encounters/queue-tokens/call-next/"


def ids(response):
    body = response.json()
    rows = body["results"] if isinstance(body, dict) and "results" in body else body
    return {row["id"] for row in rows}


class DepartmentQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Dept Queue", is_active=True)
        cls.cardio = Department.objects.create(hospital=cls.hospital, name="Cardiology")
        cls.ortho = Department.objects.create(hospital=cls.hospital, name="Orthopaedics")
        cls.tokens = {}
        for number, (key, dept) in enumerate((("ortho", cls.ortho), ("cardio", cls.cardio), ("none", None)), start=1):
            doctor = Doctor.objects.create(hospital=cls.hospital, name=f"Dr {key}", specialization="General",
                                           phone=f"90000020{number:02d}", department=dept)
            patient = Patient.objects.create(name=f"Synthetic {key}", age=30, gender="Male",
                                             phone=f"90000021{number:02d}", hospital=cls.hospital)
            PatientHospital.objects.create(patient=patient, hospital=cls.hospital, uhid=f"DQ-{number}")
            visit = Visit.objects.create(hospital=cls.hospital, patient=patient, doctor=doctor)
            cls.tokens[key] = QueueToken.objects.create(
                hospital=cls.hospital, visit=visit, patient=patient, doctor=doctor,
                token_date=hospital_today(), token_number=number,
            )
        cls.desk_cardio = cls.staff("dq_desk_cardio", StaffRole.RECEPTIONIST, cls.cardio)
        cls.desk_main = cls.staff("dq_desk_main", StaffRole.RECEPTIONIST, None)
        cls.nurse_cardio = cls.staff("dq_nurse_cardio", StaffRole.NURSE, cls.cardio)
        cls.admin = cls.staff("dq_admin", StaffRole.ADMIN, cls.cardio)

    @classmethod
    def staff(cls, username, role, department):
        user, profile = make_staff(username, cls.hospital, role=role)
        StaffHospitalMembership.objects.filter(staff=profile, hospital=cls.hospital).update(department=department)
        return user

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        return client

    def listed(self, user):
        resp = self.client_for(user).get(TOKENS, {"hospital": self.hospital.id})
        self.assertEqual(resp.status_code, 200, resp.content)
        return ids(resp)

    def token_ids(self, *keys):
        return {self.tokens[k].id for k in keys}

    def test_department_receptionist_sees_own_and_unassigned_tokens(self):
        self.assertEqual(self.listed(self.desk_cardio), self.token_ids("cardio", "none"))

    def test_receptionist_without_department_sees_the_whole_queue(self):
        self.assertEqual(self.listed(self.desk_main), self.token_ids("ortho", "cardio", "none"))

    def test_department_nurse_sees_own_and_unassigned_tokens(self):
        self.assertEqual(self.listed(self.nurse_cardio), self.token_ids("cardio", "none"))

    def test_department_nurse_sees_only_their_departments_opd_patients(self):
        resp = self.client_for(self.nurse_cardio).get("/api/patients/", {"hospital": self.hospital.id})
        patients = ids(resp)
        self.assertIn(self.tokens["cardio"].patient_id, patients)
        self.assertIn(self.tokens["none"].patient_id, patients)
        self.assertNotIn(self.tokens["ortho"].patient_id, patients)

    def test_admin_sees_the_whole_queue_even_with_a_department(self):
        self.assertEqual(self.listed(self.admin), self.token_ids("ortho", "cardio", "none"))

    def test_other_departments_token_cannot_be_opened(self):
        resp = self.client_for(self.desk_cardio).get(f"{TOKENS}{self.tokens['ortho'].id}/", {"hospital": self.hospital.id})
        self.assertEqual(resp.status_code, 404)

    def test_call_next_stays_in_the_department(self):
        resp = self.client_for(self.desk_cardio).post(f"{CALL_NEXT}?hospital={self.hospital.id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["id"], self.tokens["cardio"].id)
        self.tokens["ortho"].refresh_from_db()
        self.assertEqual(self.tokens["ortho"].status, QueueToken.Status.WAITING)

    def test_home_queue_count_follows_the_department(self):
        resp = self.client_for(self.desk_cardio).get(f"/api/home/stats/?hospital={self.hospital.id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["waiting_queue"], 2)
