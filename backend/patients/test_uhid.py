"""R-08: a UHID is a login identifier, so it must not repeat within a hospital."""

from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class UhidUniquenessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic UHID A", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic UHID B", is_active=True)
        cls.reception, _ = make_staff("uhid_reception", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.first = Patient.objects.create(name="Synthetic First", age=30, gender="Male",
                                           phone="9000000501", hospital=cls.hospital)
        cls.second = Patient.objects.create(name="Synthetic Second", age=31, gender="Female",
                                            phone="9000000502", hospital=cls.hospital)
        cls.taken = PatientHospital.objects.create(patient=cls.first, hospital=cls.hospital, uhid="UH-100")

    def api(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.reception)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def register(self, patient, uhid):
        return self.api().post(
            "/api/patient-hospitals/",
            {"patient": patient.id, "hospital": self.hospital.id, "uhid": uhid},
            format="json",
        )

    def test_same_uhid_in_the_same_hospital_is_refused(self):
        for uhid in ("UH-100", "uh-100", " UH-100 "):
            with self.subTest(uhid=uhid):
                resp = self.register(self.second, uhid)
                self.assertEqual(resp.status_code, 400, resp.content)
                self.assertIn("uhid", resp.json()["details"])

    def test_new_uhid_is_accepted(self):
        resp = self.register(self.second, "UH-101")
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_editing_a_row_keeps_its_own_uhid(self):
        resp = self.api().patch(f"/api/patient-hospitals/{self.taken.id}/", {"is_active": True}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_same_uhid_at_another_hospital_is_allowed(self):
        PatientHospital.objects.create(patient=self.second, hospital=self.other, uhid="UH-100")
        self.assertEqual(PatientHospital.objects.filter(uhid="UH-100").count(), 2)

    def test_database_refuses_a_repeat_ignoring_case(self):
        # The constraint catches writes that bypass the API (admin, scripts, imports).
        with self.assertRaises(IntegrityError), transaction.atomic():
            PatientHospital.objects.create(patient=self.second, hospital=self.hospital, uhid="uh-100")

    def test_blank_uhids_may_repeat(self):
        PatientHospital.objects.create(patient=self.second, hospital=self.hospital, uhid="")
        PatientHospital.objects.create(patient=self.first, hospital=self.other, uhid="")
        third = Patient.objects.create(name="Synthetic Third", age=32, gender="Male",
                                       phone="9000000503", hospital=self.other)
        PatientHospital.objects.create(patient=third, hospital=self.other, uhid="")
        self.assertEqual(PatientHospital.objects.filter(uhid="").count(), 3)

    def test_report_does_not_name_patients(self):
        out = StringIO()
        call_command("report_duplicate_uhids", stdout=out)
        self.assertNotIn("Synthetic", out.getvalue())

    def test_report_is_quiet_when_there_are_none(self):
        out = StringIO()
        call_command("report_duplicate_uhids", stdout=out)
        self.assertIn("No duplicate UHIDs", out.getvalue())


class UhidShownToStaffTests(TestCase):
    """A19: the patient record carries the UHID of the hospital being acted in, and only that one."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic UHID Show A", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic UHID Show B", is_active=True)
        cls.patient = Patient.objects.create(name="Synthetic Shown", age=40, gender="Male", phone="9000000511",
                                             hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="A-511")
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.other, uhid="B-511")
        cls.reception, _ = make_staff("uhid_show_desk", cls.hospital, role=StaffRole.RECEPTIONIST)

    def test_detail_and_list_show_this_hospitals_uhid_only(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.reception)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        self.assertEqual(client.get(f"/api/patients/{self.patient.id}/").json()["uhid"], "A-511")
        listed = client.get(f"/api/patients/?hospital={self.hospital.id}").json()
        rows = listed.get("results", listed)
        self.assertEqual([r["uhid"] for r in rows if r["id"] == self.patient.id], ["A-511"])
