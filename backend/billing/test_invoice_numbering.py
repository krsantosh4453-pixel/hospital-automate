"""P1-05: GST invoice numbers run consecutively per hospital per financial year (April to March)."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import Invoice
from billing.numbering import financial_year, format_invoice_number, next_invoice_number
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class InvoiceNumberFormatTests(TestCase):
    def test_format_fits_the_sixteen_character_gst_limit(self):
        number = format_invoice_number(2026, 1)

        self.assertEqual(number, "INV/26-27/000001")
        self.assertEqual(len(number), 16)

    def test_financial_year_starts_in_april(self):
        self.assertEqual(financial_year(date(2027, 3, 31)), 2026)
        self.assertEqual(financial_year(date(2027, 4, 1)), 2027)

    def test_year_rollover_restarts_the_series(self):
        hospital = Hospital.objects.create(name="Synthetic FY Hospital", is_active=True)
        with mock.patch("billing.numbering.hospital_today", return_value=date(2027, 3, 31)):
            last_of_year = next_invoice_number(hospital)
        with mock.patch("billing.numbering.hospital_today", return_value=date(2027, 4, 1)):
            first_of_next = next_invoice_number(hospital)

        self.assertEqual((last_of_year, first_of_next), ("INV/26-27/000001", "INV/27-28/000001"))


class InvoiceSeriesTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Series A", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Series B", is_active=True)

    def bill(self, hospital, username):
        biller, _ = make_staff(username, hospital, role=StaffRole.BILLING_STAFF)
        patient = Patient.objects.create(name="Synthetic Billed", age=40, gender="Male",
                                         phone=f"90000{hospital.pk:05d}", hospital=hospital)
        PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=f"S-{hospital.pk}")
        client = APIClient()
        client.force_authenticate(biller)
        client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        numbers = []
        for _ in range(2):
            resp = client.post("/api/billing/invoices/", {
                "patient": patient.id,
                "items_data": [{"description": "Consultation", "quantity": 1, "unit_price": "300.00"}],
            }, format="json")
            self.assertEqual(resp.status_code, 201, resp.content)
            numbers.append(resp.json()["invoice_number"])
        return numbers

    def test_each_hospital_numbers_its_own_bills_consecutively(self):
        fy = financial_year(date.today())
        prefix = format_invoice_number(fy, 0)[:-6]

        self.assertEqual(self.bill(self.hospital, "biller_a"), [f"{prefix}000001", f"{prefix}000002"])
        self.assertEqual(self.bill(self.other, "biller_b"), [f"{prefix}000001", f"{prefix}000002"])
        self.assertEqual(Invoice.objects.filter(invoice_number=f"{prefix}000001").count(), 2)

    def test_a_number_repeats_only_across_hospitals(self):
        from django.db import IntegrityError, transaction

        patient = Patient.objects.create(name="Synthetic Dup", age=30, gender="Female", phone="9000077777",
                                         hospital=self.hospital)
        Invoice.objects.create(patient=patient, hospital=self.hospital, invoice_number="INV/26-27/000099",
                               total=Decimal("1.00"))

        with self.assertRaises(IntegrityError), transaction.atomic():
            Invoice.objects.create(patient=patient, hospital=self.hospital, invoice_number="INV/26-27/000099",
                                   total=Decimal("1.00"))
