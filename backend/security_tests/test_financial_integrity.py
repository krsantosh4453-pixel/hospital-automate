"""Billing and stock integrity with synthetic data (end-to-end scenarios 8 and 9)."""

import datetime
from decimal import Decimal

from django.db.models import Sum
from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import Invoice, Payment
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from pharmacy.models import Medicine
from procurement.models import StockTransaction
from users.models import StaffRole

from .test_tenant_isolation import make_staff


class FinancialIntegrityTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Billing Hospital", is_active=True)
        self.biller, _ = make_staff("biller", self.hospital, role=StaffRole.BILLING_STAFF)
        self.pharmacist, _ = make_staff("pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.patient = Patient.objects.create(
            name="Synthetic Payer", age=33, gender="Female", phone="9000000030", hospital=self.hospital
        )
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="BILL-1")

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def make_invoice(self, client):
        resp = client.post("/api/billing/invoices/", {
            "patient": self.patient.id,
            "discount": "10.00",
            "total": "1.00",            # ignored
            "status": "Paid",           # ignored
            "items_data": [
                {"description": "Consultation", "quantity": 1, "unit_price": "500.00", "tax_rate": "0"},
                {"description": "Lab", "quantity": 3, "unit_price": "33.33", "tax_rate": "18", "subtotal": "1"},
            ],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return Invoice.objects.get(pk=resp.json()["id"])

    def test_invoice_totals_are_server_computed(self):
        invoice = self.make_invoice(self.client_for(self.biller))
        # 500 + 99.99 = 599.99; tax 18% of 99.99 = 18.00; minus 10 discount
        self.assertEqual(invoice.total, Decimal("607.99"))
        self.assertEqual(invoice.tax, Decimal("18.00"))
        self.assertEqual(invoice.status, Invoice.Status.UNPAID)
        self.assertEqual(sorted(invoice.items.values_list("subtotal", flat=True)),
                         [Decimal("99.99"), Decimal("500.00")])

    def test_discount_cannot_exceed_bill(self):
        resp = self.client_for(self.biller).post("/api/billing/invoices/", {
            "patient": self.patient.id, "discount": "999",
            "items_data": [{"description": "X", "quantity": 1, "unit_price": "10.00"}],
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Invoice.objects.exists())

    def test_payment_flow_balance_overpay_idempotency_refund(self):
        client = self.client_for(self.biller)
        invoice = self.make_invoice(client)
        over = client.post("/api/billing/payments/", {"invoice": invoice.id, "amount": "700.00"}, format="json")
        self.assertEqual(over.status_code, 400)
        zero = client.post("/api/billing/payments/", {"invoice": invoice.id, "amount": "0"}, format="json")
        self.assertEqual(zero.status_code, 400)

        first = client.post("/api/billing/payments/", {"invoice": invoice.id, "amount": "300.00"},
                            format="json", HTTP_IDEMPOTENCY_KEY="till-7-0001")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertTrue(first.json()["receipt_number"].startswith("RCPT-"))
        retry = client.post("/api/billing/payments/", {"invoice": invoice.id, "amount": "300.00"},
                            format="json", HTTP_IDEMPOTENCY_KEY="till-7-0001")
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(Payment.objects.count(), 1)

        detail = client.get(f"/api/billing/invoices/{invoice.id}/").json()
        self.assertEqual(Decimal(str(detail["balance_due"])), Decimal("307.99"))
        self.assertEqual(detail["status"], "Partially Paid")

        rest = client.post("/api/billing/payments/", {"invoice": invoice.id, "amount": "307.99"}, format="json")
        self.assertEqual(rest.status_code, 201)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)

        payment_id = first.json()["id"]
        self.assertEqual(client.patch(f"/api/billing/payments/{payment_id}/", {"amount": "1"}, format="json").status_code, 405)
        self.assertEqual(client.delete(f"/api/billing/payments/{payment_id}/").status_code, 405)

        too_much = client.post(f"/api/billing/invoices/{invoice.id}/refund/", {"amount": "1000", "reason": "x"}, format="json")
        self.assertEqual(too_much.status_code, 400)
        refund = client.post(f"/api/billing/invoices/{invoice.id}/refund/", {"amount": "100", "reason": "Test not done"}, format="json")
        self.assertEqual(refund.status_code, 201, refund.content)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PARTIALLY_PAID)
        self.assertEqual(invoice.total_paid, Decimal("507.99"))

        # Paid lines cannot be rewritten afterwards.
        resp = client.patch(f"/api/billing/invoices/{invoice.id}/", {"items_data": []}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_sale_uses_catalogue_price_and_keeps_ledger_consistent(self):
        client = self.client_for(self.pharmacist)
        created = client.post("/api/pharmacy/", {
            "name": "Synthetic Paracetamol", "hospital": self.hospital.id, "quantity": 20, "price": "2.50",
            "expiry_date": str(datetime.date.today() + datetime.timedelta(days=200)),
        }, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        med_id = created.json()["id"]

        sale = client.post("/api/pharmacy-sales/", {
            "medicine": med_id, "hospital": self.hospital.id, "patient_name": "Synthetic Payer",
            "quantity": 4, "unit_price": "0.01",
        }, format="json")
        self.assertEqual(sale.status_code, 201, sale.content)
        self.assertEqual(Decimal(sale.json()["total"]), Decimal("10.00"))

        oversell = client.post("/api/pharmacy-sales/", {
            "medicine": med_id, "hospital": self.hospital.id, "patient_name": "Synthetic Payer", "quantity": 50,
        }, format="json")
        self.assertEqual(oversell.status_code, 400)

        medicine = Medicine.objects.get(pk=med_id)
        ledger = StockTransaction.objects.filter(medicine=medicine)
        received = ledger.filter(transaction_type="IN").aggregate(n=Sum("quantity"))["n"] or 0
        issued = ledger.filter(transaction_type="OUT").aggregate(n=Sum("quantity"))["n"] or 0
        self.assertEqual(medicine.quantity, 16)
        self.assertEqual(received - issued, medicine.quantity)

    def test_expired_batch_cannot_be_dispensed(self):
        medicine = Medicine.objects.create(
            name="Synthetic Expired", hospital=self.hospital, quantity=5, price=Decimal("1.00"),
            expiry_date=datetime.date.today() - datetime.timedelta(days=1),
        )
        resp = self.client_for(self.pharmacist).post("/api/pharmacy-sales/", {
            "medicine": medicine.id, "hospital": self.hospital.id, "patient_name": "Synthetic Payer", "quantity": 1,
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        medicine.refresh_from_db()
        self.assertEqual(medicine.quantity, 5)
