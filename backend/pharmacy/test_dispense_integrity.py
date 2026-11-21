"""
Prompt 4/5 pharmacy checks (synthetic data only). The Android E2E run of
2026-11-19 saw: Aspirin "Not in stock" refused; Pantoprazole x5 dispensed
from DEMO-PAN-01, stock 80 -> 75, sale ₹30, billed ₹33.60 with 12% GST.
These tests keep that behaviour and add the stock and billing invariants:
stock never goes negative and is never taken twice for one dispensing.
"""

import unittest
from decimal import Decimal

from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from billing.models import Invoice, InvoiceItem
from clinical.models import Prescription, PrescriptionItem
from hospital.models import Hospital
from patients.models import Patient
from procurement.models import StockTransaction
from security_tests.test_concurrency import run_together
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

from .models import Medicine, Sale

DISPENSE = "/api/pharmacy-sales/dispense-prescription/"
# A refused dispensing: invalid (400) or already done / in progress (409).
REFUSED = (400, 409)


class DispenseFixture:
    def build(self, prefix, stock=80):
        self.hospital = Hospital.objects.create(name=f"Synthetic {prefix} Pharmacy", is_active=True)
        self.pharmacist, _ = make_staff(f"{prefix}_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.second, _ = make_staff(f"{prefix}_pharmacist2", self.hospital, role=StaffRole.PHARMACIST)
        self.patient = Patient.objects.create(name=f"Synthetic {prefix} Patient", age=58, gender="Male",
                                              phone="9000004001", hospital=self.hospital)
        self.pan = Medicine.objects.create(name="Pantoprazole", hospital=self.hospital, batch="DEMO-PAN-01",
                                           quantity=stock, price=Decimal("6.00"), tax_rate=Decimal("12.00"))
        self.aspirin = Medicine.objects.create(name="Aspirin", hospital=self.hospital, batch="DEMO-ASP-01",
                                               quantity=0, price=Decimal("1.50"))

    def prescription(self, quantity=5, name="Pantoprazole"):
        rx = Prescription.objects.create(hospital=self.hospital, patient=self.patient)
        item = PrescriptionItem.objects.create(prescription=rx, name=name, quantity=quantity)
        return rx, item

    def dispense(self, rx, item, medicine, user=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user or self.pharmacist)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))
        return client.post(DISPENSE, {"prescription": rx.pk, "lines": [{"item": item.pk, "medicine": medicine.pk}]},
                           format="json")


class DispenseIntegrityTests(DispenseFixture, TestCase):
    def setUp(self):
        self.build("e2e")

    def test_the_e2e_figures_hold(self):
        rx, item = self.prescription()

        response = self.dispense(rx, item, self.pan)

        self.assertEqual(response.status_code, 201, response.content)
        self.pan.refresh_from_db()
        self.assertEqual(self.pan.quantity, 75)
        sale = Sale.objects.get(prescription=rx)
        self.assertEqual((sale.quantity, sale.unit_price, sale.total), (5, Decimal("6.00"), Decimal("30.00")))
        line = InvoiceItem.objects.get(pharmacy_sale=sale)
        # 5 x 6.00 = 30.00; GST 12% = 3.60; bill 33.60.
        self.assertEqual((line.invoice.tax, line.invoice.total, line.invoice.status, line.category),
                         (Decimal("3.60"), Decimal("33.60"), Invoice.Status.UNPAID, "pharmacy"))
        self.assertEqual(line.invoice.prescription, rx)
        ledger = StockTransaction.objects.filter(medicine=self.pan, reason="Pharmacy sale")
        self.assertEqual(list(ledger.values_list("quantity", flat=True)), [5])

    def test_out_of_stock_is_refused_and_changes_nothing(self):
        rx, item = self.prescription(quantity=10, name="Aspirin")

        response = self.dispense(rx, item, self.aspirin)

        self.assertEqual(response.status_code, 400)
        self.aspirin.refresh_from_db()
        self.assertEqual(self.aspirin.quantity, 0)
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(Invoice.objects.exists())

    def test_more_than_the_stock_is_refused_and_never_goes_negative(self):
        rx, item = self.prescription(quantity=81)

        self.assertEqual(self.dispense(rx, item, self.pan).status_code, 400)
        self.pan.refresh_from_db()
        self.assertEqual(self.pan.quantity, 80)
        self.assertFalse(StockTransaction.objects.filter(reason="Pharmacy sale").exists())

    def test_a_repeated_request_takes_stock_and_bills_only_once(self):
        rx, item = self.prescription()

        first = self.dispense(rx, item, self.pan)
        again = self.dispense(rx, item, self.pan, user=self.second)

        self.assertEqual(first.status_code, 201)
        self.assertIn(again.status_code, REFUSED)
        self.pan.refresh_from_db()
        self.assertEqual(self.pan.quantity, 75)
        self.assertEqual(Sale.objects.filter(prescription=rx).count(), 1)
        self.assertEqual(InvoiceItem.objects.filter(pharmacy_sale__prescription=rx).count(), 1)

    def test_a_return_restocks_with_a_ledger_entry_and_lowers_the_bill(self):
        rx, item = self.prescription()
        self.dispense(rx, item, self.pan)
        sale = Sale.objects.get(prescription=rx)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.pharmacist)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.pk))

        response = client.post(f"/api/pharmacy-sales/{sale.pk}/return/",
                               {"quantity": 2, "reason": "Synthetic return", "restock": True}, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.pan.refresh_from_db()
        self.assertEqual(self.pan.quantity, 77)
        self.assertTrue(StockTransaction.objects.filter(medicine=self.pan, reason="Patient return", quantity=2).exists())
        line = InvoiceItem.objects.get(pharmacy_sale=sale)
        # 3 x 6.00 = 18.00; GST 12% = 2.16; bill 20.16.
        self.assertEqual((line.quantity, line.invoice.total), (3, Decimal("20.16")))


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ParallelDispenseTests(DispenseFixture, TransactionTestCase):
    def setUp(self):
        self.build("par", stock=5)

    def test_two_counters_on_one_prescription_dispense_it_once(self):
        rx, item = self.prescription()
        users = [self.pharmacist, self.second]

        codes = run_together(lambda i: self.dispense(rx, item, self.pan, user=users[i % 2]).status_code, count=2)

        self.assertEqual(sorted(codes)[0], 201, codes)
        self.assertIn(sorted(codes)[1], REFUSED, codes)
        self.pan.refresh_from_db()
        self.assertEqual(self.pan.quantity, 0)
        self.assertEqual(InvoiceItem.objects.filter(pharmacy_sale__prescription=rx).count(), 1)

    def test_two_prescriptions_cannot_drain_the_same_last_stock(self):
        first, second = self.prescription(), self.prescription()
        jobs = [first, second]
        users = [self.pharmacist, self.second]

        codes = run_together(lambda i: self.dispense(*jobs[i], self.pan, user=users[i]).status_code, count=2)

        self.assertEqual(sorted(codes)[0], 201, codes)
        self.assertIn(sorted(codes)[1], REFUSED, codes)
        self.pan.refresh_from_db()
        self.assertEqual(self.pan.quantity, 0)
        self.assertEqual(Sale.objects.count(), 1)
