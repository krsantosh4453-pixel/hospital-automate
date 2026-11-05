"""F1: UHIDs are issued automatically at registration, per hospital and year (synthetic data only)."""

import json
import unittest
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db import connection, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from hospital.models import Hospital
from patients.models import Patient, PatientHospital, UhidSequence
from patients.uhid import ensure_uhid, next_uhid, prefix_for
from security_tests.test_concurrency import run_together
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

YEAR = 2026


def on_day(day):
    return mock.patch("patients.uhid.hospital_today", return_value=day)


class RegistrationIssuesUhidTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Gen A", code="SGA", uhid_prefix="DCH", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Gen B", code="SGB", is_active=True)
        cls.desk, _ = make_staff("uhid_gen_desk", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.other_desk, _ = make_staff("uhid_gen_other", cls.other, role=StaffRole.RECEPTIONIST)

    def api(self, user=None, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user or self.desk)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def register(self, phone, user=None, hospital=None, **extra):
        hospital = hospital or self.hospital
        body = {"name": f"Synthetic {phone}", "age": 30, "gender": "Female", "phone": phone,
                "hospital": hospital.id, **extra}
        with on_day(date(YEAR, 3, 1)):
            return self.api(user, hospital).post("/api/patients/", body, format="json")

    def test_registration_returns_the_next_uhid_of_the_hospital(self):
        first = self.register("9000006001")
        second = self.register("9000006002")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()["uhid"], "DCH-2026-000001")
        self.assertEqual(second.json()["uhid"], "DCH-2026-000002")
        row = PatientHospital.objects.get(patient_id=first.json()["id"])
        self.assertEqual((row.hospital_id, row.uhid, row.is_active), (self.hospital.id, "DCH-2026-000001", True))

    def test_each_hospital_counts_on_its_own(self):
        self.register("9000006003")
        other = self.register("9000006004", user=self.other_desk, hospital=self.other)
        self.assertEqual(other.json()["uhid"], "SGB-2026-000001")

    def test_issue_is_audited(self):
        resp = self.register("9000006005")
        event = AuditLog.objects.get(action="patients.uhid.issue", object_id=str(resp.json()["id"]))
        self.assertEqual(json.loads(event.details)["uhid"], "DCH-2026-000001")

    def test_refused_registration_uses_no_number(self):
        bad = self.register("12")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.register("9000006006").json()["uhid"], "DCH-2026-000001")

    def test_patient_is_not_saved_when_the_uhid_cannot_be_issued(self):
        with mock.patch("patients.views.ensure_uhid", side_effect=RuntimeError("synthetic failure")):
            resp = self.register("9000006007")
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(Patient.objects.filter(phone="9000006007").exists())

    def test_search_finds_the_new_patient_by_uhid(self):
        created = self.register("9000006008").json()
        listed = self.api().get("/api/patients/", {"hospital": self.hospital.id, "search": "dch-2026-000001"}).json()
        rows = listed.get("results", listed)
        self.assertEqual([r["id"] for r in rows], [created["id"]])

    def test_other_hospital_cannot_find_it_by_uhid(self):
        self.register("9000006009")
        listed = self.api(self.other_desk, self.other).get(
            "/api/patients/", {"hospital": self.other.id, "search": "DCH-2026-000001"}).json()
        self.assertEqual(listed.get("results", listed), [])


class SequenceRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Seq", code="ab-1", is_active=True)

    def issue(self, day=date(YEAR, 6, 1)):
        with on_day(day), transaction.atomic():
            return next_uhid(self.hospital)

    def test_prefix_falls_back_to_the_code_then_the_id(self):
        self.assertEqual(prefix_for(self.hospital), "AB1")
        bare = Hospital.objects.create(name="Synthetic Bare", is_active=True)
        self.assertEqual(prefix_for(bare), f"H{bare.pk}")
        self.hospital.uhid_prefix = "xyz"
        self.assertEqual(prefix_for(self.hospital), "XYZ")

    def test_numbers_restart_each_year(self):
        self.assertEqual(self.issue(date(YEAR, 12, 31)), "AB1-2026-000001")
        self.assertEqual(self.issue(date(YEAR, 12, 31)), "AB1-2026-000002")
        self.assertEqual(self.issue(date(YEAR + 1, 1, 1)), "AB1-2027-000001")
        self.assertEqual(UhidSequence.objects.filter(hospital=self.hospital).count(), 2)

    def test_hand_entered_uhid_is_skipped(self):
        patient = Patient.objects.create(name="Synthetic Manual", age=30, gender="Male",
                                         phone="9000006101", hospital=self.hospital)
        PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid="ab1-2026-000001")
        self.assertEqual(self.issue(), "AB1-2026-000002")

    def test_ensure_uhid_keeps_an_existing_uhid_and_fills_a_blank_one(self):
        patient = Patient.objects.create(name="Synthetic Keep", age=30, gender="Male",
                                         phone="9000006102", hospital=self.hospital)
        row = PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid="")
        with on_day(date(YEAR, 6, 1)):
            filled, issued = ensure_uhid(patient, self.hospital)
            again, issued_again = ensure_uhid(patient, self.hospital)
        self.assertEqual((filled.pk, filled.uhid, issued), (row.pk, "AB1-2026-000001", True))
        self.assertEqual((again.uhid, issued_again), ("AB1-2026-000001", False))
        self.assertEqual(PatientHospital.objects.filter(patient=patient).count(), 1)


