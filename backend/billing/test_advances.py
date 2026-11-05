"""Advance payments (H4) on synthetic data: deposit, adjust, return, refund."""

import json
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from billing.models import AdvanceAccount, AdvanceTransaction, Invoice, InvoiceItem, Payment
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class AdvancePaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Advance", is_active=True)
        cls.other = Hospital.objects.create(name="Synthetic Elsewhere", is_active=True)
        cls.patient = Patient.objects.create(name="Synthetic Depositor", age=45, gender="Male",
                                             phone="9000000701", hospital=cls.hospital)
        PatientHospital.objects.create(patient=cls.patient, hospital=cls.hospital, uhid="ADV-1")
        cls.desk, _ = make_staff("adv_desk", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.billing, _ = make_staff("adv_billing", cls.hospital, role=StaffRole.BILLING_STAFF)
        cls.outsider, _ = make_staff("adv_outsider", cls.other, role=StaffRole.BILLING_STAFF)

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def deposit(self, amount="1000.00", user=None, **extra):
        body = {"patient": self.patient.id, "amount": amount, "payment_method": "Cash", **extra}
        return self.client_for(user or self.desk).post("/api/billing/advances/deposit/", body, format="json")

    def invoice(self, total="600.00", number="INV-ADV-1"):
        invoice = Invoice.objects.create(patient=self.patient, hospital=self.hospital, invoice_number=number,
                                         total=Decimal(total))
        InvoiceItem.objects.create(invoice=invoice, description="Room", quantity=1, unit_price=Decimal(total),
                                   subtotal=Decimal(total))
        return invoice

    def apply(self, invoice, amount, user=None, **extra):
        return self.client_for(user or self.desk).post(f"/api/billing/invoices/{invoice.id}/apply-advance/",
                                                       {"amount": amount, **extra}, format="json")

    def balance(self):
        return AdvanceAccount.objects.get(patient=self.patient, hospital=self.hospital).balance

    def test_deposit_creates_a_balance_with_receipt_and_audit(self):
        resp = self.deposit()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Decimal(resp.json()["balance"]), Decimal("1000.00"))
        move = resp.json()["transactions"][0]
        self.assertEqual((move["kind"], move["created_by_name"]), ("deposit", "adv_desk"))
        self.assertTrue(move["receipt_number"].startswith("ADV-"))
        entry = AuditLog.objects.get(action="billing.advance.deposit")
        self.assertEqual(entry.user, self.desk)
        self.assertEqual(json.loads(entry.details)["balance_after"], "1000.00")

    def test_a_resent_deposit_is_counted_once(self):
        for _ in range(2):
            self.deposit(idempotency_key="dep-1")
        self.assertEqual(self.balance(), Decimal("1000.00"))
        self.assertEqual(AdvanceTransaction.objects.count(), 1)

    def test_adjusting_pays_the_bill_and_lowers_the_advance(self):
        self.deposit()
        invoice = self.invoice()
        resp = self.apply(invoice, "400.00")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["invoice"]["status"], "Partially Paid")
        self.assertEqual(self.balance(), Decimal("600.00"))
        self.assertEqual(Payment.objects.get(invoice=invoice).payment_method, "Advance")

        too_much = self.apply(invoice, "300.00")  # only 200 is still due
        self.assertEqual(too_much.status_code, 400)
        self.assertEqual(self.apply(invoice, "200.00").json()["invoice"]["status"], "Paid")
        self.assertEqual(self.balance(), Decimal("400.00"))

    def test_no_adjustment_beyond_the_advance_or_on_a_cancelled_bill(self):
        self.deposit("100.00")
        invoice = self.invoice()
        self.assertEqual(self.apply(invoice, "150.00").status_code, 400)
        cancelled = self.invoice(number="INV-ADV-2")
        cancelled.status = Invoice.Status.CANCELLED
        cancelled.save()
        self.assertEqual(self.apply(cancelled, "50.00").status_code, 400)
        self.assertEqual(self.balance(), Decimal("100.00"))
        self.assertFalse(Payment.objects.exists())

    def test_a_resent_adjustment_is_deducted_once(self):
        self.deposit()
        invoice = self.invoice()
        first = self.apply(invoice, "100.00", idempotency_key="apply-1")
        again = self.apply(invoice, "100.00", idempotency_key="apply-1")
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(self.balance(), Decimal("900.00"))
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)

    def test_advance_cannot_be_spent_through_the_plain_payment_api(self):
        self.deposit()
        invoice = self.invoice()
        resp = self.client_for(self.desk).post("/api/billing/payments/",
                                               {"invoice": invoice.id, "amount": "100.00", "payment_method": "Advance"},
                                               format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(self.balance(), Decimal("1000.00"))

    def test_bill_refund_can_go_back_to_the_advance_but_only_advance_money(self):
        self.deposit()
        invoice = self.invoice()
        self.apply(invoice, "300.00")
        self.client_for(self.billing).post("/api/billing/payments/", {"invoice": invoice.id, "amount": "100.00"},
                                           format="json")
        refund = lambda amount: self.client_for(self.billing).post(  # noqa: E731
            f"/api/billing/invoices/{invoice.id}/refund/",
            {"amount": amount, "reason": "Room charge reduced", "payment_method": "Advance"}, format="json")
        self.assertEqual(refund("350.00").status_code, 400)  # 100 of the 400 paid was cash
        self.assertEqual(refund("300.00").status_code, 201)
        self.assertEqual(self.balance(), Decimal("1000.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "Partially Paid")
        kinds = list(AdvanceTransaction.objects.order_by("id").values_list("kind", flat=True))
        self.assertEqual(kinds, ["deposit", "applied", "returned"])

    def test_refund_to_patient_needs_billing_staff_a_reason_and_balance(self):
        account_id = self.deposit("500.00").json()["id"]
        url = f"/api/billing/advances/{account_id}/refund/"
        body = {"amount": "200.00", "reason": "Discharged early", "payment_method": "Cash"}
        self.assertEqual(self.client_for(self.desk).post(url, body, format="json").status_code, 403)
        billing = self.client_for(self.billing)
        self.assertEqual(billing.post(url, {**body, "reason": ""}, format="json").status_code, 400)
        self.assertEqual(billing.post(url, {**body, "amount": "600.00"}, format="json").status_code, 400)
        resp = billing.post(url, body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Decimal(resp.json()["balance"]), Decimal("300.00"))
        self.assertTrue(AuditLog.objects.filter(action="billing.advance.refund", user=self.billing).exists())

    def test_refund_to_patient_retried_with_one_key_pays_once(self):
        """RL-05: a double click on 'Refund advance' must not pay the money back twice."""
        account_id = self.deposit("500.00").json()["id"]
        url = f"/api/billing/advances/{account_id}/refund/"
        body = {"amount": "200.00", "reason": "Discharged early", "payment_method": "Cash",
                "idempotency_key": "adv-refund-1"}
        billing = self.client_for(self.billing)

        first = billing.post(url, body, format="json")
        retry = billing.post(url, body, format="json")

        self.assertEqual((first.status_code, retry.status_code), (201, 200), first.content)
        self.assertEqual(Decimal(retry.json()["balance"]), Decimal("300.00"))
        self.assertEqual(AdvanceTransaction.objects.filter(kind=AdvanceTransaction.Kind.REFUND).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="billing.advance.refund").count(), 1)

    def test_another_hospital_sees_and_spends_nothing(self):
        account_id = self.deposit().json()["id"]
        outsider = self.client_for(self.outsider, self.other)
        self.assertEqual(outsider.get(f"/api/billing/advances/{account_id}/").status_code, 404)
        self.assertEqual(outsider.get("/api/billing/advances/").json().get("results", []), [])
        resp = outsider.post("/api/billing/advances/deposit/",
                             {"patient": self.patient.id, "amount": "10.00"}, format="json")
        self.assertIn(resp.status_code, (400, 403))
        self.assertEqual(AdvanceTransaction.objects.count(), 1)
