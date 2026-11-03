"""Per-item stock settings (unit, reorder level, usual supplier) and what the store UI needs to receive goods."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from pharmacy.models import Medicine
from procurement.models import PurchaseItem, PurchaseOrder, Supplier
from reports.services import KPIService
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class StockSettingsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Store A", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Store B", is_active=True)
        cls.store_user, _ = make_staff("stock_store", cls.hospital, role=StaffRole.INVENTORY_STAFF)
        cls.supplier = Supplier.objects.create(name="Synthetic Pharma", hospital=cls.hospital)
        cls.foreign_supplier = Supplier.objects.create(name="Other Pharma", hospital=cls.other_hospital)

    def setUp(self):
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.store_user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def create_medicine(self, **extra):
        payload = {"name": "Synthetic Gauze", "hospital": self.hospital.id, "category": "Surgical",
                   "quantity": 5, "price": "12.00", **extra}
        return self.client.post(f"/api/pharmacy/?hospital={self.hospital.id}", payload, format="json")

    def test_unit_reorder_level_and_supplier_are_stored(self):
        response = self.create_medicine(unit="Box", reorder_level=25, supplier=self.supplier.id)

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body["unit"], body["reorder_level"], body["supplier"]), ("Box", 25, self.supplier.id))
        self.assertEqual(body["supplier_name"], "Synthetic Pharma")

    def test_defaults_when_not_given(self):
        body = self.create_medicine().json()

        self.assertEqual((body["unit"], body["reorder_level"], body["supplier"]), ("Unit", 10, None))

    def test_supplier_of_another_hospital_is_refused(self):
        response = self.create_medicine(supplier=self.foreign_supplier.id)

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("supplier", response.content.decode())

    def test_low_stock_report_uses_each_items_reorder_level(self):
        Medicine.objects.create(name="Above own level", hospital=self.hospital, quantity=15,
                                price=Decimal("1"), reorder_level=10)
        Medicine.objects.create(name="Below own level", hospital=self.hospital, quantity=15,
                                price=Decimal("1"), reorder_level=30)

        kpis = KPIService(self.hospital.id).get_pharmacy_kpis()

        self.assertEqual(kpis["low_stock"], 1)

    def test_purchase_order_lines_carry_what_receiving_needs(self):
        medicine = Medicine.objects.create(name="Synthetic Saline", hospital=self.hospital,
                                           quantity=0, price=Decimal("30"))
        order = PurchaseOrder.objects.create(hospital=self.hospital, supplier=self.supplier,
                                             reference="PO-SYN-1", purchase_date=date(2026, 11, 3))
        line = PurchaseItem.objects.create(purchase=order, medicine=medicine, quantity_ordered=20,
                                           unit_cost=Decimal("25.00"), line_total=Decimal("500.00"))

        response = self.client.get(f"/api/procurement/purchases/{order.id}/?hospital={self.hospital.id}")

        self.assertEqual(response.status_code, 200, response.content)
        item = response.json()["items"][0]
        self.assertEqual(item["id"], line.id)
        self.assertEqual(item["medicine_name"], "Synthetic Saline")
        self.assertEqual(item["quantity_received"], 0)
