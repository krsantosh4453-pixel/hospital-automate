"""
End-to-end hospital workflows through the real API with synthetic data.

Covers the documented scenarios: registration (1), appointment -> visit ->
queue (2), encounter + vitals + diagnosis (3), prescription -> pharmacy (5),
lab order -> sample -> result (6), admission -> bed -> nursing -> discharge
(7), patient portal sees only released own records (10) and restricted
role actions (11). Tenant isolation (12), AI approval (4), billing (8),
stock (9) and provider failure (14) are in the other security_tests files.
"""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from doctors.models import Doctor
from hospital.models import Bed, Hospital, Room, Ward
from patients.models import Patient
from pharmacy.models import Medicine
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_on_duty

User = get_user_model()
TODAY = datetime.date.today()


class HospitalWorkflowTests(TestCase):
    RAISE = False
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic General Hospital", is_active=True)
        role = lambda name, r: make_staff(name, self.hospital, role=r)[0]  # noqa: E731
        self.reception = role("wf_reception", StaffRole.RECEPTIONIST)
        self.doctor_user = role("wf_doctor", StaffRole.DOCTOR)
        self.nurse = role("wf_nurse", StaffRole.NURSE)
        self.lab = role("wf_lab", StaffRole.LAB_STAFF)
        self.pharmacist = role("wf_pharmacist", StaffRole.PHARMACIST)
        self.doctor = Doctor.objects.create(
            hospital=self.hospital, user=self.doctor_user, name="Dr Workflow",
            specialization="Medicine", phone="9000000040",
        )

    def api(self, user):
        client = APIClient(raise_request_exception=self.RAISE)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def ok(self, resp, code=(200, 201)):
        codes = code if isinstance(code, tuple) else (code,)
        self.assertIn(resp.status_code, codes, getattr(resp, "content", b"")[:500])
        return resp.json() if resp.content else None

    def register_patient(self):
        data = self.ok(self.api(self.reception).post("/api/patients/", {
            "name": "Synthetic Asha", "age": 52, "gender": "Female", "phone": "9000000041",
            "hospital": self.hospital.id,
        }, format="json"), 201)
        fetched = self.ok(self.api(self.reception).get(f"/api/patients/{data['id']}/"))
        self.assertEqual(fetched["name"], "Synthetic Asha")
        return Patient.objects.get(pk=data["id"])

    def test_opd_consultation_prescription_and_lab(self):
        patient = self.register_patient()                                         # 1
        reception = self.api(self.reception)
        appt = self.ok(reception.post("/api/appointments/", {
            "patient": patient.id, "doctor": self.doctor.id, "hospital": self.hospital.id,
            "appointment_date": str(TODAY), "appointment_time": "10:30", "reason": "Fever",
        }, format="json"), 201)
        token = self.ok(reception.post("/api/encounters/queue-tokens/issue/", {
            "appointment": appt["id"], "chief_complaint": "Fever 3 days",
        }, format="json"))                                                        # 2
        visit_id = token["visit"]
        self.assertTrue(token["token_number"] >= 1)

        doctor = self.api(self.doctor_user)
        self.ok(self.api(self.nurse).post("/api/clinical/vitals/", {
            "visit": visit_id, "temperature": "38.40", "heart_rate": 96, "spo2": 97,
        }, format="json"), 201)
        diagnosis = self.ok(doctor.post("/api/clinical/diagnoses/", {
            "visit": visit_id, "name": "Viral fever", "icd10_code": "A99", "diagnosis_type": "Provisional",
        }, format="json"), 201)                                                   # 3
        self.assertEqual(diagnosis["recorded_by"], self.doctor_user.id)

        # 11: reception cannot write clinical data.
        self.assertEqual(reception.post("/api/clinical/diagnoses/", {
            "visit": visit_id, "name": "Self-diagnosed",
        }, format="json").status_code, 403)

        rx = self.ok(doctor.post("/api/clinical/prescriptions/", {
            "hospital": self.hospital.id, "patient": patient.id, "doctor": self.doctor.id, "visit": visit_id,
            "items": [{"name": "Synthetic Paracetamol 500", "dosage": "1 tab", "frequency": "TDS",
                       "duration": "3 days", "quantity": 9}],
        }, format="json"), 201)
        medicine = Medicine.objects.create(
            name="Synthetic Paracetamol 500", hospital=self.hospital, quantity=100, price=Decimal("1.50"),
            expiry_date=TODAY + datetime.timedelta(days=365),
        )
        sale = self.ok(self.api(self.pharmacist).post("/api/pharmacy-sales/", {
            "medicine": medicine.id, "hospital": self.hospital.id, "patient_name": patient.name,
            "quantity": 9, "prescription": rx["id"],
        }, format="json"), 201)                                                   # 5
        self.assertEqual(Decimal(sale["total"]), Decimal("13.50"))
        medicine.refresh_from_db()
        self.assertEqual(medicine.quantity, 91)

        test = self.ok(doctor.post("/api/laboratory/", {
            "name": "CBC", "patient": patient.id, "hospital": self.hospital.id, "visit": visit_id,
            "doctor": self.doctor.id,
        }, format="json"), 201)
        nurse = self.api(self.nurse)
        lab = self.api(self.lab)
        base = f"/api/laboratory/{test['id']}"
        self.ok(nurse.post(f"{base}/collect_sample/", {"sample_type": "Blood"}, format="json"), 201)
        self.ok(nurse.post(f"{base}/dispatch_sample/", {}, format="json"), 201)
        self.assertEqual(nurse.post(f"{base}/receive_sample/", {}, format="json").status_code, 403)
        self.ok(lab.post(f"{base}/receive_sample/", {}, format="json"))
        self.ok(lab.post(f"{base}/start_processing/", {}, format="json"))
        self.ok(lab.post(f"{base}/enter_result/", {"result_text": "Hb 12.1 g/dL"}, format="json"), 201)
        self.assertEqual(doctor.post(f"{base}/verify_result/", {}, format="json").status_code, 403)
        self.ok(lab.post(f"{base}/verify_result/", {}, format="json"))
        # Status cannot be forged by editing the record.
        self.ok(doctor.patch(f"{base}/", {"status": "Released", "result": "forged"}, format="json"))
        released_before = self.ok(lab.get(f"{base}/"))
        self.assertEqual(released_before["status"], "Verified")
        self.ok(lab.post(f"{base}/release_result/", {}, format="json"))           # 6

        # 10: the patient's own login sees only released results, and only theirs.
        login = User.objects.create_user(username="wf_patient_login", password="Synthetic-Pass-123")
        patient.user = login
        patient.save(update_fields=["user"])
        other = Patient.objects.create(name="Synthetic Other", age=20, gender="Male",
                                       phone="9000000042", hospital=self.hospital)
        # Another patient's test, ordered by the lab (the doctor has no care of them).
        self.ok(lab.post("/api/laboratory/", {"name": "LFT", "patient": other.id,
                                                  "hospital": self.hospital.id}, format="json"), 201)
        self.ok(doctor.post("/api/laboratory/", {"name": "ESR", "patient": patient.id,
                                                  "hospital": self.hospital.id}, format="json"), 201)
        portal = APIClient(raise_request_exception=False)
        portal.force_authenticate(login)
        rows = portal.get("/api/laboratory/").json()
        rows = rows.get("results", rows)
        self.assertEqual([(r["name"], r["status"]) for r in rows], [("CBC", "Released")])
        self.assertEqual(portal.post("/api/laboratory/", {"name": "X", "patient": patient.id},
                                     format="json").status_code, 403)
        self.assertEqual(portal.get(f"/api/patients/{other.id}/").status_code, 404)

    def test_admission_bed_nursing_and_discharge(self):
        patient = self.register_patient()
        ward = Ward.objects.create(hospital=self.hospital, name="Synthetic Ward")
        room = Room.objects.create(ward=ward, room_number="101")
        bed = Bed.objects.create(room=room, bed_number="101-A", status="Available")
        put_on_duty(self.nurse, self.hospital, ward)

        doctor = self.api(self.doctor_user)
        nurse = self.api(self.nurse)
        admission = self.ok(doctor.post("/api/ipd/admissions/", {
            "patient": patient.id, "hospital": self.hospital.id, "reason": "Observation",
            "admitting_doctor": self.doctor.id,
        }, format="json"), 201)
        base = f"/api/ipd/admissions/{admission['id']}"
        self.ok(nurse.post(f"{base}/allocate_bed/", {"bed_id": bed.id}, format="json"), 201)
        bed.refresh_from_db()
        self.assertEqual(bed.status, "Occupied")

        self.ok(nurse.post("/api/nurses/notes/", {
            "patient": patient.id, "admission": admission["id"], "hospital": self.hospital.id,
            "note_type": "Progress", "note": "Comfortable overnight.",
        }, format="json"), 201)

        self.ok(doctor.post(f"{base}/initiate_discharge/", {}, format="json"))
        self.assertEqual(doctor.post(f"{base}/complete_discharge/", {}, format="json").status_code, 400)
        summary = self.ok(doctor.post("/api/ipd/discharge-summaries/", {
            "admission": admission["id"], "summary": "Recovered; review in 1 week.", "finalized": True,
        }, format="json"), 201)
        self.assertFalse(summary["finalized"])                                    # cannot self-finalize by field
        self.ok(doctor.post(f"/api/ipd/discharge-summaries/{summary['id']}/finalize/", {}, format="json"))
        self.assertEqual(doctor.patch(f"/api/ipd/discharge-summaries/{summary['id']}/",
                                      {"summary": "edited"}, format="json").status_code, 400)
        done = self.ok(doctor.post(f"{base}/complete_discharge/", {}, format="json"))  # 7
        self.assertEqual(done["status"], "Discharged")
        bed.refresh_from_db()
        self.assertEqual(bed.status, "Available")
