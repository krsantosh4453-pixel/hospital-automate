"""P1-10: drug schedules, Schedule H1 register, MRP cap and HSN codes (synthetic data)."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import InvoiceItem
from clinical.models import Prescription, PrescriptionItem
from config.hospital_time import hospital_today
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

from .models import Medicine

DISPENSE = "/api/pharmacy-sales/dispense-prescription/"
REGISTER = "/api/pharmacy-sales/h1-register/"


class RegulatoryTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Regulatory Hospital", is_active=True)
        self.pharmacist, _ = make_staff("reg_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.patient = Patient.objects.create(name="Synthetic Scheduled Patient", age=45, gender="Male",
                                              phone="9000000071", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="REG-1")
        self.doctor = Doctor.objects.create(hospital=self.hospital, name="Dr Synthetic Prescriber",
                                            specialization="General", phone="9000000072",
                                            registration_number="MCI-12345")
        self.h1 = Medicine.objects.create(
            name="Tab Synthetic H1 500", generic_name="levofloxacin", hospital=self.hospital, quantity=20,
            price=Decimal("10.00"), mrp=Decimal("12.00"), drug_schedule="H1", hsn_code="30049099",
            batch="H1B", expiry_date=hospital_today() + timedelta(days=300), tax_rate=Decimal("12.00"))
        self.otc = Medicine.objects.create(
            name="Synthetic ORS", hospital=self.hospital, quantity=20, price=Decimal("5.00"), batch="O1",
            expiry_date=hospital_today() + timedelta(days=300))

    def api(self, user=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user or self.pharmacist)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def dispense_h1(self, quantity=6):
        rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient, doctor=self.doctor)
        item = PrescriptionItem.objects.create(prescription=rx, name=self.h1.name, quantity=quantity)
        resp = self.api().post(DISPENSE, {"prescription": rx.pk, "lines": [{"item": item.pk, "medicine": self.h1.pk}]},
                               format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return rx

    # --- catalogue ---------------------------------------------------------

    def test_selling_price_above_mrp_is_refused(self):
        resp = self.api().patch(f"/api/pharmacy/{self.h1.pk}/", {"price": "12.50"}, format="json")

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("MRP", resp.content.decode())

    def test_selling_at_mrp_is_allowed(self):
        self.assertEqual(self.api().patch(f"/api/pharmacy/{self.h1.pk}/", {"price": "12.00"},
                                          format="json").status_code, 200)

    def test_hsn_code_must_be_4_6_or_8_digits(self):
        for bad in ("3004A", "30049"):
            with self.subTest(hsn=bad):
                resp = self.api().patch(f"/api/pharmacy/{self.h1.pk}/", {"hsn_code": bad}, format="json")
                self.assertEqual(resp.status_code, 400, resp.content)

    # --- scheduled drugs are prescription-only ------------------------------

    def test_scheduled_drug_is_not_sold_without_a_prescription(self):
        resp = self.api().post("/api/pharmacy-sales/", {
            "medicine": self.h1.pk, "hospital": self.hospital.id, "patient_name": "Walk-in", "quantity": 1,
        }, format="json")

        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("prescription", resp.content.decode())
        self.h1.refresh_from_db()
        self.assertEqual(self.h1.quantity, 20)

    def test_unscheduled_medicine_can_still_be_sold_over_the_counter(self):
        resp = self.api().post("/api/pharmacy-sales/", {
            "medicine": self.otc.pk, "hospital": self.hospital.id, "patient_name": "Walk-in", "quantity": 1,
        }, format="json")

        self.assertEqual(resp.status_code, 201, resp.content)

    # --- Schedule H1 register ----------------------------------------------

    def test_h1_register_names_prescriber_patient_drug_quantity_and_batch(self):
        self.dispense_h1()

        rows = self.api().get(REGISTER).json()["results"]

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row["prescriber"], row["prescriber_registration"]), ("Dr Synthetic Prescriber", "MCI-12345"))
        self.assertEqual((row["patient"], row["patient_uhid"]), ("Synthetic Scheduled Patient", "REG-1"))
        self.assertEqual((row["medicine"], row["schedule"], row["quantity"], row["batch"]),
                         ("Tab Synthetic H1 500", "H1", 6, "H1B"))

    def test_h1_register_leaves_out_unscheduled_sales_and_filters_by_date(self):
        self.dispense_h1()
        self.api().post("/api/pharmacy-sales/", {"medicine": self.otc.pk, "hospital": self.hospital.id,
                                                 "patient_name": "Walk-in", "quantity": 1}, format="json")
        tomorrow = (hospital_today() + timedelta(days=1)).isoformat()

        self.assertEqual(len(self.api().get(REGISTER).json()["results"]), 1)
        self.assertEqual(self.api().get(REGISTER, {"from": tomorrow}).json()["results"], [])

    def test_h1_register_is_for_pharmacy_and_management_only(self):
        nurse, _ = make_staff("reg_nurse", self.hospital, role=StaffRole.NURSE)

        self.assertEqual(self.api(nurse).get(REGISTER).status_code, 403)

    # --- HSN on the bill ---------------------------------------------------

    def test_bill_line_carries_the_medicine_hsn(self):
        rx = self.dispense_h1()

        line = InvoiceItem.objects.get(invoice__prescription=rx)

        self.assertEqual(line.hsn_code, "30049099")
