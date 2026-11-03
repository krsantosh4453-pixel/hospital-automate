"""Financial report totals: billing payments plus pharmacy sales, no invented lab figure."""

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import Invoice, Payment
from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class FinancialReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Finance Hospital", is_active=True)
        cls.admin, _ = make_staff("fin_admin", cls.hospital, role=StaffRole.ADMIN)
        patient = Patient.objects.create(
            name="Synthetic Finance Patient", age=50, gender="Female", phone="9000000041", hospital=cls.hospital
        )
        invoice = Invoice.objects.create(
            patient=patient, hospital=cls.hospital, invoice_number="FIN-TEST-1", total=Decimal("500.00")
        )
        Payment.objects.create(invoice=invoice, amount=Decimal("500.00"))

    def test_total_is_billing_plus_pharmacy_and_lab_is_not_a_fake_zero(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.admin)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

        response = client.get(f"/api/reports/analytics/financial/?hospital={self.hospital.id}&period=today")

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["billing"]["period_revenue"], 500.0)
        self.assertEqual(body["total_revenue"], 500.0 + body["pharmacy_revenue"])
        # Lab tests carry no price; lab charges are billed on invoices and already in billing revenue.
        self.assertIsNone(body["laboratory_revenue"])
