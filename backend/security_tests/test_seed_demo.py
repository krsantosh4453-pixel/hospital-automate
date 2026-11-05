"""The seed_demo command builds a synthetic demo hospital for manual testing."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from config.hospital_time import hospital_today
from hospital.models import Hospital
from patients.models import Patient

DEMO_PASSWORD = "Demo-Check-2026"
User = get_user_model()


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    def seed(self, *args, **kwargs):
        out = StringIO()
        call_command("seed_demo", *args, stdout=out, **kwargs)
        return out.getvalue()

    def login(self, username):
        client = APIClient()
        resp = client.post("/api/auth/staff/login/", {"username": username, "password": DEMO_PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.json()['access']}")
        return client

    def hospital_id(self):
        return Hospital.objects.get(name="Demo City Hospital").id

    def patient_names(self, username):
        resp = self.login(username).get("/api/patients/", {"hospital": self.hospital_id()})
        body = resp.json()
        return {row["name"] for row in (body["results"] if isinstance(body, dict) else body)}

    def test_creates_every_role_without_printing_the_password(self):
        output = self.seed(password=DEMO_PASSWORD)
        self.assertNotIn(DEMO_PASSWORD, output)
        for username in ("demo.admin", "demo.doctor1", "demo.doctor2", "demo.nurse", "demo.desk", "demo.desk.main",
                         "demo.manager", "demo.pharmacist", "demo.compounder", "demo.lab", "demo.bloodbank",
                         "demo.billing", "demo.inventory"):
            self.assertTrue(User.objects.get(username=username).check_password(DEMO_PASSWORD), username)
        self.assertTrue(Patient.objects.get(user__username="demo.patient").email_verified)

    def test_each_role_sees_what_the_rules_allow(self):
        self.seed(password=DEMO_PASSWORD)
        everyone = self.patient_names("demo.admin")
        self.assertGreaterEqual(len(everyone), 4)
        self.assertEqual(self.patient_names("demo.doctor1"), {"Demo Ravi (Cardiology OPD)", "Demo Kiran (Ward A)"})
        self.assertNotIn("Demo Meena (Ward B)", self.patient_names("demo.nurse"))
        self.assertIn("Demo Kiran (Ward A)", self.patient_names("demo.nurse"))

    def test_running_twice_does_not_duplicate(self):
        self.seed(password=DEMO_PASSWORD)
        count = Patient.objects.count()
        self.seed(password=DEMO_PASSWORD)
        self.assertEqual(Patient.objects.count(), count)

    def test_opd_tokens_belong_to_their_appointments(self):
        # An unlinked token left the appointment "without a token", so the queue issued a second one.
        from appointments.models import Appointment
        from encounters.models import QueueToken

        self.seed(password=DEMO_PASSWORD)
        for appointment in Appointment.objects.filter(hospital_id=self.hospital_id()):
            self.assertTrue(QueueToken.objects.filter(appointment=appointment).exists(), appointment.patient.name)

    def test_remove_deletes_only_demo_data(self):
        other = Hospital.objects.create(name="Real Hospital", is_active=True)
        self.seed(password=DEMO_PASSWORD)
        self.seed("--remove")
        self.assertFalse(Hospital.objects.filter(name="Demo City Hospital").exists())
        self.assertFalse(User.objects.filter(username__startswith="demo.").exists())
        self.assertTrue(Hospital.objects.filter(pk=other.pk).exists())

    def test_pharmacy_stock_is_demo_marked_and_added_once(self):
        from pharmacy.models import Medicine
        from procurement.models import StockTransaction

        self.seed(password=DEMO_PASSWORD)
        self.seed(password=DEMO_PASSWORD)
        stock = Medicine.objects.filter(hospital_id=self.hospital_id())
        self.assertGreaterEqual(stock.count(), 8)
        self.assertTrue(all(m.batch.startswith("DEMO-") for m in stock))
        self.assertEqual(StockTransaction.objects.filter(hospital_id=self.hospital_id()).count(), stock.count())
        self.assertTrue(stock.filter(expiry_date__lt=hospital_today()).exists())

    def test_expired_demo_batch_cannot_be_dispensed(self):
        from pharmacy.models import Medicine

        self.seed(password=DEMO_PASSWORD)
        expired = Medicine.objects.get(hospital_id=self.hospital_id(), batch="DEMO-IBU-OLD")
        resp = self.login("demo.pharmacist").post(
            "/api/pharmacy-sales/", {"medicine": expired.id, "hospital": self.hospital_id(),
                                     "patient_name": "Demo walk-in", "quantity": 1}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_icd10_terms_are_searchable(self):
        from terminology.models import ICD10Code

        self.seed(password=DEMO_PASSWORD)
        self.assertTrue(ICD10Code.objects.filter(code="J02.9").exists())
        count = ICD10Code.objects.count()
        self.seed(password=DEMO_PASSWORD)
        self.assertEqual(ICD10Code.objects.count(), count)

    def test_new_registration_gets_a_demo_uhid(self):
        self.seed(password=DEMO_PASSWORD)
        resp = self.login("demo.desk.main").post("/api/patients/", {
            "name": "Demo New Registration", "age": 30, "gender": "Male", "phone": "9000003099",
            "hospital": self.hospital_id()}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertRegex(resp.json()["uhid"], r"^DCH-\d{4}-000001$")

    def test_remove_works_after_medicine_was_billed_and_paid(self):
        from billing.models import Invoice
        from billing.services import record_payment
        from clinical.models import Prescription, PrescriptionItem
        from pharmacy.models import Medicine

        self.seed(password=DEMO_PASSWORD)
        patient = Patient.objects.get(name="Demo Ravi (Cardiology OPD)")
        rx = Prescription.objects.create(hospital_id=self.hospital_id(), patient=patient)
        item = PrescriptionItem.objects.create(prescription=rx, name="Paracetamol 500mg", quantity=2)
        batch = Medicine.objects.get(hospital_id=self.hospital_id(), batch="DEMO-PCM-01")
        resp = self.login("demo.pharmacist").post("/api/pharmacy-sales/dispense-prescription/", {
            "prescription": rx.id, "lines": [{"item": item.id, "medicine": batch.id}]}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        invoice = Invoice.objects.get(prescription=rx)
        record_payment(invoice, invoice.total)

        self.seed("--remove")
        self.assertFalse(Hospital.objects.filter(name="Demo City Hospital").exists())
        self.assertFalse(Medicine.objects.filter(batch__startswith="DEMO-").exists())

    def test_refuses_a_short_password(self):
        with self.assertRaises(CommandError):
            self.seed(password="short")

    @override_settings(DEBUG=False)
    def test_refuses_to_run_outside_development(self):
        with self.assertRaises(CommandError):
            self.seed(password=DEMO_PASSWORD)
