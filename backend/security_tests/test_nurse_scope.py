"""A Nurse sees only the patients of today's ward/shift duty (synthetic data only)."""

from datetime import timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import Allergy
from config.hospital_time import hospital_today
from doctors.models import Doctor
from emergency.models import EmergencyVisit
from encounters.models import QueueToken, Visit
from hospital.models import Bed, Hospital, Room, Ward
from ipd.models import Admission, BedAllocation
from nurses.models import Nurse, NurseWardAssignment, PatientAssignment
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

PATIENTS = "/api/patients/"
ALLERGIES = "/api/clinical/allergies/"
WARD_DUTY = "/api/nurses/ward-assignments/"


def ids(response):
    body = response.json()
    rows = body["results"] if isinstance(body, dict) and "results" in body else body
    return {row["id"] for row in rows}


class NurseScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Nurse Scope", is_active=True)
        cls.nurse_user, _ = make_staff("scope_nurse", cls.hospital, role=StaffRole.NURSE)
        cls.admin_user, _ = make_staff("scope_nurse_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.nurse = Nurse.objects.create(hospital=cls.hospital, user=cls.nurse_user, name="Nurse Own", phone="9000001001")
        cls.ward_a = Ward.objects.create(hospital=cls.hospital, name="Ward A")
        cls.ward_b = Ward.objects.create(hospital=cls.hospital, name="Ward B")
        cls.today = hospital_today()

        cls.in_a = cls.admit("Synthetic Ward A", "9000001011", cls.ward_a)
        cls.in_b = cls.admit("Synthetic Ward B", "9000001012", cls.ward_b)
        cls.direct = cls.patient("Synthetic Direct", "9000001013")
        PatientAssignment.objects.create(nurse=cls.nurse, patient=cls.direct, hospital=cls.hospital,
                                         shift="Morning", shift_date=cls.today)
        cls.opd_today = cls.patient("Synthetic OPD Today", "9000001014")
        cls.token(cls.opd_today, cls.today, 1)
        cls.opd_old = cls.patient("Synthetic OPD Old", "9000001015")
        cls.token(cls.opd_old, cls.today - timedelta(days=3), 1)
        cls.emergency = cls.patient("Synthetic ER", "9000001016")
        EmergencyVisit.objects.create(hospital=cls.hospital, patient=cls.emergency, visit_number="SYN-NER-1", status="Waiting")

    @classmethod
    def patient(cls, name, phone):
        patient = Patient.objects.create(name=name, age=50, gender="Female", phone=phone, hospital=cls.hospital)
        PatientHospital.objects.create(patient=patient, hospital=cls.hospital, uhid=f"N-{phone}")
        return patient

    @classmethod
    def admit(cls, name, phone, ward):
        patient = cls.patient(name, phone)
        room = Room.objects.create(ward=ward, room_number=f"R-{phone}")
        bed = Bed.objects.create(room=room, bed_number="1", status="Occupied")
        admission = Admission.objects.create(patient=patient, hospital=cls.hospital, status="Admitted")
        BedAllocation.objects.create(admission=admission, bed=bed)
        return patient

    @classmethod
    def token(cls, patient, day, number):
        doctor, _ = Doctor.objects.get_or_create(
            hospital=cls.hospital, name="Dr OPD", defaults={"specialization": "General", "phone": "9000001018"},
        )
        visit = Visit.objects.create(hospital=cls.hospital, patient=patient, doctor=doctor)
        QueueToken.objects.create(hospital=cls.hospital, visit=visit, patient=patient, doctor=doctor,
                                  token_date=day, token_number=number)

    def duty(self, ward, shift="Morning", day=None, active=True):
        return NurseWardAssignment.objects.create(
            nurse=self.nurse, ward=ward, hospital=self.hospital, shift=shift,
            shift_date=day or self.today, is_active=active,
        )

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        return client

    def listed(self, user=None):
        return ids(self.client_for(user or self.nurse_user).get(PATIENTS, {"hospital": self.hospital.id}))

    def test_nurse_sees_ward_direct_opd_and_emergency_patients(self):
        self.duty(self.ward_a)
        self.assertEqual(self.listed(), {self.in_a.id, self.direct.id, self.opd_today.id, self.emergency.id})

    def test_without_ward_duty_only_direct_opd_and_emergency(self):
        self.assertEqual(self.listed(), {self.direct.id, self.opd_today.id, self.emergency.id})

    def test_past_duty_gives_no_access_but_last_nights_shift_does(self):
        self.duty(self.ward_a, "Morning", self.today - timedelta(days=1))
        self.assertNotIn(self.in_a.id, self.listed())
        self.duty(self.ward_a, "Night", self.today - timedelta(days=1))
        self.assertIn(self.in_a.id, self.listed())

    def test_cancelled_duty_gives_no_access(self):
        self.duty(self.ward_a, active=False)
        self.assertNotIn(self.in_a.id, self.listed())

    def test_nurse_cannot_write_for_a_patient_outside_their_duty(self):
        self.duty(self.ward_a)
        client = self.client_for(self.nurse_user)
        body = {"hospital": self.hospital.id, "name": "Dust"}
        self.assertEqual(client.post(ALLERGIES, {**body, "patient": self.in_b.id}, format="json").status_code, 403)
        ok = client.post(ALLERGIES, {**body, "patient": self.in_a.id}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(Allergy.objects.filter(name="Dust").count(), 1)

    def test_admin_assigns_ward_duty_and_nurse_cannot(self):
        body = {"hospital": self.hospital.id, "nurse": self.nurse.id, "ward": self.ward_b.id,
                "shift": "Evening", "shift_date": self.today.isoformat()}
        self.assertEqual(self.client_for(self.nurse_user).post(WARD_DUTY, body, format="json").status_code, 403)
        resp = self.client_for(self.admin_user).post(WARD_DUTY, body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIn(self.in_b.id, self.listed())

    def test_unknown_shift_is_refused(self):
        body = {"hospital": self.hospital.id, "nurse": self.nurse.id, "ward": self.ward_a.id,
                "shift": "Brunch", "shift_date": self.today.isoformat()}
        self.assertEqual(self.client_for(self.admin_user).post(WARD_DUTY, body, format="json").status_code, 400)

    def test_nurse_profile_links_to_the_login_with_the_same_email(self):
        login, _ = make_staff("scope_new_nurse", self.hospital, role=StaffRole.NURSE)
        login.email = "new.nurse@example.test"
        login.save(update_fields=["email"])
        resp = self.client_for(self.admin_user).post("/api/nurses/nurses/", {
            "hospital": self.hospital.id, "name": "Nurse New", "phone": "9000001017",
            "email": "New.Nurse@example.test",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Nurse.objects.get(pk=resp.json()["id"]).user, login)

    def test_admin_still_sees_every_patient(self):
        self.assertTrue({self.in_a.id, self.in_b.id, self.opd_old.id} <= self.listed(self.admin_user))

    def test_nurse_home_counts_only_their_patients(self):
        self.duty(self.ward_a)
        resp = self.client_for(self.nurse_user).get(f"/api/home/stats/?hospital={self.hospital.id}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["patients"], 4)
