"""
BUG-01 / BUG-04 (Android E2E 2026-11-19, synthetic data only).

BUG-01: a self-registered patient could never become a patient of a hospital,
so could never book; the E2E run needed a database fixture. BUG-04: every
self-registered patient was stored with age 1.
"""

import importlib
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import QueueToken
from hospital.models import Hospital
from patients.models import Patient, PatientHospital, age_from_dob
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

User = get_user_model()


def register(client, **overrides):
    payload = {
        "role": "Patient", "full_name": "Synthetic Meera Link", "phone": "9000002001",
        "email": "meera.link@example.test", "password": "correct-horse-42", "confirm_password": "correct-horse-42",
        "date_of_birth": "1990-04-02", "gender": "Female",
    }
    payload.update(overrides)
    return client.post("/api/auth/register/", payload, format="json")


def staff_client(user, hospital):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.pk))
    return client


class Fixture:
    def build(self):
        self.hospital = Hospital.objects.create(name="Synthetic Link General", is_active=True, uhid_prefix="SLG")
        self.other = Hospital.objects.create(name="Synthetic Link Other", is_active=True)
        self.closed = Hospital.objects.create(name="Synthetic Link Closed", is_active=True,
                                              allow_patient_self_registration=False)
        self.inactive = Hospital.objects.create(name="Synthetic Link Inactive", is_active=False)
        self.desk, _ = make_staff("link_desk", self.hospital, role=StaffRole.RECEPTIONIST)
        self.other_desk, _ = make_staff("link_other_desk", self.other, role=StaffRole.RECEPTIONIST)
        self.nurse, _ = make_staff("link_nurse", self.hospital, role=StaffRole.NURSE)

    def portal_patient(self, phone="9000002002", dob=date(1985, 1, 20)):
        user = User.objects.create_user(username=f"portal_{phone}", email=f"{phone}@example.test",
                                        password="correct-horse-42")
        return Patient.objects.create(user=user, name=f"Synthetic Portal {phone}", gender="Male", phone=phone,
                                      date_of_birth=dob, email_verified=True)

    def patient_client(self, patient):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(patient.user)
        return client


class RegistrationTests(Fixture, TestCase):
    def setUp(self):
        self.build()
        self.client = APIClient(raise_request_exception=False)

    def test_registration_with_a_hospital_links_it_and_issues_a_uhid(self):
        response = register(self.client, hospital=self.hospital.pk)

        self.assertEqual(response.status_code, 201, response.content)
        patient = Patient.objects.get(user__email="meera.link@example.test")
        membership = PatientHospital.objects.get(patient=patient, hospital=self.hospital)
        self.assertTrue(membership.uhid.startswith("SLG-"), membership.uhid)
        self.assertEqual(response.json()["patient"]["hospitals"],
                         [{"id": self.hospital.pk, "name": self.hospital.name, "uhid": membership.uhid}])
        self.assertEqual(Patient.objects.filter(phone="9000002001").count(), 1)

    def test_age_comes_from_the_date_of_birth_never_a_placeholder(self):
        register(self.client)
        patient = Patient.objects.get(user__email="meera.link@example.test")
        self.assertEqual(patient.date_of_birth, date(1990, 4, 2))
        self.assertEqual(patient.age, age_from_dob(date(1990, 4, 2)))
        self.assertGreater(patient.age, 30)

    def test_a_date_of_birth_is_required_and_checked(self):
        for dob, reason in (("", "required"), ("2999-01-01", "future"), ("02/04/1990", "not valid"),
                            ("1850-01-01", "year")):
            response = register(self.client, date_of_birth=dob)
            self.assertEqual(response.status_code, 400, dob)
            self.assertIn(reason, response.json()["error"].lower(), dob)
        self.assertFalse(Patient.objects.filter(phone="9000002001").exists())
        self.assertFalse(User.objects.filter(email="meera.link@example.test").exists())

    def test_a_patient_cannot_pick_a_closed_inactive_or_unknown_hospital(self):
        for hospital_id in (self.closed.pk, self.inactive.pk, 999999, "abc"):
            response = register(self.client, hospital=hospital_id)
            self.assertEqual(response.status_code, 400, (hospital_id, response.content))
        self.assertFalse(User.objects.filter(email="meera.link@example.test").exists())
        self.assertFalse(PatientHospital.objects.exists())

    def test_the_public_list_shows_only_open_hospitals(self):
        response = self.client.get("/api/auth/patient/hospitals/")
        self.assertEqual(response.status_code, 200)
        names = [row["name"] for row in response.json()]
        self.assertIn(self.hospital.name, names)
        self.assertNotIn(self.closed.name, names)
        self.assertNotIn(self.inactive.name, names)
        self.assertEqual(set(response.json()[0]), {"id", "name", "city"})