class OutsideTransactionTests(SimpleTestCase):
    def test_next_uhid_needs_a_transaction(self):
        # TestCase wraps every test in one, so this check runs without the database.
        with self.assertRaises(RuntimeError):
            next_uhid(Hospital(pk=1, name="Synthetic Unsaved"))


class MembershipEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Member", uhid_prefix="MEM", is_active=True)
        cls.desk, _ = make_staff("uhid_member_desk", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.patient = Patient.objects.create(name="Synthetic Member Patient", age=50, gender="Male",
                                             phone="9000006201", hospital=cls.hospital)

    def api(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.desk)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def test_blank_uhid_is_issued(self):
        with on_day(date(YEAR, 2, 2)):
            resp = self.api().post("/api/patient-hospitals/", {"patient": self.patient.id, "hospital": self.hospital.id},
                                   format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["uhid"], "MEM-2026-000001")

    def test_second_membership_at_the_same_hospital_is_refused(self):
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="MEM-OLD-1")
        resp = self.api().post("/api/patient-hospitals/", {"patient": self.patient.id, "hospital": self.hospital.id},
                               format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(PatientHospital.objects.filter(patient=self.patient).count(), 1)

    def test_issued_uhid_cannot_be_blanked(self):
        row = PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="MEM-OLD-2")
        resp = self.api().patch(f"/api/patient-hospitals/{row.id}/", {"uhid": ""}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        row.refresh_from_db()
        self.assertEqual(row.uhid, "MEM-OLD-2")


class HospitalPrefixSettingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Prefix A", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Prefix B", uhid_prefix="TAKEN", is_active=True)
        cls.admin, _ = make_staff("uhid_prefix_admin", cls.hospital, role=StaffRole.ADMIN)

    def patch(self, value):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.admin)
        return client.patch(f"/api/hospital/hospitals/{self.hospital.id}/", {"uhid_prefix": value}, format="json")

    def test_prefix_is_saved_in_capitals(self):
        resp = self.patch("dch")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["uhid_prefix"], "DCH")

    def test_bad_or_taken_prefix_is_refused(self):
        for value in ("D-C", "TOOLONGPREFIX1", "taken"):
            with self.subTest(value=value):
                self.assertEqual(self.patch(value).status_code, 400)


class BackfillCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Backfill", uhid_prefix="BF", is_active=True)
        cls.direct = Patient.objects.create(name="Synthetic Direct", age=20, gender="Male",
                                            phone="9000006301", hospital=cls.hospital)
        cls.blank = Patient.objects.create(name="Synthetic Blank", age=21, gender="Male", phone="9000006302")
        PatientHospital.objects.create(patient=cls.blank, hospital=cls.hospital, uhid="")
        cls.kept = Patient.objects.create(name="Synthetic Kept", age=22, gender="Male",
                                          phone="9000006303", hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.kept, hospital=cls.hospital, uhid="BF-LEGACY-9")

    def run_command(self, *args):
        out = StringIO()
        with on_day(date(YEAR, 4, 4)):
            call_command("assign_missing_uhids", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing_and_names_no_one(self):
        out = self.run_command()
        self.assertIn("2 patient(s) without a UHID", out)
        self.assertNotIn("Synthetic", out)
        self.assertFalse(PatientHospital.objects.filter(patient=self.direct).exists())

    def test_apply_fills_the_gaps_once(self):
        self.run_command("--apply")
        self.assertEqual(PatientHospital.objects.get(patient=self.direct).uhid, "BF-2026-000001")
        self.assertEqual(PatientHospital.objects.get(patient=self.blank).uhid, "BF-2026-000002")
        self.assertEqual(PatientHospital.objects.get(patient=self.kept).uhid, "BF-LEGACY-9")
        self.assertIn("Every registered patient has a UHID.", self.run_command("--apply"))


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ConcurrentRegistrationTests(TransactionTestCase):
    def test_parallel_registrations_get_distinct_uhids(self):
        hospital = Hospital.objects.create(name="Synthetic Race UHID", uhid_prefix="RACE", is_active=True)
        patients = [Patient.objects.create(name=f"Synthetic Race {i}", age=30, gender="Male",
                                           phone=f"900007{i:04d}", hospital=hospital) for i in range(8)]

        with on_day(date(YEAR, 5, 5)):
            results = run_together(lambda i: ensure_uhid(patients[i], hospital)[0].uhid)

        self.assertFalse([r for r in results if isinstance(r, Exception)], results)
        self.assertEqual(sorted(results), [f"RACE-2026-{n:06d}" for n in range(1, 9)])
        self.assertEqual(UhidSequence.objects.get(hospital=hospital, year=YEAR).last_value, 8)
