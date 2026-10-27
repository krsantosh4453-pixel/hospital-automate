"""Tests for billing module."""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from hospital.models import Hospital, Department
from users.models import StaffProfile, StaffHospitalMembership, StaffRole
from patients.models import Patient, PatientHospital
from billing.models import Invoice, InvoiceItem, Payment, InsuranceClaim

User = get_user_model()


class BillingAPITests(TestCase):
    """Tests for billing API endpoints."""

    def setUp(self):
        self.client = APIClient()

        self.hospital_a = Hospital.objects.create(name="Hospital A", is_active=True)
        self.hospital_b = Hospital.objects.create(name="Hospital B", is_active=True)

        self.dept = Department.objects.create(hospital=self.hospital_a, name="General")

        # Create billing staff user for Hospital A
        self.user = User.objects.create_user(
            username="billing_a",
            email="billing_a@hospital.com",
            password="testpass123",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.BILLING_STAFF,
            employee_id="EMP001",
            is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.BILLING_STAFF,
            is_active=True,
        )

        # Create patient
        self.patient = Patient.objects.create(
            name="Test Patient",
            age=30,
            gender="Male",
            phone="9876543210",
            hospital=self.hospital_a,
        )
        PatientHospital.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            is_active=True,
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _get_invoices_url(self):
        return f"/api/billing/invoices/?hospital={self.hospital_a.id}"

    def _get_payments_url(self):
        return f"/api/billing/payments/?hospital={self.hospital_a.id}"

    def test_create_invoice(self):
        """Test creating an invoice."""
        response = self.client.post(
            self._get_invoices_url(),
            {
                "patient": self.patient.id,
                "invoice_type": "Outpatient",
                "status": "Pending",
                "items_data": [
                    {
                        "description": "Consultation",
                        "quantity": 1,
                        "unit_price": "500.00",
                        "tax_rate": "18.00",
                    },
                    {
                        "description": "Medication",
                        "quantity": 2,
                        "unit_price": "250.00",
                        "tax_rate": "12.00",
                    },
                ],
            },
            format="json",
        )
        print("Response status:", response.status_code)
        print("Response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertEqual(len(response.data["items"]), 2)

    def test_invoice_total_calculation(self):
        """Test invoice total is calculated correctly."""
        response = self.client.post(
            self._get_invoices_url(),
            {
                "patient": self.patient.id,
                "invoice_type": "Outpatient",
                "status": "Pending",
                "items_data": [
                    {
                        "description": "Test Service",
                        "quantity": 2,
                        "unit_price": "100.00",
                        "tax_rate": "10.00",
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # 2 * 100 = 200, tax = 20, total = 220
        self.assertEqual(Decimal(response.data["subtotal"]), Decimal("200.00"))
        self.assertEqual(Decimal(response.data["tax_amount"]), Decimal("20.00"))
        self.assertEqual(Decimal(response.data["total_amount"]), Decimal("220.00"))

    def test_create_payment(self):
        """Test creating a payment."""
        invoice = Invoice.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            status="Pending",
            total=Decimal("1180.00"),
        )
        response = self.client.post(
            self._get_payments_url(),
            {
                "invoice": invoice.id,
                "amount": "500.00",
                "payment_method": "Cash",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("500.00"))
        invoice.refresh_from_db()

    def test_insurance_claim(self):
        """Test insurance claim model."""
        invoice = Invoice.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            status="Pending",
            total=Decimal("5900.00"),
        )
        claim = InsuranceClaim.objects.create(
            patient=self.patient,
            invoice=invoice,
            insurance_company="Test Insurance",
            claim_number="POL123456",
            amount=Decimal("5000.00"),
            status="Submitted",
        )
        self.assertEqual(claim.invoice, invoice)
        self.assertEqual(claim.status, "Submitted")

    def test_list_invoices(self):
        """Test listing invoices."""
        Invoice.objects.create(
            patient=self.patient,
            hospital=self.hospital_a,
            status="Pending",
            total=Decimal("118.00"),
        )
        response = self.client.get(self._get_invoices_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data)
        self.assertEqual(len(data), 1)
