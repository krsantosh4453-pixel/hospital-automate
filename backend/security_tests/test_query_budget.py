"""Guard against N+1 queries on the busiest list endpoints (30 synthetic rows each)."""

from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from billing.models import Invoice, InvoiceItem, Payment
from hospital.models import Hospital
from laboratory.models import LabTest
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

ROWS = 30
BUDGET = 15  # queries per list request, independent of row count


class QueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Perf", is_active=True)
        cls.user, _ = make_staff("perf_admin", cls.hospital, role=StaffRole.ADMIN)
        for i in range(ROWS):
            patient = Patient.objects.create(name=f"Synthetic {i}", age=30, gender="Male",
                                             phone=f"90001{i:05d}", hospital=cls.hospital)
            PatientHospital.objects.create(patient=patient, hospital=cls.hospital, uhid=f"PERF-{i}")
            invoice = Invoice.objects.create(patient=patient, hospital=cls.hospital, invoice_number=f"INV-PERF-{i}",
                                             total=Decimal("10.00"))
            InvoiceItem.objects.create(invoice=invoice, description="Consult", quantity=1,
                                       unit_price=Decimal("10.00"), subtotal=Decimal("10.00"))
            Payment.objects.create(invoice=invoice, amount=Decimal("5.00"))
            LabTest.objects.create(name="CBC", patient=patient, hospital=cls.hospital)

    def test_list_endpoints_stay_within_query_budget(self):
        client = APIClient()
        client.force_authenticate(self.user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        for url in ("/api/patients/", "/api/billing/invoices/", "/api/laboratory/"):
            with CaptureQueriesContext(connection) as ctx:
                resp = client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertLessEqual(len(ctx.captured_queries), BUDGET, f"{url}: {len(ctx.captured_queries)} queries")
        rows = client.get("/api/billing/invoices/").json()
        rows = rows.get("results", rows)
        self.assertEqual({str(r["balance_due"]) for r in rows}, {"5.00"})
