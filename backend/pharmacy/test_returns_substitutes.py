"""Partial dispensing, same-salt substitutes (F8) and patient returns (F5); synthetic data."""

import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from clinical.models import Prescription, PrescriptionItem
from config.hospital_time import hospital_today
from hospital.models import Hospital
from patients.models import Patient
from procurement.models import StockTransaction
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

from .models import Medicine, Sale, SaleReturn

DISPENSE = "/api/pharmacy-sales/dispense-prescription/"


class PharmacyFlowCase(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Pharmacy", is_active=True)
        self.pharmacist, _ = make_staff("ph_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.compounder, _ = make_staff("ph_compounder", self.hospital, role=StaffRole.COMPOUNDER)
        patient = Patient.objects.create(name="Synthetic Buyer", age=40, gender="Female", phone="9000000901",
                                         hospital=self.hospital)
        self.rx = Prescription.objects.create(hospital=self.hospital, patient=patient)
        self.item = PrescriptionItem.objects.create(prescription=self.rx, name="Crocin 500", quantity=10)
        self.brand = Medicine.objects.create(name="Crocin 500", generic_name="Paracetamol", hospital=self.hospital,
                                             batch="C1", quantity=4, price=Decimal("2.00"))
        self.generic = Medicine.objects.create(name="Dolo 500", generic_name=" paracetamol ", hospital=self.hospital,
                                               batch="D1", quantity=50, price=Decimal("1.50"))
        self.other_salt = Medicine.objects.create(name="Brufen 400", generic_name="Ibuprofen", hospital=self.hospital,
                                                  batch="B1", quantity=50, price=Decimal("3.00"))

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def dispense(self, lines, partial=False, user=None):
        return self.client_for(user or self.pharmacist).post(
            DISPENSE, {"prescription": self.rx.pk, "lines": lines, "partial": partial}, format="json")


class PartialDispenseTests(PharmacyFlowCase):
    def test_part_now_and_the_rest_later_never_more_than_prescribed(self):
        first = self.dispense([{"item": self.item.pk, "medicine": self.brand.pk, "quantity": 4}], partial=True)
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()["status"], "Partially Dispensed")
        self.assertEqual(first.json()["remaining"], {str(self.item.pk): 6})
        self.rx.refresh_from_db()
        self.assertIsNone(self.rx.dispensed_at)

        too_many = self.dispense([{"item": self.item.pk, "medicine": self.generic.pk, "quantity": 7,
                                   "substitute_reason": "Crocin out of stock"}], partial=True)
        self.assertEqual(too_many.status_code, 400, too_many.content)

        rest = self.dispense([{"item": self.item.pk, "medicine": self.generic.pk, "quantity": 6,
                               "substitute_reason": "Crocin out of stock"}], partial=True)
        self.assertEqual(rest.status_code, 201, rest.content)
        self.assertEqual(rest.json()["status"], "Dispensed")
        self.assertEqual(self.dispense([{"item": self.item.pk, "medicine": self.generic.pk}]).status_code, 409)
        self.assertEqual(sum(Sale.objects.filter(prescription=self.rx).values_list("quantity", flat=True)), 10)

    def test_without_partial_the_whole_remaining_quantity_is_issued(self):
        self.brand.quantity = 20
        self.brand.save()
        resp = self.dispense([{"item": self.item.pk, "medicine": self.brand.pk, "quantity": 2}])
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Sale.objects.get().quantity, 10)
        self.assertEqual(Sale.objects.get().dispensed_by, self.pharmacist)


class SubstituteTests(PharmacyFlowCase):
    def line(self, medicine, reason="Prescribed brand out of stock"):
        return [{"item": self.item.pk, "medicine": medicine.pk, "substitute_reason": reason}]

    def test_pharmacist_gives_a_same_salt_brand_with_a_reason_and_it_is_audited(self):
        resp = self.dispense(self.line(self.generic))
        self.assertEqual(resp.status_code, 201, resp.content)
        sale = Sale.objects.get()
        self.assertEqual((sale.medicine, sale.substituted_for), (self.generic, "Crocin 500"))
        self.assertEqual(sale.substitution_reason, "Prescribed brand out of stock")
        entry = AuditLog.objects.get(action="pharmacy.sale.substituted")
        self.assertEqual(entry.user, self.pharmacist)
        self.assertEqual(json.loads(entry.details)["given"], "Dolo 500")

    def test_a_different_salt_is_refused(self):
        resp = self.dispense(self.line(self.other_salt))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not the same salt", str(resp.json()))
        self.assertFalse(Sale.objects.exists())
        self.other_salt.refresh_from_db()
        self.assertEqual(self.other_salt.quantity, 50)

    def test_a_substitute_needs_a_reason_and_a_pharmacist(self):
        self.assertEqual(self.dispense(self.line(self.generic, reason="")).status_code, 400)
        self.assertEqual(self.dispense(self.line(self.generic), user=self.compounder).status_code, 400)
        self.assertFalse(Sale.objects.exists())

    def test_no_substitute_when_the_prescribed_salt_is_unknown(self):
        self.brand.generic_name = ""
        self.brand.save()
        self.assertEqual(self.dispense(self.line(self.generic)).status_code, 400)


class ReturnTests(PharmacyFlowCase):
    def setUp(self):
        super().setUp()
        self.brand.quantity = 20
        self.brand.save()
        self.dispense([{"item": self.item.pk, "medicine": self.brand.pk}])
        self.sale = Sale.objects.get()

    def give_back(self, quantity, restock=True, user=None, reason="Course stopped by doctor"):
        return self.client_for(user or self.pharmacist).post(
            f"/api/pharmacy-sales/{self.sale.pk}/return/",
            {"quantity": quantity, "restock": restock, "reason": reason}, format="json")

    def test_fit_returns_go_back_to_stock_with_a_ledger_entry_and_refund_amount(self):
        resp = self.give_back(4)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Decimal(resp.json()["refund_amount"]), Decimal("8.00"))
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.quantity, 14)  # 20 - 10 + 4
        self.assertTrue(StockTransaction.objects.filter(reason="Patient return", quantity=4).exists())
        self.assertTrue(AuditLog.objects.filter(action="pharmacy.sale.returned", user=self.pharmacist).exists())

    def test_discarded_returns_do_not_touch_stock(self):
        self.assertEqual(self.give_back(3, restock=False).status_code, 201)
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.quantity, 10)

    def test_never_more_than_was_sold_in_total(self):
        self.assertEqual(self.give_back(6).status_code, 201)
        self.assertEqual(self.give_back(5).status_code, 400)
        self.assertEqual(self.give_back(4).status_code, 201)
        self.assertEqual(sum(SaleReturn.objects.values_list("quantity", flat=True)), 10)
        listed = self.client_for(self.pharmacist).get(f"/api/pharmacy-sales/{self.sale.pk}/").json()
        self.assertEqual(listed["returned_quantity"], 10)

    def test_expired_batch_is_never_restocked(self):
        Medicine.objects.filter(pk=self.brand.pk).update(expiry_date=hospital_today() - timedelta(days=1))
        self.assertEqual(self.give_back(2, restock=True).status_code, 400)
        self.assertEqual(self.give_back(2, restock=False).status_code, 201)

    def test_returns_need_a_pharmacist_and_a_reason(self):
        self.assertEqual(self.give_back(1, user=self.compounder).status_code, 403)
        self.assertEqual(self.give_back(1, reason="").status_code, 400)
        self.assertFalse(SaleReturn.objects.exists())
