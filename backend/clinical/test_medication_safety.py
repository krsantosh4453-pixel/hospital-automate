"""Medication safety check when prescribing (F7 Phase A): allergies, duplicates, starter interaction list."""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.medication_safety import check_items
from clinical.models import Allergy, Prescription
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from pharmacy.models import Medicine
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

RX_URL = "/api/clinical/prescriptions/"


class MedicationSafetyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Safety Hospital", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        cls.patient = Patient.objects.create(name="Synthetic Safety Patient", age=60, gender="Male",
                                             phone="9000000051", hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="SAFE-1")
        cls.doctor_user, _ = make_staff("safety_doctor", cls.hospital, role=StaffRole.DOCTOR)
        put_in_care(cls.doctor_user, cls.hospital, cls.patient)
        cls.doctor = Doctor.objects.get(user=cls.doctor_user, hospital=cls.hospital)
        Medicine.objects.create(name="Brufen 400", generic_name="ibuprofen", hospital=cls.hospital,
                                quantity=10, price=Decimal("2"))

    def setUp(self):
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.doctor_user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def alerts(self, *names):
        return check_items(self.hospital, self.patient, list(names))

    def kinds(self, alerts):
        return {(alert["type"], alert["severity"]) for alert in alerts}

    # --- the check itself -------------------------------------------------

    def test_brand_name_resolved_through_the_catalogue_meets_an_allergy_class(self):
        Allergy.objects.create(patient=self.patient, hospital=self.hospital, name="NSAIDs", reaction="Hives")

        alerts = self.alerts("Brufen 400")

        self.assertIn(("allergy", "high"), self.kinds(alerts))
        self.assertIn("Hives", alerts[0]["message"])

    def test_allergy_recorded_in_another_hospital_is_not_used(self):
        Allergy.objects.create(patient=self.patient, hospital=self.other_hospital, name="Penicillin")

        self.assertNotIn(("allergy", "high"), self.kinds(self.alerts("Cap Amoxicillin 500")))

    def test_salt_written_in_free_text_meets_the_interaction_list(self):
        alerts = self.alerts("Tab Warfarin 5 mg", "Tab Ibuprofen 400")

        self.assertIn(("interaction", "high"), self.kinds(alerts))

    def test_moderate_interaction_and_duplicate_salt(self):
        alerts = self.alerts("Tab Clopidogrel 75", "Cap Omeprazole 20", "Brufen 400", "Tab Ibuprofen 200")

        self.assertIn(("interaction", "moderate"), self.kinds(alerts))
        self.assertIn(("duplicate", "moderate"), self.kinds(alerts))

    def test_unknown_medicine_is_reported_not_silently_passed(self):
        alerts = self.alerts("Crocin Advance")

        self.assertEqual(self.kinds(alerts), {("unidentified", "info")})

    def test_safe_prescription_has_no_alerts(self):
        self.assertEqual(self.alerts("Tab Paracetamol 500"), [])

    # --- the API ----------------------------------------------------------

    def prescribe(self, *names, reason=None):
        payload = {"hospital": self.hospital.id, "patient": self.patient.id, "doctor": self.doctor.id,
                   "items": [{"name": name, "quantity": 1} for name in names]}
        if reason is not None:
            payload["safety_override_reason"] = reason
        return self.client.post(RX_URL, payload, format="json")

    def test_safety_check_endpoint_returns_alerts_and_rule_status(self):
        response = self.client.post(f"{RX_URL}safety-check/", {
            "hospital": self.hospital.id, "patient": self.patient.id,
            "items": [{"name": "Tab Sildenafil 50"}, {"name": "Tab Isosorbide Mononitrate 20"}],
        }, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["alerts"][0]["rule"], "pde5-nitrate")
        self.assertIn("pending", body["review_status"])

    def test_high_alert_blocks_until_a_reason_is_given_then_is_stored_and_audited(self):
        blocked = self.prescribe("Tab Warfarin 5 mg", "Tab Diclofenac 50")
        self.assertEqual(blocked.status_code, 400, blocked.content)
        self.assertIn("safety_override_reason", blocked.content.decode())
        self.assertEqual(Prescription.objects.count(), 0)

        allowed = self.prescribe("Tab Warfarin 5 mg", "Tab Diclofenac 50", reason="Short course, INR checked today")

        self.assertEqual(allowed.status_code, 201, allowed.content)
        rx = Prescription.objects.get()
        self.assertEqual(rx.safety_override_reason, "Short course, INR checked today")
        self.assertEqual(rx.safety_alerts[0]["rule"], "anticoagulant-nsaid")
        self.assertTrue(AuditLog.objects.filter(action="clinical.prescription.safety_override").exists())

    def test_moderate_alert_does_not_block_and_no_reason_is_kept(self):
        response = self.prescribe("Tab Clopidogrel 75", "Cap Omeprazole 20", reason="not needed")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Prescription.objects.get().safety_override_reason, "")

    def test_safety_check_refuses_a_hospital_the_user_is_not_in(self):
        response = self.client.post(f"{RX_URL}safety-check/", {
            "hospital": self.other_hospital.id, "patient": self.patient.id, "items": [],
        }, format="json")

        self.assertEqual(response.status_code, 403)
