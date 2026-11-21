"""
BUG-07 (Android E2E 2026-11-19, synthetic data only): the hospital price list,
invoice lines priced from it, and the rule that a bill with charges reaches
₹0 only through an authorised waiver.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from billing.models import Invoice, InvoiceItem, InvoiceWaiver, ServicePrice
from config.hospital_time import hospital_today
from doctors.models import Doctor
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from pharmacy.models import Medicine
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

PRICES = "/api/billing/price-list/"
INVOICES = "/api/billing/invoices/"


def client_for(user, hospital):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.pk))
    return client


class PriceListFixture:
    def build(self):
        self.hospital = Hospital.objects.create(name="Synthetic Tariff A", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Tariff B", is_active=True)
        self.admin, _ = make_staff("tariff_admin", self.hospital, role=StaffRole.ADMIN)
        self.manager, _ = make_staff("tariff_manager", self.hospital, role=StaffRole.HOSPITAL_MANAGER)
        self.clerk, _ = make_staff("tariff_clerk", self.hospital, role=StaffRole.BILLING_STAFF)
        self.nurse, _ = make_staff("tariff_nurse", self.hospital, role=StaffRole.NURSE)
        self.other_admin, _ = make_staff("tariff_admin_b", self.other, role=StaffRole.ADMIN)
        self.patient = Patient.objects.create(name="Synthetic Tariff Patient", age=40, gender="Female",
                                              phone="9000007001", hospital=self.hospital)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="SYN-T-1", is_active=True)

    def add(self, user=None, **body):
        payload = {"category": "laboratory", "code": "LAB-LIPID", "name": "Lipid profile",
                   "applies_to": "Lipid Profile", "unit_price": "650.00", "tax_rate": "0"}
        payload.update(body)
        return client_for(user or self.admin, self.hospital).post(PRICES, payload, format="json")


class PriceListApiTests(PriceListFixture, TestCase):
    def setUp(self):
        self.build()

    def test_admin_adds_a_price_in_inr_from_today(self):
        response = self.add()

        self.assertEqual(response.status_code, 201, response.content)
        price = ServicePrice.objects.get(pk=response.data["id"])
        self.assertEqual((price.hospital, price.unit_price, price.currency, price.effective_from),
                         (self.hospital, Decimal("650.00"), "INR", hospital_today()))
        self.assertTrue(response.data["is_current"])
        self.assertTrue(AuditLog.objects.filter(action="billing.price.create", object_id=str(price.pk)).exists())

    def test_hospital_manager_may_add_but_billing_clerk_and_nurse_may_not(self):
        self.assertEqual(self.add(self.manager).status_code, 201)
        self.assertEqual(self.add(self.clerk, code="LAB-X", applies_to="X").status_code, 403)
        self.assertEqual(self.add(self.nurse, code="LAB-Y", applies_to="Y").status_code, 403)

    def test_billing_clerk_reads_the_list_and_nurse_cannot(self):
        self.add()
        listed = client_for(self.clerk, self.hospital).get(PRICES)
        refused = client_for(self.nurse, self.hospital).get(PRICES)

        self.assertEqual(listed.status_code, 200)
        self.assertEqual([row["code"] for row in listed.json()["results"]], ["LAB-LIPID"])
        self.assertEqual(refused.status_code, 403)

    def test_another_hospital_never_sees_or_uses_these_prices(self):
        self.add()
        rows = client_for(self.other_admin, self.other).get(PRICES).json()["results"]
        self.assertEqual(rows, [])

    def test_bad_prices_are_refused(self):
        cases = [
            {"unit_price": "0"}, {"unit_price": "-10"}, {"unit_price": "12.345"}, {"tax_rate": "101"},
            {"currency": "USD"}, {"applies_to": ""}, {"code": "  "},
            {"effective_from": str(hospital_today() - timedelta(days=1))},
        ]
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(self.add(**body).status_code, 400, body)
        self.assertEqual(ServicePrice.objects.count(), 0)

    def test_doctor_fee_only_for_consultation_and_own_hospital(self):
        doctor_b = Doctor.objects.create(hospital=self.other, name="Dr Synthetic B", specialization="General",
                                         phone="9000007002")
        doctor_a = Doctor.objects.create(hospital=self.hospital, name="Dr Synthetic A", specialization="General",
                                         phone="9000007003")
        self.assertEqual(self.add(doctor=doctor_a.pk).status_code, 400)  # a lab price cannot belong to a doctor
        foreign = self.add(category="consultation", code="CON-B", name="Fee", applies_to="", doctor=doctor_b.pk)
        own = self.add(category="consultation", code="CON-A", name="Fee", applies_to="", doctor=doctor_a.pk)
        self.assertEqual(foreign.status_code, 400)
        self.assertEqual(own.status_code, 201, own.content)

    def test_a_new_price_closes_the_old_one_and_old_bills_keep_their_price(self):
        first = self.add().data
        line = InvoiceItem.objects.create(
            invoice=Invoice.objects.create(patient=self.patient, hospital=self.hospital, invoice_number="SYN-OLD"),
            description="Lipid profile", unit_price=Decimal("650.00"), subtotal=Decimal("650.00"),
            service_price_id=first["id"],
        )
        tomorrow = hospital_today() + timedelta(days=1)
        second = self.add(unit_price="700.00", effective_from=str(tomorrow))
        same_day = self.add(unit_price="720.00", effective_from=str(tomorrow))

        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(same_day.status_code, 400)
        old = ServicePrice.objects.get(pk=first["id"])
        self.assertEqual((old.unit_price, old.effective_to), (Decimal("650.00"), hospital_today()))
        line.refresh_from_db()
        self.assertEqual(line.unit_price, Decimal("650.00"))

    def test_prices_are_never_edited_or_deleted_only_retired(self):
        price = self.add().data
        client = client_for(self.admin, self.hospital)

        self.assertEqual(client.patch(f"{PRICES}{price['id']}/", {"unit_price": "1"}, format="json").status_code, 405)
        self.assertEqual(client.delete(f"{PRICES}{price['id']}/").status_code, 405)
        self.assertEqual(client_for(self.clerk, self.hospital).post(f"{PRICES}{price['id']}/retire/").status_code, 403)
        retired = client.post(f"{PRICES}{price['id']}/retire/", {"effective_to": str(hospital_today())}, format="json")
        self.assertEqual(retired.status_code, 200, retired.content)
        self.assertEqual(retired.data["effective_to"], str(hospital_today()))

    def test_current_filter_hides_future_and_ended_prices(self):
        self.add()
        self.add(code="LAB-TSH", applies_to="TSH", effective_from=str(hospital_today() + timedelta(days=3)))
        rows = client_for(self.clerk, self.hospital).get(f"{PRICES}?current=1").json()["results"]
        self.assertEqual([row["code"] for row in rows], ["LAB-LIPID"])

    def test_medicine_prices_are_read_from_pharmacy_stock(self):
        Medicine.objects.create(name="Pantoprazole 40", hospital=self.hospital, batch="DEMO-PAN-01", quantity=80,
                                price=Decimal("6.00"), tax_rate=Decimal("12.00"), mrp=Decimal("7.50"))
        Medicine.objects.create(name="Other hospital stock", hospital=self.other, batch="B", quantity=1,
                                price=Decimal("1.00"))
        rows = client_for(self.clerk, self.hospital).get(f"{PRICES}medicines/").json()

        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["unit_price"], rows[0]["tax_rate"], rows[0]["mrp"], rows[0]["currency"]),
                         ("6.00", "12.00", "7.50", "INR"))


class PricedInvoiceLineTests(PriceListFixture, TestCase):
    def setUp(self):
        self.build()
        self.price = ServicePrice.objects.create(
            hospital=self.hospital, category="procedure", code="PROC-DRESS", name="Wound dressing",
            applies_to="Wound dressing", unit_price=Decimal("250.00"), tax_rate=Decimal("18.00"),
            effective_from=hospital_today(),
        )

    def create(self, lines, discount="0"):
        return client_for(self.clerk, self.hospital).post(INVOICES, {
            "hospital": self.hospital.pk, "patient": self.patient.pk, "discount": discount, "items_data": lines,
        }, format="json")

    def test_a_line_from_the_list_takes_its_price_and_gst(self):
        response = self.create([{"service_price": self.price.pk, "quantity": 2}])

        self.assertEqual(response.status_code, 201, response.content)
        item = InvoiceItem.objects.get(invoice_id=response.data["id"])
        self.assertEqual((item.description, item.unit_price, item.tax_rate, item.category, item.service_price_id),
                         ("Wound dressing", Decimal("250.00"), Decimal("18.00"), "procedure", self.price.pk))
        # 2 x 250 = 500.00; GST 18% = 90.00; total 590.00.
        self.assertEqual(response.data["total"], "590.00")

    def test_a_different_price_for_a_listed_service_is_refused(self):
        response = self.create([{"service_price": self.price.pk, "unit_price": "1.00"}])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_another_hospitals_price_cannot_be_used(self):
        foreign = ServicePrice.objects.create(hospital=self.other, category="other", code="X", name="X",
                                              applies_to="X", unit_price=Decimal("5.00"), effective_from=hospital_today())
        self.assertEqual(self.create([{"service_price": foreign.pk}]).status_code, 400)

    def test_free_lines_and_empty_bills_are_refused(self):
        self.assertEqual(self.create([{"description": "Free item", "unit_price": "0"}]).status_code, 400)
        self.assertEqual(self.create([]).status_code, 400)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_a_discount_cannot_take_a_bill_to_zero(self):
        refused = self.create([{"description": "Dressing", "unit_price": "250.00"}], discount="250.00")
        allowed = self.create([{"description": "Dressing", "unit_price": "250.00"}], discount="50.00")

        self.assertEqual(refused.status_code, 400)
        self.assertEqual(allowed.status_code, 201)
        invoice_id = allowed.data["id"]
        later = client_for(self.clerk, self.hospital).patch(f"{INVOICES}{invoice_id}/", {"discount": "250.00"},
                                                             format="json")
        self.assertEqual(later.status_code, 400)
        self.assertEqual(Invoice.objects.get(pk=invoice_id).total, Decimal("200.00"))


class WaiverTests(PriceListFixture, TestCase):
    def setUp(self):
        self.build()
        self.invoice = Invoice.objects.create(patient=self.patient, hospital=self.hospital, invoice_number="SYN-W1")
        InvoiceItem.objects.create(invoice=self.invoice, description="Bed day", unit_price=Decimal("1000.00"),
                                   subtotal=Decimal("1000.00"), tax_rate=Decimal("5.00"))
        from billing.services import recalculate
        recalculate(self.invoice)

    def waive(self, user, reason="Charity case approved by the board"):
        return client_for(user, self.hospital).post(f"{INVOICES}{self.invoice.pk}/waive/", {"reason": reason},
                                                    format="json")

    def test_only_admin_or_manager_waive_and_a_reason_is_required(self):
        self.assertEqual(self.waive(self.clerk).status_code, 403)
        self.assertEqual(self.waive(self.manager, reason="free").status_code, 400)
        self.assertFalse(InvoiceWaiver.objects.exists())

    def test_a_waiver_makes_the_bill_zero_with_an_audit_trail(self):
        response = self.waive(self.manager)

        self.assertEqual(response.status_code, 201, response.content)
        self.invoice.refresh_from_db()
        # 1000.00 + 5% GST = 1050.00 waived; discount 1000.00 before tax leaves 0.00.
        self.assertEqual((self.invoice.discount, self.invoice.tax, self.invoice.total, self.invoice.status),
                         (Decimal("1000.00"), Decimal("0.00"), Decimal("0.00"), Invoice.Status.PAID))
        waiver = InvoiceWaiver.objects.get(invoice=self.invoice)
        self.assertEqual((waiver.amount, waiver.approved_by), (Decimal("1050.00"), self.manager))
        self.assertTrue(AuditLog.objects.filter(action="billing.invoice.waived", object_id=str(self.invoice.pk)).exists())
        self.assertEqual(self.waive(self.manager).status_code, 400)  # never twice

    def test_a_bill_with_money_taken_is_not_waived(self):
        from billing.services import record_payment
        record_payment(self.invoice, Decimal("100.00"))
        self.assertEqual(self.waive(self.admin).status_code, 400)

    def test_a_waived_bill_keeps_its_discount_and_cannot_be_deleted(self):
        self.waive(self.manager)
        client = client_for(self.admin, self.hospital)

        self.assertEqual(client.patch(f"{INVOICES}{self.invoice.pk}/", {"discount": "0"}, format="json").status_code, 400)
        self.assertEqual(client.delete(f"{INVOICES}{self.invoice.pk}/").status_code, 400)
        self.assertTrue(Invoice.objects.filter(pk=self.invoice.pk).exists())


class BillLineEditTests(PriceListFixture, TestCase):
    """Review fixes: editing single lines never makes a bill an unexplained ₹0."""

    def setUp(self):
        self.build()
        self.price = ServicePrice.objects.create(
            hospital=self.hospital, category="procedure", code="PROC-DRESS", name="Wound dressing",
            applies_to="Wound dressing", unit_price=Decimal("250.00"), effective_from=hospital_today())
        client = client_for(self.clerk, self.hospital)
        created = client.post(INVOICES, {"hospital": self.hospital.pk, "patient": self.patient.pk, "discount": "250",
                                         "items_data": [{"service_price": self.price.pk},
                                                        {"description": "Sutures", "unit_price": "50.00"}]},
                              format="json")
        self.invoice = Invoice.objects.get(pk=created.data["id"])
        self.priced, self.manual = self.invoice.items.order_by("id")
        self.client = client

    def test_removing_a_line_cannot_leave_the_discount_covering_everything(self):
        response = self.client.delete(f"/api/billing/invoice-items/{self.manual.pk}/")
        self.invoice.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.invoice.total, Decimal("50.00"))  # 300 - 250

    def test_the_last_line_cannot_be_deleted(self):
        Invoice.objects.filter(pk=self.invoice.pk).update(discount=0)
        self.client.delete(f"/api/billing/invoice-items/{self.manual.pk}/")
        response = self.client.delete(f"/api/billing/invoice-items/{self.priced.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(InvoiceItem.objects.filter(pk=self.priced.pk).exists())

    def test_a_price_list_line_keeps_its_price_and_gst(self):
        for body in ({"unit_price": "1.00"}, {"tax_rate": "0.50"}):
            response = self.client.patch(f"/api/billing/invoice-items/{self.priced.pk}/", body, format="json")
            self.assertEqual(response.status_code, 400, body)
        self.priced.refresh_from_db()
        self.assertEqual(self.priced.unit_price, Decimal("250.00"))

    def test_a_waived_bill_takes_no_new_lines(self):
        client_for(self.manager, self.hospital).post(f"{INVOICES}{self.invoice.pk}/waive/",
                                                     {"reason": "Charity case approved by the board"}, format="json")
        response = self.client.post("/api/billing/invoice-items/", {"invoice": self.invoice.pk,
                                                                    "description": "Extra", "unit_price": "10.00"},
                                    format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.invoice.items.count(), 2)
