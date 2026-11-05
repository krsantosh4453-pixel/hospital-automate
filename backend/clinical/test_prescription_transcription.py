"""
F13: pharmacists do not prescribe. A paper prescription is transcribed by the
pharmacy, names who signed it, and is dispensed only after a second person
(another pharmacist or an Admin) verifies it. Synthetic data only.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import Prescription, PrescriptionItem
from config.hospital_time import hospital_today
from hospital.models import Hospital
from patients.models import Patient
from pharmacy.models import Medicine
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

URL = "/api/clinical/prescriptions/"
DISPENSE = "/api/pharmacy-sales/dispense-prescription/"


class TranscriptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Paper Rx", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Paper Rx Other", is_active=True)
        cls.pharmacist, _ = make_staff("paper_pharm_a", cls.hospital, role=StaffRole.PHARMACIST)
        cls.second, _ = make_staff("paper_pharm_b", cls.hospital, role=StaffRole.PHARMACIST)
        cls.admin, _ = make_staff("paper_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.doctor_user, _ = make_staff("paper_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.desk, _ = make_staff("paper_desk", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.outsider, _ = make_staff("paper_outsider", cls.other, role=StaffRole.PHARMACIST)
        cls.patient = Patient.objects.create(name="Synthetic Paper Patient", age=50, gender="Female",
                                             phone="9000009101", hospital=cls.hospital)
        cls.doctor = put_in_care(cls.doctor_user, cls.hospital, cls.patient)
        cls.medicine = Medicine.objects.create(name="Paracetamol", hospital=cls.hospital, batch="PP1",
                                               quantity=50, price=Decimal("2.00"))

    def api(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def body(self, **extra):
        return {
            "hospital": self.hospital.id, "patient": self.patient.id,
            "original_prescriber_name": "Dr Outside Synthetic", "original_prescriber_registration": "REG-12345",
            "original_prescription_date": str(hospital_today()),
            "items": [{"name": "Paracetamol", "dosage": "500 mg", "frequency": "1-0-1", "duration": "3 days",
                       "quantity": 6, "instructions": "After food"}],
            **extra,
        }

    def transcribe(self, user=None, **extra):
        return self.api(user or self.pharmacist).post(f"{URL}transcribe/", self.body(**extra), format="json")

    def dispense(self, rx_id, user=None):
        item = PrescriptionItem.objects.get(prescription_id=rx_id)
        return self.api(user or self.pharmacist).post(
            DISPENSE, {"prescription": rx_id, "lines": [{"item": item.pk, "medicine": self.medicine.pk}]}, format="json")

    # --- pharmacists do not prescribe -------------------------------------

    def test_pharmacist_cannot_write_a_prescription(self):
        client = self.api(self.pharmacist)
        resp = client.post(URL, {"hospital": self.hospital.id, "patient": self.patient.id,
                                 "items": [{"name": "Paracetamol", "quantity": 1}]}, format="json")
        self.assertEqual(resp.status_code, 403)
        rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor)
        self.assertEqual(client.patch(f"{URL}{rx.pk}/", {"status": "Cancelled"}, format="json").status_code, 403)
        self.assertEqual(client.post("/api/clinical/prescription-items/",
                                     {"prescription": rx.pk, "name": "Extra", "quantity": 1},
                                     format="json").status_code, 403)
        self.assertEqual(client.get(f"{URL}{rx.pk}/").status_code, 200)

    def test_doctor_and_desk_cannot_transcribe(self):
        for user in (self.doctor_user, self.desk):
            with self.subTest(user=user.username):
                self.assertEqual(self.transcribe(user).status_code, 403)

    def test_source_fields_cannot_be_set_on_a_normal_prescription(self):
        resp = self.api(self.doctor_user).post(URL, self.body(source="Paper transcription"), format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        rx = Prescription.objects.get(pk=resp.json()["id"])
        self.assertEqual((rx.source, rx.original_prescriber_name, rx.transcribed_by_id), ("Electronic", "", None))

    # --- the transcription ------------------------------------------------

    def test_transcription_records_its_source_and_waits(self):
        resp = self.transcribe()
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual((data["status"], data["source"]), ("Pending Verification", "Paper transcription"))
        self.assertEqual((data["original_prescriber_name"], data["original_prescriber_registration"]),
                         ("Dr Outside Synthetic", "REG-12345"))
        self.assertEqual(data["transcribed_by"], self.pharmacist.pk)
        self.assertIsNone(data["doctor"])
        self.assertEqual(data["items"][0]["instructions"], "After food")
        entry = AuditLog.objects.get(action="clinical.prescription.transcribed", object_id=str(data["id"]))
        self.assertEqual(json.loads(entry.details)["registration"], "REG-12345")

    def test_staff_doctor_may_be_named_instead(self):
        resp = self.transcribe(doctor=self.doctor.id, original_prescriber_name="", original_prescriber_registration="")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["original_prescriber_name"], self.doctor.name)

    def test_transcription_must_say_who_signed_and_when(self):
        cases = {
            "no prescriber": {"original_prescriber_name": ""},
            "no registration": {"original_prescriber_registration": ""},
            "no date": {"original_prescription_date": None},
            "future date": {"original_prescription_date": str(hospital_today() + timedelta(days=1))},
            "stale paper": {"original_prescription_date": str(hospital_today() - timedelta(days=400))},
        }
        for label, extra in cases.items():
            with self.subTest(label):
                self.assertEqual(self.transcribe(**extra).status_code, 400)
        self.assertFalse(Prescription.objects.exists())

    def test_transcription_cannot_be_written_for_another_hospital(self):
        resp = self.transcribe(self.outsider)
        self.assertIn(resp.status_code, (400, 403))
        self.assertFalse(Prescription.objects.exists())

    # --- verification before dispensing ------------------------------------

    def test_unverified_transcription_cannot_be_dispensed(self):
        rx_id = self.transcribe().json()["id"]
        resp = self.dispense(rx_id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("verified", json.dumps(resp.json()))
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.quantity, 50)

    def test_transcriber_cannot_verify_their_own_work(self):
        rx_id = self.transcribe().json()["id"]
        self.assertEqual(self.api(self.pharmacist).post(f"{URL}{rx_id}/verify/").status_code, 403)
        self.assertEqual(Prescription.objects.get(pk=rx_id).status, "Pending Verification")

    def test_second_pharmacist_verifies_then_it_can_be_dispensed(self):
        rx_id = self.transcribe().json()["id"]
        resp = self.api(self.second).post(f"{URL}{rx_id}/verify/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()["status"], resp.json()["verified_by"]), ("Confirmed", self.second.pk))
        self.assertTrue(AuditLog.objects.filter(action="clinical.prescription.verified").exists())
        self.assertEqual(self.dispense(rx_id).status_code, 201)

    def test_admin_may_verify(self):
        rx_id = self.transcribe().json()["id"]
        self.assertEqual(self.api(self.admin).post(f"{URL}{rx_id}/verify/").status_code, 200)

    def test_verify_only_once_and_only_transcriptions(self):
        rx_id = self.transcribe().json()["id"]
        self.api(self.second).post(f"{URL}{rx_id}/verify/")
        self.assertEqual(self.api(self.admin).post(f"{URL}{rx_id}/verify/").status_code, 400)
        normal = Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor)
        self.assertEqual(self.api(self.second).post(f"{URL}{normal.pk}/verify/").status_code, 400)

    def test_other_hospital_cannot_verify(self):
        rx_id = self.transcribe().json()["id"]
        resp = self.api(self.outsider, self.other).post(f"{URL}{rx_id}/verify/")
        self.assertEqual(resp.status_code, 404)

    def test_status_cannot_skip_verification(self):
        rx_id = self.transcribe().json()["id"]
        admin = self.api(self.admin)
        self.assertEqual(admin.patch(f"{URL}{rx_id}/", {"status": "Confirmed"}, format="json").status_code, 400)
        self.assertEqual(admin.patch(f"{URL}{rx_id}/", {"status": "Cancelled"}, format="json").status_code, 200)
        normal = Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor)
        self.assertEqual(admin.patch(f"{URL}{normal.pk}/", {"status": "Pending Verification"},
                                     format="json").status_code, 400)


class DispensingGuardTests(TestCase):
    """A cancelled prescription is not dispensed, and issued lines are not rewritten."""

    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Rx Guard", is_active=True)
        cls.pharmacist, _ = make_staff("guard_pharm", cls.hospital, role=StaffRole.PHARMACIST)
        cls.doctor_user, _ = make_staff("guard_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.patient = Patient.objects.create(name="Synthetic Guard", age=30, gender="Male",
                                             phone="9000009201", hospital=cls.hospital)
        cls.doctor = put_in_care(cls.doctor_user, cls.hospital, cls.patient)
        cls.medicine = Medicine.objects.create(name="Cetirizine", hospital=cls.hospital, quantity=20,
                                               price=Decimal("3.00"))

    def api(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def make_rx(self, status="Confirmed"):
        rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor,
                                         status=status)
        item = PrescriptionItem.objects.create(prescription=rx, name="Cetirizine", quantity=2)
        return rx, item

    def dispense(self, rx, item):
        return self.api(self.pharmacist).post(
            DISPENSE, {"prescription": rx.pk, "lines": [{"item": item.pk, "medicine": self.medicine.pk}]},
            format="json")

    def test_cancelled_prescription_is_not_dispensed(self):
        rx, item = self.make_rx(status="Cancelled")
        self.assertEqual(self.dispense(rx, item).status_code, 400)
        single = self.api(self.pharmacist).post("/api/pharmacy-sales/", {
            "medicine": self.medicine.pk, "hospital": self.hospital.id, "patient_name": "x", "quantity": 1,
            "prescription": rx.pk}, format="json")
        self.assertEqual(single.status_code, 400)
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.quantity, 20)

    def test_issued_medicines_cannot_be_rewritten(self):
        rx, item = self.make_rx()
        self.assertEqual(self.dispense(rx, item).status_code, 201)
        doctor = self.api(self.doctor_user)
        resp = doctor.patch(f"{URL}{rx.pk}/", {"items": [{"name": "Other", "quantity": 1}]}, format="json")
        self.assertEqual(resp.status_code, 400)
        # The item endpoint is read-only (RL-01); lines change only through the prescription.
        self.assertEqual(doctor.patch(f"/api/clinical/prescription-items/{item.pk}/", {"quantity": 9},
                                      format="json").status_code, 405)
        self.assertEqual(list(rx.items.values_list("name", "quantity")), [("Cetirizine", 2)])
