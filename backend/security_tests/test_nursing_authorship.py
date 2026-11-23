"""
Who a nursing record says wrote it, and doses recorded at the same moment
(synthetic data only). Notes, assessments, finished care tasks and doses
carry the requester's own nurse profile; naming another nurse is refused.

The parallel-dose test needs real row locks and runs only on PostgreSQL:

    TEST_DATABASE_URL=postgres://user:pass@localhost:5432/hms_test \\
        python manage.py test security_tests.test_nursing_authorship
"""

import datetime
import unittest

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from clinical.models import Prescription, PrescriptionItem
from hospital.models import Hospital
from ipd.models import Admission
from nurses.models import MAR, CareTask, MARAdministration, Nurse, NursingAssessment, NursingNote
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_concurrency import THREADS, run_together
from .test_tenant_isolation import make_staff


class WardSetup:
    """One hospital, two linked nurses, a doctor and an admitted patient (no bed yet, so every nurse sees them)."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Authorship", is_active=True)
        self.nurse_user, _ = make_staff("author_nurse", self.hospital, role=StaffRole.NURSE)
        self.other_user, _ = make_staff("other_nurse", self.hospital, role=StaffRole.NURSE)
        self.doctor_user, _ = make_staff("author_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.nurse = Nurse.objects.create(hospital=self.hospital, user=self.nurse_user, name="Synthetic Nurse A",
                                          phone="9000000101")
        self.other = Nurse.objects.create(hospital=self.hospital, user=self.other_user, name="Synthetic Nurse B",
                                          phone="9000000102")
        self.patient = Patient.objects.create(name="Synthetic Ward Patient", age=60, gender="Female",
                                              phone="9000000103", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="AUTH-1")
        self.admission = Admission.objects.create(patient=self.patient, hospital=self.hospital, status="Admitted")

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def make_dose(self):
        rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        item = PrescriptionItem.objects.create(prescription=rx, name="Synthetic Paracetamol", dosage="500 mg")
        mar = MAR.objects.create(patient=self.patient, admission=self.admission, hospital=self.hospital,
                                 prescription=rx, prescription_item=item, medicine_name="Synthetic Paracetamol",
                                 dose="500 mg", route="Oral", frequency="TID",
                                 start_date=datetime.date.today(),
                                 end_date=datetime.date.today() + datetime.timedelta(days=1))
        return MARAdministration.objects.create(mar=mar, scheduled_time=timezone.now())


class NursingAuthorshipTests(WardSetup, TestCase):
    def note_body(self, **extra):
        return {"hospital": self.hospital.id, "patient": self.patient.id, "admission": self.admission.id,
                "note_type": "Progress", "note": "Synthetic progress note.", **extra}

    def test_a_note_is_recorded_under_the_writers_own_nurse_profile(self):
        resp = self.client_for(self.nurse_user).post("/api/nurses/notes/", self.note_body(), format="json")

        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["nurse"], self.nurse.id)
        self.assertEqual(resp.json()["nurse_name"], "Synthetic Nurse A")

    def test_a_note_cannot_name_another_nurse_as_its_author(self):
        resp = self.client_for(self.nurse_user).post(
            "/api/nurses/notes/", self.note_body(nurse=self.other.id), format="json")

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("nurse", resp.json()["details"])
        self.assertFalse(NursingNote.objects.exists())

    def test_naming_ones_own_profile_is_accepted(self):
        resp = self.client_for(self.nurse_user).post(
            "/api/nurses/notes/", self.note_body(nurse=self.nurse.id), format="json")

        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(NursingNote.objects.get().nurse, self.nurse)

    def test_an_assessment_with_vitals_is_recorded_under_the_writers_profile(self):
        resp = self.client_for(self.nurse_user).post("/api/nurses/assessments/", {
            "hospital": self.hospital.id, "patient": self.patient.id, "admission": self.admission.id,
            "assessment_type": "Focused", "vitals": {"pulse": "80", "spo2": "98"},
        }, format="json")

        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(NursingAssessment.objects.get().nurse, self.nurse)

    def test_the_author_of_a_note_cannot_be_changed(self):
        created = self.client_for(self.nurse_user).post("/api/nurses/notes/", self.note_body(), format="json")
        note_id = created.json()["id"]

        resp = self.client_for(self.nurse_user).patch(
            f"/api/nurses/notes/{note_id}/", {"nurse": self.other.id}, format="json")

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(NursingNote.objects.get(pk=note_id).nurse, self.nurse)

    def test_a_doctors_nursing_note_names_no_nurse(self):
        from .test_tenant_isolation import put_in_care

        put_in_care(self.doctor_user, self.hospital, self.patient)
        resp = self.client_for(self.doctor_user).post("/api/nurses/notes/", self.note_body(), format="json")

        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIsNone(NursingNote.objects.get().nurse)

    def test_a_dose_cannot_be_recorded_as_given_by_another_nurse(self):
        dose = self.make_dose()

        resp = self.client_for(self.nurse_user).post(
            f"/api/nurses/mar-administrations/{dose.id}/administer/", {"administered_by": self.other.id},
            format="json")

        self.assertEqual(resp.status_code, 400, resp.content)
        dose.refresh_from_db()
        self.assertEqual(dose.status, MARAdministration.SCHEDULED)

    def test_a_given_dose_names_the_nurse_who_recorded_it(self):
        dose = self.make_dose()

        resp = self.client_for(self.nurse_user).post(
            f"/api/nurses/mar-administrations/{dose.id}/administer/", {}, format="json")

        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["administered_by"], self.nurse.id)
        self.assertEqual(resp.json()["administered_by_name"], "Synthetic Nurse A")

    def test_a_finished_care_task_names_the_nurse_who_finished_it(self):
        task = CareTask.objects.create(patient=self.patient, admission=self.admission, hospital=self.hospital,
                                       task_type="Vitals", description="Synthetic 4-hourly vitals",
                                       scheduled_at=timezone.now())
        client = self.client_for(self.nurse_user)

        refused = client.post(f"/api/nurses/care-tasks/{task.id}/complete/",
                              {"completed_by": self.other.id}, format="json")
        done = client.post(f"/api/nurses/care-tasks/{task.id}/complete/", {}, format="json")

        self.assertEqual(refused.status_code, 400, refused.content)
        self.assertEqual(done.status_code, 200, done.content)
        task.refresh_from_db()
        self.assertEqual((task.status, task.completed_by), ("Completed", self.nurse))


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ParallelDoseTests(WardSetup, TransactionTestCase):
    def test_one_dose_is_recorded_once_however_many_nurses_tap_at_once(self):
        dose = self.make_dose()

        def administer(index):
            client = APIClient()
            client.force_authenticate(self.nurse_user if index % 2 == 0 else self.other_user)
            client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
            return client.post(f"/api/nurses/mar-administrations/{dose.id}/administer/", {},
                               format="json").status_code

        statuses = run_together(administer)

        self.assertEqual((statuses.count(200), statuses.count(400)), (1, THREADS - 1), statuses)
        from audit.models import AuditLog

        self.assertEqual(
            AuditLog.objects.filter(action="nurses.maradministration.administered", object_id=str(dose.id)).count(), 1)
