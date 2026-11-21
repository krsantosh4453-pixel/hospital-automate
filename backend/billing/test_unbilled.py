"""
B-1: a hand-added price-list line for a service that is charged
automatically (consultation, laboratory test, bed day) would bill it twice,
so it is refused. B-2 / B-3: work done before its price existed, or left on a
cancelled bill, is listed and charged once by the unbilled-work sweep.
Synthetic data only.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from audit.models import AuditLog
from billing.charges import release_charges
from billing.models import Invoice, InvoiceItem
from billing.test_charge_capture import add_price
from config.hospital_time import hospital_today
from encounters.models import QueueToken, Visit
from encounters.test_visit_lifecycle import LifecycleFixture, client_for
from hospital.models import Hospital
from laboratory.models import LabTest
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

Token = QueueToken.Status
PRICES = "/api/billing/price-list/"


class HandAddedLineTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("hand")
        self.patient = Patient.objects.create(name="Synthetic Hand", age=40, gender="Male", phone="9000002001",
                                              hospital=self.hospital)
        self.invoice = Invoice.objects.create(patient=self.patient, hospital=self.hospital, invoice_number="T-HAND-1")

    def add_line(self, price):
        return client_for(self.admin_user, self.hospital).post(
            "/api/billing/invoice-items/", {"invoice": self.invoice.pk, "service_price": price.pk, "quantity": 1},
            format="json")

    def test_automatic_services_cannot_be_added_by_hand(self):
        for category in ("consultation", "laboratory", "bed"):
            with self.subTest(category=category):
                price = add_price(self.hospital, category, f"P-{category}", "500.00")
                response = self.add_line(price)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn("bill it twice", str(response.json()))
        self.assertFalse(InvoiceItem.objects.filter(invoice=self.invoice).exists())

    def test_a_new_bill_cannot_type_the_old_consultation_or_lab_lines(self):
        client = client_for(self.admin_user, self.hospital)
        for description in ("Doctor Consultation", " laboratory services "):
            with self.subTest(description=description):
                response = client.post("/api/billing/invoices/", {
                    "hospital": self.hospital.pk, "patient": self.patient.pk,
                    "items_data": [{"description": description, "quantity": 1, "unit_price": "300.00"}],
                }, format="json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn("bill them twice", str(response.json()))
        ok = client.post("/api/billing/invoices/", {
            "hospital": self.hospital.pk, "patient": self.patient.pk,
            "items_data": [{"description": "Other Services", "quantity": 1, "unit_price": "300.00"}],
        }, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)

    def test_an_older_bill_with_such_a_line_can_still_be_edited(self):
        InvoiceItem.objects.create(invoice=self.invoice, description="Doctor Consultation", quantity=1,
                                   unit_price=Decimal("300.00"), subtotal=Decimal("300.00"))
        response = client_for(self.admin_user, self.hospital).patch(f"/api/billing/invoices/{self.invoice.pk}/", {
            "discount": "0",
            "items_data": [{"description": "Doctor Consultation", "quantity": 1, "unit_price": "300.00"},
                           {"description": "Other Services", "quantity": 1, "unit_price": "50.00"}],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.invoice.items.count(), 2)

    def test_other_services_are_still_added_from_the_price_list(self):
        price = add_price(self.hospital, "procedure", "P-DRESSING", "150.00")
        response = self.add_line(price)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(InvoiceItem.objects.get(invoice=self.invoice).unit_price, Decimal("150.00"))


class UnbilledSweepTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("sweep")

    def get(self, user, **params):
        return client_for(user, self.hospital).get(f"{PRICES}unbilled/", params)

    def sweep(self, user, **body):
        return client_for(user, self.hospital).post(f"{PRICES}charge-unbilled/", body, format="json")

    def completed_without_price(self, name):
        token = self.booked(name, state=Token.IN_CONSULTATION)
        self.assertEqual(self.patch(self.doctor_user, token, "Completed").status_code, 200)
        self.assertFalse(InvoiceItem.objects.filter(charge_key=f"visit:{token.visit_id}:consultation").exists())
        return token

    def test_work_done_before_its_price_is_listed_then_charged_once(self):
        token = self.completed_without_price("Early")
        listed = self.get(self.desk_user).json()
        self.assertEqual([(r["kind"], r["id"], r["priced"]) for r in listed["results"]],
                         [("consultation", token.visit_id, False)])

        add_price(self.hospital, "consultation", "CON-OPD", "500.00")
        self.assertTrue(self.get(self.desk_user).json()["results"][0]["priced"])

        swept = self.sweep(self.admin_user)
        self.assertEqual(swept.status_code, 200, swept.content)
        self.assertEqual(len(swept.json()["charged"]), 1)
        line = InvoiceItem.objects.get(charge_key=f"visit:{token.visit_id}:consultation")
        self.assertEqual(line.unit_price, Decimal("500.00"))
        self.assertTrue(AuditLog.objects.filter(action="billing.charge.unbilled_swept").exists())

        again = self.sweep(self.admin_user)
        self.assertEqual(again.json()["charged"], [])
        self.assertEqual(InvoiceItem.objects.filter(charge_key__startswith=f"visit:{token.visit_id}:").count(), 1)
        self.assertEqual(self.get(self.desk_user).json()["count"], 0)

    def test_unpriced_work_is_reported_not_charged(self):
        self.completed_without_price("NoPrice")
        swept = self.sweep(self.admin_user).json()
        self.assertEqual((swept["charged"], len(swept["unpriced"])), ([], 1))
        self.assertFalse(InvoiceItem.objects.exists())

    def test_a_verified_lab_test_without_a_charge_is_swept(self):
        patient = Patient.objects.create(name="Synthetic Lab Sweep", age=33, gender="Female", phone="9000002002",
                                         hospital=self.hospital)
        test = LabTest.objects.create(hospital=self.hospital, name="Lipid Profile", patient=patient,
                                      status="Verified", verified_at=timezone.now())
        add_price(self.hospital, "laboratory", "LAB-LIPID", "650.00", applies_to="Lipid Profile")
        swept = self.sweep(self.admin_user).json()
        self.assertEqual([r["id"] for r in swept["charged"]], [test.pk])
        self.assertEqual(InvoiceItem.objects.get(charge_key=f"labtest:{test.pk}").unit_price, Decimal("650.00"))

    def test_a_charge_on_a_cancelled_bill_is_billed_again(self):
        add_price(self.hospital, "consultation", "CON-OPD", "500.00")
        token = self.booked("Cancelled", state=Token.IN_CONSULTATION)
        self.patch(self.doctor_user, token, "Completed")
        invoice = InvoiceItem.objects.get(charge_key=f"visit:{token.visit_id}:consultation").invoice
        Invoice.objects.filter(pk=invoice.pk).update(status=Invoice.Status.CANCELLED)
        invoice.refresh_from_db()
        release_charges(invoice)

        self.assertEqual(self.get(self.desk_user).json()["count"], 1)
        self.sweep(self.admin_user)
        live = InvoiceItem.objects.get(charge_key=f"visit:{token.visit_id}:consultation")
        self.assertNotEqual(live.invoice_id, invoice.pk)

    def test_only_an_admin_or_manager_charges(self):
        self.completed_without_price("Roles")
        add_price(self.hospital, "consultation", "CON-OPD", "500.00")
        self.assertEqual(self.sweep(self.desk_user).status_code, 403)
        self.assertEqual(self.get(self.doctor_user).status_code, 403)
        self.assertFalse(InvoiceItem.objects.exists())

    def test_the_look_back_is_limited(self):
        today = hospital_today()
        for since in (today - timedelta(days=91), today + timedelta(days=1)):
            with self.subTest(since=since):
                self.assertEqual(self.get(self.desk_user, since=str(since)).status_code, 400)
        self.assertEqual(self.get(self.desk_user, since="yesterday").status_code, 400)
        old = self.completed_without_price("Old")
        Visit.objects.filter(pk=old.visit_id).update(visit_date=timezone.now() - timedelta(days=40))
        self.assertEqual(self.get(self.desk_user).json()["count"], 0)
        since = str(today - timedelta(days=60))
        self.assertEqual(self.get(self.desk_user, since=since).json()["count"], 1)

    def test_another_hospitals_work_is_never_listed(self):
        self.completed_without_price("Ours")
        other = Hospital.objects.create(name="Synthetic Other Sweep", is_active=True)
        other_admin, _ = make_staff("sweep_other_admin", other, role=StaffRole.ADMIN)
        self.assertEqual(client_for(other_admin, other).get(f"{PRICES}unbilled/").json()["count"], 0)
        foreign = client_for(other_admin, self.hospital).get(f"{PRICES}unbilled/")
        self.assertIn(foreign.status_code, (400, 403))
