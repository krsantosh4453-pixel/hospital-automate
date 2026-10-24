"""Medication Administration Record states (synthetic data)."""

import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from clinical.models import Prescription, PrescriptionItem
from hospital.models import Hospital
from ipd.models import Admission
from nurses.models import MAR, MARAdministration
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff


class MARSafetyTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic MAR", is_active=True)
        self.nurse, _ = make_staff("mar_nurse", self.hospital, role=StaffRole.NURSE)
        patient = Patient.objects.create(name="Synthetic MAR Patient", age=70, gender="Male",
                                         phone="9000000080", hospital=self.hospital)
        PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid="MAR-1")
        admission = Admission.objects.create(patient=patient, hospital=self.hospital, status="Admitted")
        rx = Prescription.objects.create(hospital=self.hospital, patient=patient)
        item = PrescriptionItem.objects.create(prescription=rx, name="Synthetic Amoxicillin", dosage="500 mg")

        def mar(freq):
            return MAR.objects.create(patient=patient, admission=admission, hospital=self.hospital,
                                      prescription=rx, prescription_item=item, medicine_name="Synthetic Amoxicillin",
                                      dose="500 mg", route="Oral", frequency=freq,
                                      start_date=datetime.date.today(),
                                      end_date=datetime.date.today() + datetime.timedelta(days=1))
        self.mar = mar("TID")
        self.prn = mar("PRN")
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.nurse)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def test_schedule_starts_due_and_outcomes_need_a_nurse_action(self):
        resp = self.client.post(f"/api/nurses/mar/{self.mar.id}/generate_schedule/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        doses = MARAdministration.objects.filter(mar=self.mar)
        self.assertTrue(doses.exists())
        self.assertEqual(set(doses.values_list("status", flat=True)), {"Scheduled"})

        due = self.client.get(f"/api/nurses/mar/due_medications/?hospital={self.hospital.id}").json()
        self.assertTrue(due and all(row["status"] == "Scheduled" for row in due))

        dose = doses.order_by("scheduled_time").first()
        given = self.client.post(f"/api/nurses/mar-administrations/{dose.id}/administer/", {}, format="json")
        self.assertEqual(given.status_code, 200, given.content)
        dose.refresh_from_db()
        self.assertEqual(dose.status, "Administered")
        self.assertEqual(dose.recorded_by, self.nurse)
        self.assertIsNotNone(dose.administered_time)

        again = self.client.post(f"/api/nurses/mar-administrations/{dose.id}/administer/", {}, format="json")
        self.assertEqual(again.status_code, 400)  # no double dose

        # Regenerating the schedule keeps recorded outcomes.
        self.client.post(f"/api/nurses/mar/{self.mar.id}/generate_schedule/", {}, format="json")
        self.assertTrue(MARAdministration.objects.filter(pk=dose.pk, status="Administered").exists())

        other = doses.exclude(pk=dose.pk).first()
        self.client.patch(f"/api/nurses/mar-administrations/{other.id}/", {"status": "Administered"}, format="json")
        other.refresh_from_db()
        self.assertEqual(other.status, "Scheduled")
        self.assertEqual(self.client.post(f"/api/nurses/mar-administrations/{other.id}/exclude/", {}, format="json").status_code, 400)
        excluded = self.client.post(f"/api/nurses/mar-administrations/{other.id}/exclude/", {"reason": "NPO for surgery"}, format="json")
        self.assertEqual(excluded.json()["status"], "Excluded")

    def test_prn_dose(self):
        self.assertEqual(self.client.post(f"/api/nurses/mar/{self.mar.id}/prn/", {}, format="json").status_code, 400)
        resp = self.client.post(f"/api/nurses/mar/{self.prn.id}/prn/", {"notes": "Pain 6/10"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(resp.json()["is_prn"])
        self.assertEqual(resp.json()["status"], "Administered")
