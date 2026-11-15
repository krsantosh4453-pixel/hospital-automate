"""F9: dispensed medicine is billed on the patient's invoice (synthetic data only)."""

import json
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from billing.models import Invoice, InvoiceItem, Payment
from billing.services import record_payment
from clinical.models import Prescription, PrescriptionItem
from hospital.models import Hospital
from patients.models import Patient
from pharmacy.models import Medicine, Sale
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

DISPENSE = "/api/pharmacy-sales/dispense-prescription/"


class PharmacyBillingTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Bill A", is_active=True)
        self.pharmacist, _ = make_staff("bill_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.billing, _ = make_staff("bill_clerk", self.hospital, role=StaffRole.BILLING_STAFF)
        self.patient = Patient.objects.create(name="Synthetic Billed", age=40, gender="Female",
                                              phone="9000008001", hospital=self.hospital)
        self.rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        self.pcm_item = PrescriptionItem.objects.create(prescription=self.rx, name="Paracetamol", quantity=10)
        self.ctz_item = PrescriptionItem.objects.create(prescription=self.rx, name="Cetirizine", quantity=5)
        self.pcm = Medicine.objects.create(name="Paracetamol", hospital=self.hospital, batch="P1", quantity=100,
                                           price=Decimal("2.00"))
        self.ctz = Medicine.objects.create(name="Cetirizine", hospital=self.hospital, batch="C1", quantity=50,
                                           price=Decimal("3.00"), tax_rate=Decimal("12.00"))

    def api(self, user=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user or self.pharmacist)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def dispense(self, lines=None, partial=False):
        lines = lines or [{"item": self.pcm_item.pk, "medicine": self.pcm.pk},
                          {"item": self.ctz_item.pk, "medicine": self.ctz.pk}]
        return self.api().post(DISPENSE, {"prescription": self.rx.pk, "lines": lines, "partial": partial},
                               format="json")

    def bill(self):
        return Invoice.objects.get(prescription=self.rx)

    def test_dispensing_bills_every_sale_once_and_stays_unpaid(self):
        resp = self.dispense()
        self.assertEqual(resp.status_code, 201, resp.content)
        invoice = self.bill()
        lines = {item.pharmacy_sale.medicine_id: item for item in invoice.items.all()}
        self.assertEqual(lines[self.pcm.pk].quantity, 10)
        self.assertEqual(lines[self.pcm.pk].unit_price, Decimal("2.00"))
        self.assertEqual(lines[self.ctz.pk].tax_rate, Decimal("12.00"))
        # 20 + 15 + 12% of 15
        self.assertEqual(invoice.total, Decimal("36.80"))
        self.assertEqual((invoice.patient_id, invoice.hospital_id, invoice.status),
                         (self.patient.pk, self.hospital.pk, Invoice.Status.UNPAID))
        self.assertFalse(invoice.payments.exists())
        self.assertEqual(resp.json()["invoice"]["invoice_number"], invoice.invoice_number)
        self.assertEqual(Sale.objects.filter(prescription=self.rx).count(), invoice.items.count())
        self.assertTrue(AuditLog.objects.filter(action="billing.invoice.pharmacy_charges").exists())

    def test_sales_ledger_is_unchanged(self):
        self.dispense()
        totals = sorted(Sale.objects.filter(prescription=self.rx).values_list("total", flat=True))
        self.assertEqual(totals, [Decimal("15.00"), Decimal("20.00")])

    def test_sale_lists_its_invoice_number(self):
        self.dispense()
        rows = self.api().get("/api/pharmacy-sales/", {"hospital": self.hospital.id}).json()
        rows = rows.get("results", rows)
        self.assertEqual({row["invoice_number"] for row in rows}, {self.bill().invoice_number})

    def test_partial_dispensing_adds_to_the_same_open_bill(self):
        self.dispense([{"item": self.pcm_item.pk, "medicine": self.pcm.pk, "quantity": 4}], partial=True)
        self.dispense([{"item": self.pcm_item.pk, "medicine": self.pcm.pk, "quantity": 6},
                       {"item": self.ctz_item.pk, "medicine": self.ctz.pk, "quantity": 5}], partial=True)
        self.assertEqual(Invoice.objects.filter(prescription=self.rx).count(), 1)
        self.assertEqual(self.bill().items.count(), 3)

    def test_after_a_payment_the_next_dispensing_starts_a_new_bill(self):
        self.dispense([{"item": self.pcm_item.pk, "medicine": self.pcm.pk, "quantity": 4}], partial=True)
        first = self.bill()
        record_payment(first, Decimal("3.00"))
        first.refresh_from_db()
        self.assertEqual(first.status, Invoice.Status.PARTIALLY_PAID)
        self.dispense([{"item": self.ctz_item.pk, "medicine": self.ctz.pk, "quantity": 5}], partial=True)
        bills = Invoice.objects.filter(prescription=self.rx).order_by("pk")
        self.assertEqual(bills.count(), 2)
        self.assertEqual(bills[0].items.count(), 1)
        self.assertEqual(bills[1].status, Invoice.Status.UNPAID)

    def test_a_failed_bill_undoes_the_dispensing(self):
        with mock.patch("billing.pharmacy_charges.recalculate", side_effect=RuntimeError("synthetic failure")):
            resp = self.dispense()
        self.assertEqual(resp.status_code, 500)
        self.pcm.refresh_from_db()
        self.rx.refresh_from_db()
        self.assertEqual(self.pcm.quantity, 100)
        self.assertEqual(self.rx.status, "Confirmed")
        self.assertFalse(Sale.objects.filter(prescription=self.rx).exists())
        self.assertFalse(Invoice.objects.exists())

    def test_walk_in_sale_is_not_billed_to_anyone(self):
        resp = self.api().post("/api/pharmacy-sales/", {"medicine": self.pcm.pk, "hospital": self.hospital.id,
                                                        "patient_name": "Walk-in", "quantity": 2}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertFalse(Invoice.objects.exists())

    def test_single_sale_against_a_prescription_is_billed(self):
        resp = self.api().post("/api/pharmacy-sales/", {"medicine": self.pcm.pk, "hospital": self.hospital.id,
                                                        "patient_name": self.patient.name, "quantity": 2,
                                                        "prescription": self.rx.pk}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self.bill().total, Decimal("4.00"))

    def return_sale(self, medicine, quantity):
        sale = Sale.objects.get(prescription=self.rx, medicine=medicine)
        return self.api().post(f"/api/pharmacy-sales/{sale.pk}/return/",
                               {"quantity": quantity, "reason": "Synthetic return", "restock": True}, format="json")

    def test_return_on_an_unpaid_bill_lowers_the_line(self):
        self.dispense()
        resp = self.return_sale(self.pcm, 4)
        self.assertEqual(resp.status_code, 201, resp.content)
        invoice = self.bill()
        self.assertEqual(invoice.items.get(pharmacy_sale__medicine=self.pcm).quantity, 6)
        self.assertEqual(invoice.total, Decimal("28.80"))
        self.assertFalse(invoice.payments.exists())
        self.assertIsNone(resp.json()["invoice_refund"])

    def test_return_figure_includes_gst_like_the_bill(self):
        """P1-05 / RL-11: the pharmacy shows the same tax-inclusive value the bill takes off."""
        self.dispense()

        resp = self.return_sale(self.ctz, 2)

        self.assertEqual(resp.status_code, 201, resp.content)
        # 2 x 3.00 + 12% GST
        self.assertEqual(Decimal(resp.json()["refund_amount"]), Decimal("6.72"))

    def test_return_on_a_paid_bill_refunds_the_difference(self):
        self.dispense()
        invoice = self.bill()
        record_payment(invoice, invoice.total)
        resp = self.return_sale(self.pcm, 4)
        self.assertEqual(resp.status_code, 201, resp.content)
        invoice.refresh_from_db()
        refund = invoice.payments.get(kind=Payment.Kind.REFUND)
        self.assertEqual(refund.amount, Decimal("8.00"))
        self.assertIn("RET-", refund.reference)
        self.assertEqual((invoice.total, invoice.balance_due, invoice.status),
                         (Decimal("28.80"), Decimal("0.00"), Invoice.Status.PAID))
        self.assertEqual(resp.json()["invoice_refund"], "8.00")
        entry = AuditLog.objects.get(action="billing.invoice.pharmacy_return")
        self.assertEqual(json.loads(entry.details)["refund"], "8.00")

    def test_return_on_a_partly_paid_bill_refunds_only_the_over_payment(self):
        self.dispense()
        invoice = self.bill()
        record_payment(invoice, Decimal("30.00"))
        self.return_sale(self.pcm, 4)
        invoice.refresh_from_db()
        self.assertEqual(invoice.payments.get(kind=Payment.Kind.REFUND).amount, Decimal("1.20"))
        self.assertEqual(invoice.status, Invoice.Status.PAID)

    def test_return_on_a_cancelled_bill_leaves_it_alone(self):
        self.dispense()
        invoice = self.bill()
        cancelled = self.api(self.billing).post(f"/api/billing/invoices/{invoice.pk}/cancel/", {}, format="json")
        self.assertEqual(cancelled.status_code, 200, cancelled.content)
        self.return_sale(self.pcm, 4)
        invoice.refresh_from_db()
        self.assertEqual(invoice.items.get(pharmacy_sale__medicine=self.pcm).quantity, 10)

    def test_billing_cannot_edit_or_delete_medicine_lines(self):
        self.dispense()
        invoice = self.bill()
        line = invoice.items.first()
        clerk = self.api(self.billing)
        self.assertEqual(clerk.patch(f"/api/billing/invoice-items/{line.pk}/", {"quantity": 1},
                                     format="json").status_code, 400)
        self.assertEqual(clerk.delete(f"/api/billing/invoice-items/{line.pk}/").status_code, 400)
        self.assertEqual(clerk.delete(f"/api/billing/invoices/{invoice.pk}/").status_code, 400)
        self.assertEqual(clerk.patch(f"/api/billing/invoices/{invoice.pk}/", {"items_data": []},
                                     format="json").status_code, 400)
        self.assertEqual(InvoiceItem.objects.filter(invoice=invoice).count(), 2)

    def test_billing_staff_take_payment_on_the_medicine_bill(self):
        self.dispense()
        invoice = self.bill()
        resp = self.api(self.billing).post("/api/billing/payments/", {"invoice": invoice.pk, "amount": "10.00",
                                                                      "payment_method": "Cash"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PARTIALLY_PAID)

    def test_gst_rate_is_validated(self):
        resp = self.api().patch(f"/api/pharmacy/{self.pcm.pk}/", {"tax_rate": "101"}, format="json")
        self.assertEqual(resp.status_code, 400)


class PharmacyBillingIsolationTests(TestCase):
    def test_other_hospital_cannot_see_the_medicine_bill(self):
        hospital = Hospital.objects.create(name="Synthetic Bill Iso A", is_active=True)
        other = Hospital.objects.create(name="Synthetic Bill Iso B", is_active=True)
        patient = Patient.objects.create(name="Synthetic Iso", age=30, gender="Male", phone="9000008101",
                                         hospital=hospital)
        rx = Prescription.objects.create(hospital=hospital, patient=patient)
        item = PrescriptionItem.objects.create(prescription=rx, name="Paracetamol", quantity=1)
        medicine = Medicine.objects.create(name="Paracetamol", hospital=hospital, quantity=5, price=Decimal("2.00"))
        pharmacist, _ = make_staff("bill_iso_pharm", hospital, role=StaffRole.PHARMACIST)
        outsider, _ = make_staff("bill_iso_clerk", other, role=StaffRole.BILLING_STAFF)

        client = APIClient(raise_request_exception=False)
        client.force_authenticate(pharmacist)
        client.post(DISPENSE, {"prescription": rx.pk, "lines": [{"item": item.pk, "medicine": medicine.pk}]},
                    format="json")
        invoice = Invoice.objects.get(prescription=rx)

        client.force_authenticate(outsider)
        self.assertEqual(client.get(f"/api/billing/invoices/{invoice.pk}/").status_code, 404)
        listed = client.get("/api/billing/invoices/", {"hospital": other.id}).json()
        self.assertEqual(listed.get("results", listed), [])
