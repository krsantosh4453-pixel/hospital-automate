"""Medication Administration Record states (synthetic data)."""

import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import Prescription, PrescriptionItem
from hospital.models import Hospital
from ipd.models import Admission
from nurses.models import MAR, MARAdministration
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_in_care


class MARSafetyTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic MAR", is_active=True)
        self.nurse, _ = make_staff("mar_nurse", self.hospital, role=StaffRole.NURSE)
        self.doctor, _ = make_staff("mar_doctor", self.hospital, role=StaffRole.DOCTOR)
        patient = Patient.objects.create(name="Synthetic MAR Patient", age=70, gender="Male",
                                         phone="9000000080", hospital=self.hospital)
        PatientHospital.objects.create(patient=patient, hospital=self.hospital, uhid="MAR-1")
        admission = Admission.objects.create(patient=patient, hospital=self.hospital, status="Admitted")
        rx = Prescription.objects.create(hospital=self.hospital, patient=patient)
        item = PrescriptionItem.objects.create(prescription=rx, name="Synthetic Amoxicillin", dosage="500 mg")
        self.patient, self.admission, self.rx, self.item = patient, admission, rx, item
        put_in_care(self.doctor, self.hospital, patient)

        def mar(freq):
            return MAR.objects.create(patient=patient, admission=admission, hospital=self.hospital,
                                      prescription=rx, prescription_item=item, medicine_name="Synthetic Amoxicillin",
                                      dose="500 mg", route="Oral", frequency=freq,
                                      start_date=datetime.date.today(),
                                      end_date=datetime.date.today() + datetime.timedelta(days=1))
        self.mar = mar("TID")
        self.prn = mar("PRN")
        self.client = self.client_for(self.nurse)
        self.doctor_client = self.client_for(self.doctor)

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def test_schedule_starts_due_and_outcomes_need_a_nurse_action(self):
        resp = self.doctor_client.post(f"/api/nurses/mar/{self.mar.id}/generate_schedule/", {}, format="json")
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
        self.doctor_client.post(f"/api/nurses/mar/{self.mar.id}/generate_schedule/", {}, format="json")
        self.assertTrue(MARAdministration.objects.filter(pk=dose.pk, status="Administered").exists())

        other = doses.exclude(pk=dose.pk).first()
        self.client.patch(f"/api/nurses/mar-administrations/{other.id}/", {"status": "Administered"}, format="json")
        other.refresh_from_db()
        self.assertEqual(other.status, "Scheduled")
        # Not giving a dose is the doctor's decision.
        self.assertEqual(self.client.post(f"/api/nurses/mar-administrations/{other.id}/exclude/",
                                          {"reason": "NPO for surgery"}, format="json").status_code, 403)
        self.assertEqual(self.doctor_client.post(f"/api/nurses/mar-administrations/{other.id}/exclude/", {}, format="json").status_code, 400)
        excluded = self.doctor_client.post(f"/api/nurses/mar-administrations/{other.id}/exclude/", {"reason": "NPO for surgery"}, format="json")
        self.assertEqual(excluded.json()["status"], "Excluded")

    def test_prn_dose(self):
        self.assertEqual(self.client.post(f"/api/nurses/mar/{self.mar.id}/prn/", {}, format="json").status_code, 400)
        resp = self.client.post(f"/api/nurses/mar/{self.prn.id}/prn/", {"notes": "Pain 6/10"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(resp.json()["is_prn"])
        self.assertEqual(resp.json()["status"], "Administered")

    # Doctor's order: a nurse gives medicine only under one (owner decision, 2026-11-05).

    def order(self, client, **extra):
        body = {"patient": self.patient.id, "admission": self.admission.id, "hospital": self.hospital.id,
                "prescription": self.rx.id, "prescription_item": self.item.id,
                "medicine_name": "Synthetic Amoxicillin", "dose": "500 mg", "route": "Oral", "frequency": "BID",
                "start_date": datetime.date.today().isoformat()}
        body.update(extra)
        return client.post("/api/nurses/mar/", body, format="json")

    def test_only_a_doctor_writes_or_changes_an_order(self):
        self.assertEqual(self.order(self.client).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/nurses/mar/{self.mar.id}/", {"dose": "1 g"}, format="json").status_code, 403)
        self.assertEqual(self.client.post(f"/api/nurses/mar/{self.mar.id}/generate_schedule/", {}, format="json").status_code, 403)

        resp = self.order(self.doctor_client)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["ordered_by"], self.doctor.id)
        self.assertTrue(self.client.get(f"/api/nurses/mar/{resp.json()['id']}/").status_code == 200)  # nurse can read it

    def test_order_must_match_the_patients_own_prescription(self):
        other_rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        resp = self.order(self.doctor_client, prescription=other_rx.id)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("prescription_item", resp.json().get("details", resp.json()))

    def test_no_dose_is_given_once_the_doctor_stops_the_order(self):
        self.doctor_client.post(f"/api/nurses/mar/{self.mar.id}/generate_schedule/", {}, format="json")
        dose = MARAdministration.objects.filter(mar=self.mar).order_by("scheduled_time").first()
        stopped = self.doctor_client.patch(f"/api/nurses/mar/{self.mar.id}/", {"is_active": False}, format="json")
        self.assertEqual(stopped.status_code, 200, stopped.content)

        resp = self.client.post(f"/api/nurses/mar-administrations/{dose.id}/administer/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("doctor", resp.json()["detail"])
        dose.refresh_from_db()
        self.assertEqual(dose.status, "Scheduled")

        self.mar.refresh_from_db()
        self.prn.is_active = False
        self.prn.save()
        self.assertEqual(self.client.post(f"/api/nurses/mar/{self.prn.id}/prn/", {}, format="json").status_code, 400)

    def test_no_dose_after_the_orders_end_date(self):
        self.mar.end_date = datetime.date.today() - datetime.timedelta(days=1)
        self.mar.start_date = self.mar.end_date
        self.mar.save()
        dose = MARAdministration.objects.create(mar=self.mar, scheduled_time=timezone.now())
        resp = self.client.post(f"/api/nurses/mar-administrations/{dose.id}/administer/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_each_dose_records_who_gave_it(self):
        self.doctor_client.post(f"/api/nurses/mar/{self.mar.id}/generate_schedule/", {}, format="json")
        dose = MARAdministration.objects.filter(mar=self.mar).order_by("scheduled_time").first()
        self.client.post(f"/api/nurses/mar-administrations/{dose.id}/administer/", {}, format="json")
        entry = AuditLog.objects.get(action="nurses.maradministration.administered", object_id=str(dose.id))
        self.assertEqual(entry.user, self.nurse)