class JoinHospitalTests(Fixture, TestCase):
    def setUp(self):
        self.build()
        self.patient = self.portal_patient()

    def join(self, hospital_id, client=None):
        client = client or self.patient_client(self.patient)
        return client.post("/api/auth/patient/hospitals/join/", {"hospital": hospital_id}, format="json")

    def test_joining_issues_one_uhid_and_repeating_returns_it(self):
        first = self.join(self.hospital.pk)
        again = self.join(self.hospital.pk)

        self.assertEqual((first.status_code, again.status_code), (201, 200), first.content)
        self.assertEqual(first.json()["uhid"], again.json()["uhid"])
        self.assertEqual(PatientHospital.objects.filter(patient=self.patient, hospital=self.hospital).count(), 1)

    def test_joined_hospital_can_be_booked_and_records_stay_separate(self):
        self.join(self.hospital.pk)
        self.join(self.other.pk)
        client = self.patient_client(self.patient)

        options = client.get("/api/appointments/booking-options/").json()

        self.assertEqual({h["id"] for h in options["hospitals"]}, {self.hospital.pk, self.other.pk})
        uhids = set(PatientHospital.objects.filter(patient=self.patient).values_list("uhid", flat=True))
        self.assertEqual(len(uhids), 2)

    def test_a_patient_cannot_join_a_closed_hospital(self):
        response = self.join(self.closed.pk)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(PatientHospital.objects.filter(patient=self.patient).exists())

    def test_staff_and_strangers_cannot_use_the_patient_join(self):
        self.assertEqual(self.join(self.hospital.pk, client=staff_client(self.desk, self.hospital)).status_code, 403)
        self.assertEqual(self.join(self.hospital.pk, client=APIClient()).status_code, 401)


class ReceptionLinkTests(Fixture, TestCase):
    def setUp(self):
        self.build()
        self.patient = self.portal_patient()

    def link(self, user=None, hospital=None, **body):
        payload = {"phone": "9000002002", "date_of_birth": "1985-01-20", **body}
        return staff_client(user or self.desk, hospital or self.hospital).post(
            "/api/patients/link/", payload, format="json")

    def test_the_desk_links_an_existing_patient_with_phone_and_date_of_birth(self):
        first = self.link()
        again = self.link()

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(first.json()["id"], self.patient.pk)
        self.assertTrue(first.json()["uhid"].startswith("SLG-"))
        # Prompt 3: the reception screen tells "registered now" from "already here".
        self.assertIs(first.json()["created"], True)
        self.assertIs(again.json()["created"], False)
        self.assertEqual(again.json()["uhid"], first.json()["uhid"])
        self.assertEqual(PatientHospital.objects.filter(patient=self.patient).count(), 1)
        self.assertEqual(Patient.objects.filter(phone="9000002002").count(), 1)

    def test_a_wrong_date_of_birth_finds_nobody(self):
        response = self.link(date_of_birth="1985-01-21")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.json().get("not_found"))
        self.assertFalse(PatientHospital.objects.exists())

    def test_the_mobile_number_alone_is_not_enough(self):
        response = self.link(date_of_birth="")
        self.assertEqual(response.status_code, 400)

    def test_other_roles_and_other_hospitals_cannot_link(self):
        self.assertEqual(self.link(user=self.nurse).status_code, 403)
        # A desk of another hospital acting in this one.
        self.assertEqual(self.link(user=self.other_desk, hospital=self.hospital).status_code, 403)
        self.assertFalse(PatientHospital.objects.exists())

    def test_registering_a_portal_patient_again_is_stopped(self):
        client = staff_client(self.desk, self.hospital)
        body = {"name": "Synthetic Portal Again", "age": 41, "gender": "Male", "phone": "9000002002",
                "hospital": self.hospital.pk}

        refused = client.post("/api/patients/", body, format="json")
        confirmed = client.post("/api/patients/", {**body, "confirm_new": True}, format="json")

        self.assertEqual(refused.status_code, 409, refused.content)
        self.assertTrue(refused.json().get("portal_account"))
        self.assertEqual(confirmed.status_code, 201, confirmed.content)  # a different person sharing the phone

    def test_desk_registration_needs_an_age_or_a_date_of_birth(self):
        client = staff_client(self.desk, self.hospital)
        base = {"name": "Synthetic Walk In", "gender": "Female", "phone": "9000002099", "hospital": self.hospital.pk}

        missing = client.post("/api/patients/", base, format="json")
        with_dob = client.post("/api/patients/", {**base, "date_of_birth": "2001-03-04"}, format="json")

        self.assertEqual(missing.status_code, 400, missing.content)
        self.assertEqual(with_dob.status_code, 201, with_dob.content)
        self.assertEqual(with_dob.json()["age"], age_from_dob(date(2001, 3, 4)))
        self.assertTrue(with_dob.json()["uhid"])

    def test_a_linked_patient_gets_one_token_at_check_in(self):
        self.link()
        doctor = Doctor.objects.create(hospital=self.hospital, name="Dr Synthetic Link", specialization="General",
                                       phone="9000002098")
        appointment = Appointment.objects.create(hospital=self.hospital, patient=self.patient, doctor=doctor,
                                                 appointment_date=hospital_today(), appointment_time=time(11, 0))
        client = staff_client(self.desk, self.hospital)

        first = client.post("/api/encounters/queue-tokens/issue/", {"appointment": appointment.pk}, format="json")
        again = client.post("/api/encounters/queue-tokens/issue/", {"appointment": appointment.pk}, format="json")

        self.assertEqual((first.status_code, again.status_code), (201, 200), first.content)
        self.assertEqual(QueueToken.objects.filter(appointment=appointment).count(), 1)
        self.assertEqual(Appointment.objects.get(pk=appointment.pk).status, Appointment.Status.CHECKED_IN)


