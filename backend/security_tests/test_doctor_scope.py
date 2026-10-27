"""A Doctor sees only the patients in their care (synthetic data only)."""

from datetime import date, time

from django.test import TestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from clinical.models import Allergy
from doctors.models import Doctor
from emergency.models import EmergencyVisit
from encounters.models import QueueToken, Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffHospitalMembership, StaffRole

from .test_tenant_isolation import make_staff

PATIENTS = "/api/patients/"
ALLERGIES = "/api/clinical/allergies/"
APPOINTMENTS = "/api/appointments/"
CALL_NEXT = "/api/encounters/queue-tokens/call-next/"


def ids(response):
    body = response.json()
    rows = body["results"] if isinstance(body, dict) and "results" in body else body
    return {row["id"] for row in rows}


class DoctorScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Scope A", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Scope B", is_active=True)
        cls.doctor_user, cls.doctor_profile = make_staff("scope_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.colleague_user, _ = make_staff("scope_colleague", cls.hospital, role=StaffRole.DOCTOR)
        cls.admin_user, _ = make_staff("scope_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.doctor = Doctor.objects.create(
            hospital=cls.hospital, user=cls.doctor_user, name="Dr Mine", specialization="General", phone="9000000701",
        )
        cls.colleague = Doctor.objects.create(
            hospital=cls.hospital, user=cls.colleague_user, name="Dr Other", specialization="General", phone="9000000702",
        )

        cls.mine = cls.make_patient("Synthetic Mine", "9000000711")
        cls.theirs = cls.make_patient("Synthetic Theirs", "9000000712")
        cls.emergency = cls.make_patient("Synthetic Emergency", "9000000713")
        Appointment.objects.create(
            hospital=cls.hospital, patient=cls.mine, doctor=cls.doctor,
            appointment_date=date(2026, 11, 2), appointment_time=time(10, 0),
        )
        Appointment.objects.create(
            hospital=cls.hospital, patient=cls.theirs, doctor=cls.colleague,
            appointment_date=date(2026, 11, 2), appointment_time=time(10, 0),
        )
        EmergencyVisit.objects.create(
            hospital=cls.hospital, patient=cls.emergency, visit_number="SYN-ER-1", status="Waiting",
        )
        cls.my_allergy = Allergy.objects.create(hospital=cls.hospital, patient=cls.mine, name="Penicillin")
        cls.their_allergy = Allergy.objects.create(hospital=cls.hospital, patient=cls.theirs, name="Latex")

    @classmethod
    def make_patient(cls, name, phone):
        patient = Patient.objects.create(name=name, age=40, gender="Female", phone=phone, hospital=cls.hospital)
        PatientHospital.objects.create(patient=patient, hospital=cls.hospital, uhid=f"S-{phone}")
        return patient

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        return client

    def get(self, user, url):
        return self.client_for(user).get(url, {"hospital": self.hospital.id})

    def test_doctor_lists_only_their_patients(self):
        listed = ids(self.get(self.doctor_user, PATIENTS))
        self.assertIn(self.mine.id, listed)
        self.assertNotIn(self.theirs.id, listed)

    def test_doctor_cannot_open_another_doctors_patient(self):
        url = f"{PATIENTS}{self.theirs.id}/"
        self.assertEqual(self.get(self.doctor_user, url).status_code, 404)
        self.assertEqual(self.get(self.doctor_user, f"{PATIENTS}{self.mine.id}/").status_code, 200)

    def test_clinical_rows_follow_the_patient(self):
        listed = ids(self.get(self.doctor_user, ALLERGIES))
        self.assertEqual(listed, {self.my_allergy.id})
        self.assertEqual(ids(self.get(self.doctor_user, APPOINTMENTS)), set(
            Appointment.objects.filter(patient=self.mine).values_list("id", flat=True)
        ))

    def test_unassigned_emergency_patients_stay_visible(self):
        self.assertIn(self.emergency.id, ids(self.get(self.doctor_user, PATIENTS)))

    def test_admin_still_sees_every_patient(self):
        listed = ids(self.get(self.admin_user, PATIENTS))
        self.assertTrue({self.mine.id, self.theirs.id} <= listed)

    def test_doctor_cannot_write_for_another_doctors_patient(self):
        client = self.client_for(self.doctor_user)
        body = {"hospital": self.hospital.id, "name": "Dust", "patient": self.theirs.id}
        self.assertIn(client.post(ALLERGIES, body, format="json").status_code, (400, 403))
        self.assertFalse(Allergy.objects.filter(name="Dust").exists())
        ok = client.post(ALLERGIES, {**body, "patient": self.mine.id}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)

    def test_write_through_a_visit_is_checked_too(self):
        visit = Visit.objects.create(hospital=self.hospital, patient=self.theirs, doctor=self.colleague)
        resp = self.client_for(self.doctor_user).post(
            "/api/clinical/vitals/", {"hospital": self.hospital.id, "visit": visit.id, "heart_rate": 70}, format="json",
        )
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_any_doctor_can_register_an_emergency(self):
        resp = self.client_for(self.doctor_user).post(
            "/api/emergency/emergency-visits/",
            {"hospital": self.hospital.id, "patient": self.theirs.id, "triage_level": "Emergency"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIn(self.theirs.id, ids(self.get(self.doctor_user, PATIENTS)))

    def test_doctor_profile_links_to_the_login_with_the_same_email(self):
        login, _ = make_staff("scope_new_doctor", self.hospital, role=StaffRole.DOCTOR)
        login.email = "new.doctor@example.test"
        login.save(update_fields=["email"])
        resp = self.client_for(self.admin_user).post("/api/doctors/", {
            "hospital": self.hospital.id, "name": "Dr New", "specialization": "General",
            "phone": "9000000715", "email": "New.Doctor@example.test",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Doctor.objects.get(pk=resp.json()["id"]).user, login)

    def test_doctor_role_elsewhere_does_not_limit_other_roles(self):
        StaffHospitalMembership.objects.create(
            staff=self.doctor_profile, hospital=self.other_hospital, role=StaffRole.ADMIN, is_active=True,
        )
        stranger = Patient.objects.create(
            name="Synthetic B", age=30, gender="Male", phone="9000000714", hospital=self.other_hospital,
        )
        PatientHospital.objects.create(patient=stranger, hospital=self.other_hospital, uhid="B-SCOPE")
        resp = self.client_for(self.doctor_user).get(PATIENTS, {"hospital": self.other_hospital.id})
        self.assertIn(stranger.id, ids(resp))

    def test_call_next_only_calls_the_doctors_own_tokens(self):
        def token(patient, doctor, number):
            visit = Visit.objects.create(hospital=self.hospital, patient=patient, doctor=doctor)
            return QueueToken.objects.create(
                hospital=self.hospital, visit=visit, patient=patient, doctor=doctor,
                token_date=date.today(), token_number=number,
            )

        theirs = token(self.theirs, self.colleague, 1)
        mine = token(self.mine, self.doctor, 2)
        resp = self.client_for(self.doctor_user).post(f"{CALL_NEXT}?hospital={self.hospital.id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["id"], mine.id)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, QueueToken.Status.WAITING)
