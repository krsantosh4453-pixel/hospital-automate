"""
BUG-002 (E2E audit 2026-11-24): bills with paise must be payable exactly.
Every case goes through the real invoice and payment API. Synthetic data only.

Reconciliation checked throughout: total = net paid + balance due, to the paisa.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from billing.models import Invoice, Payment
from billing.services import record_payment, record_refund
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class DecimalPaymentTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Paise Hospital", is_active=True)
        self.user, _ = make_staff("paise_billing", self.hospital, role=StaffRole.BILLING_STAFF)
        self.patient = Patient.objects.create(name="Synthetic Paise Patient", age=40, gender="Female",
                                              phone="9000007001", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, is_active=True)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

    # Helpers ---------------------------------------------------------------

    def invoice(self, unit_price, tax_rate="0.00"):
        response = self.client.post(f"/api/billing/invoices/?hospital={self.hospital.pk}", {
            "patient": self.patient.pk,
            "items_data": [{"description": "Synthetic service", "quantity": 1,
                            "unit_price": unit_price, "tax_rate": tax_rate}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.data["id"]

    def pay(self, invoice_id, amount, key=""):
        body = {"invoice": invoice_id, "amount": amount, "payment_method": "Cash"}
        if key:
            body["idempotency_key"] = key
        return self.client.post(f"/api/billing/payments/?hospital={self.hospital.pk}", body, format="json")

    def state(self, invoice_id):
        data = self.client.get(f"/api/billing/invoices/{invoice_id}/").json()
        return data["status"], Decimal(data["total_amount"]), Decimal(data["total_paid"]), Decimal(data["balance_due"])

    def assert_reconciles(self, invoice_id):
        _status, total, paid, balance = self.state(invoice_id)
        self.assertEqual(total, paid + balance, "invoice total must equal paid + balance")
        db = Invoice.objects.get(pk=invoice_id)
        db_paid = sum((p.amount if p.kind == Payment.Kind.PAYMENT else -p.amount) for p in db.payments.all())
        self.assertEqual(db.total, db_paid + balance)

    # Required cases ----------------------------------------------------------

    def test_1_exact_decimal_payment_pays_the_bill(self):
        invoice_id = self.invoice("30.00", "12.00")  # ₹30 + 12% GST = ₹33.60
        self.assertEqual(self.state(invoice_id)[1], Decimal("33.60"))

        response = self.pay(invoice_id, "33.60")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.state(invoice_id), ("Paid", Decimal("33.60"), Decimal("33.60"), Decimal("0.00")))
        self.assert_reconciles(invoice_id)

    def test_2_partial_decimal_payment(self):
        invoice_id = self.invoice("30.00", "12.00")

        self.assertEqual(self.pay(invoice_id, "10.25").status_code, 201)

        self.assertEqual(self.state(invoice_id), ("Partially Paid", Decimal("33.60"), Decimal("10.25"), Decimal("23.35")))
        self.assert_reconciles(invoice_id)

    def test_3_multiple_payments_add_up_to_the_paisa(self):
        invoice_id = self.invoice("100.50")
        for amount, status in (("30.25", "Partially Paid"), ("20.25", "Partially Paid"), ("50.00", "Paid")):
            self.assertEqual(self.pay(invoice_id, amount).status_code, 201)
            self.assertEqual(self.state(invoice_id)[0], status)
            self.assert_reconciles(invoice_id)
        self.assertEqual(self.state(invoice_id), ("Paid", Decimal("100.50"), Decimal("100.50"), Decimal("0.00")))

    def test_4_overpayment_by_one_paisa_is_refused(self):
        invoice_id = self.invoice("30.00", "12.00")

        response = self.pay(invoice_id, "33.61")

        self.assertEqual(response.status_code, 400)
        self.assertIn("outstanding balance", str(response.content))
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(self.state(invoice_id), ("Unpaid", Decimal("33.60"), Decimal("0.00"), Decimal("33.60")))

    def test_5_and_6_zero_and_negative_payments_are_refused(self):
        invoice_id = self.invoice("30.00", "12.00")
        for amount in ("0.00", "0", "-10.00"):
            with self.subTest(amount=amount):
                self.assertEqual(self.pay(invoice_id, amount).status_code, 400)
        self.assertFalse(Payment.objects.exists())

    def test_7_more_than_two_decimals_is_refused_never_rounded(self):
        # Policy: INR amounts carry at most 2 decimal places; anything finer is
        # refused (never rounded), at the API and in the service itself.
        invoice_id = self.invoice("30.00", "12.00")
        for amount in ("10.999", "10.001", "33.595"):
            with self.subTest(amount=amount):
                self.assertEqual(self.pay(invoice_id, amount).status_code, 400)
        self.assertFalse(Payment.objects.exists())

        invoice = Invoice.objects.get(pk=invoice_id)
        with self.assertRaises((ValidationError, DjangoValidationError)):
            record_payment(invoice, Decimal("10.999"), user=self.user)
        self.assertFalse(Payment.objects.exists())

    def test_7b_a_refund_with_more_than_two_decimals_is_refused(self):
        invoice_id = self.invoice("30.00", "12.00")
        self.pay(invoice_id, "33.60")
        invoice = Invoice.objects.get(pk=invoice_id)
        with self.assertRaises((ValidationError, DjangoValidationError)):
            record_refund(invoice, Decimal("1.005"), "Synthetic refund", user=self.user)
        self.assertEqual(Payment.objects.filter(kind=Payment.Kind.REFUND).count(), 0)

    def test_8_whole_rupee_bills_still_work(self):
        invoice_id = self.invoice("100.00")
        self.assertEqual(self.pay(invoice_id, "100").status_code, 201)
        self.assertEqual(self.state(invoice_id), ("Paid", Decimal("100.00"), Decimal("100.00"), Decimal("0.00")))

    def test_9_the_same_payment_sent_twice_is_recorded_once(self):
        invoice_id = self.invoice("30.00", "12.00")

        first = self.pay(invoice_id, "10.25", key="synthetic-key-1")
        second = self.pay(invoice_id, "10.25", key="synthetic-key-1")

        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(self.state(invoice_id)[3], Decimal("23.35"))

    def test_10_a_second_payment_for_the_same_balance_is_refused(self):
        # Sequential form of the race; true parallel payments are covered on
        # PostgreSQL by security_tests.test_concurrency (row lock).
        invoice_id = self.invoice("30.00", "12.00")
        self.assertEqual(self.pay(invoice_id, "33.60", key="tab-1").status_code, 201)
        self.assertEqual(self.pay(invoice_id, "33.60", key="tab-2").status_code, 400)
        self.assertEqual(Payment.objects.count(), 1)
        self.assert_reconciles(invoice_id)

    def test_11_payment_history_keeps_each_amount_exactly(self):
        invoice_id = self.invoice("100.50")
        for amount in ("30.25", "20.25", "50.00"):
            self.pay(invoice_id, amount)

        rows = self.client.get(f"/api/billing/payments/?hospital={self.hospital.pk}&invoice={invoice_id}").json()
        rows = rows["results"] if isinstance(rows, dict) else rows

        self.assertEqual(sorted(r["amount"] for r in rows), ["20.25", "30.25", "50.00"])
        for row in rows:
            self.assertEqual(row["invoice"], invoice_id)
            self.assertEqual(row["kind"], "payment")
            self.assertTrue(row["paid_at"])
            self.assertTrue(row["receipt_number"])