class AccessTests(Fixture, TestCase):
    def setUp(self):
        self.build()
        self.patient = self.portal_patient()
        staff_client(self.desk, self.hospital).post(
            "/api/patients/link/", {"phone": "9000002002", "date_of_birth": "1985-01-20"}, format="json")

    def test_the_patient_sees_only_their_own_record(self):
        someone = self.portal_patient(phone="9000002003")
        client = self.patient_client(self.patient)
        rows = client.get("/api/patients/").json()
        rows = rows.get("results", rows)
        self.assertEqual([row["id"] for row in rows], [self.patient.pk])
        self.assertEqual(client.get(f"/api/patients/{someone.pk}/").status_code, 404)

    def test_a_receptionist_cannot_read_clinical_records(self):
        client = staff_client(self.desk, self.hospital)
        # Prescriptions are not listed: the front desk reads them by design
        # (clinical/views.py PrescriptionViewSet, IsReceptionistReadOnly).
        for url in ("/api/clinical/vitals/", "/api/clinical/diagnoses/",
                    f"/api/patients/{self.patient.pk}/timeline/"):
            self.assertIn(client.get(url).status_code, (403, 404), url)

    def test_another_hospitals_desk_cannot_see_the_linked_patient(self):
        client = staff_client(self.other_desk, self.other)
        self.assertEqual(client.get(f"/api/patients/{self.patient.pk}/").status_code, 404)


class PlaceholderAgeMigrationTests(Fixture, TestCase):
    """Migration 0015 clears only the self-registration placeholder age."""

    def test_only_placeholder_rows_lose_their_age(self):
        self.build()
        placeholder = self.portal_patient(phone="9000002010", dob=None)
        Patient.objects.filter(pk=placeholder.pk).update(age=1)
        real_infant = Patient.objects.create(name="Synthetic Infant", age=1, gender="Female",
                                             phone="9000002011", hospital=self.hospital)
        migration = importlib.import_module("patients.migrations.0015_clear_placeholder_age")

        from django.apps import apps
        migration.clear(apps, None)

        self.assertIsNone(Patient.objects.get(pk=placeholder.pk).age)
        self.assertEqual(Patient.objects.get(pk=real_infant.pk).age, 1)

    def test_a_baby_born_this_year_is_zero_not_one(self):
        today = hospital_today()
        self.assertEqual(age_from_dob(today - timedelta(days=30), today), 0)


class PatientProfileUhidTests(Fixture, TestCase):
    """BUG-11: the patient app showed the internal record id as "Patient ID"."""

    def test_me_lists_each_hospital_uhid(self):
        self.build()
        patient = self.portal_patient(phone="9000002020")
        client = self.patient_client(patient)
        joined = client.post("/api/auth/patient/hospitals/join/", {"hospital": self.hospital.pk}, format="json")
        self.assertIn(joined.status_code, (200, 201), joined.data)

        me = client.get("/api/auth/patient/me/")

        self.assertEqual(me.status_code, 200)
        uhid = PatientHospital.objects.get(patient=patient, hospital=self.hospital).uhid
        self.assertTrue(uhid.startswith("SLG"))
        self.assertEqual(me.data["hospitals"], [{"id": self.hospital.pk, "name": self.hospital.name, "uhid": uhid}])

    def test_me_has_no_hospital_rows_before_joining(self):
        self.build()
        me = self.patient_client(self.portal_patient(phone="9000002021")).get("/api/auth/patient/me/")
        self.assertEqual(me.data["hospitals"], [])
