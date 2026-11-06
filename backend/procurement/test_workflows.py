"""Requisitions (I2), quotations, PO cancellation, department issue, supplier returns, consignment (I4)."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from audit.models import AuditLog
from config.hospital_time import hospital_today
from hospital.models import Department, Hospital
from pharmacy.models import Medicine
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

from .models import (
    ConsignmentSettlement,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseRequisition,
    StockIssue,
    StockTransaction,
    Supplier,
    SupplierQuotation,
)

API = "/api/procurement"


class StoreCase(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Store", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Store", is_active=True)
        self.store, _ = make_staff("st_store", self.hospital, role=StaffRole.INVENTORY_STAFF)
        self.manager, _ = make_staff("st_manager", self.hospital, role=StaffRole.HOSPITAL_MANAGER)
        self.manager2, _ = make_staff("st_manager2", self.hospital, role=StaffRole.HOSPITAL_MANAGER)
        self.pharmacist, _ = make_staff("st_pharmacist", self.hospital, role=StaffRole.PHARMACIST)
        self.ward = Department.objects.create(hospital=self.hospital, name="Ward A")
        self.foreign_ward = Department.objects.create(hospital=self.other, name="Elsewhere")
        self.saline = Medicine.objects.create(name="NS 500 ml", hospital=self.hospital, batch="NS1", quantity=40,
                                              price=Decimal("30.00"))
        self.gloves = Medicine.objects.create(name="Gloves M", hospital=self.hospital, batch="G1", quantity=0,
                                              price=Decimal("5.00"))
        self.supplier = Supplier.objects.create(name="Synthetic Pharma", hospital=self.hospital)
        self.supplier2 = Supplier.objects.create(name="Synthetic Distributors", hospital=self.hospital)

    def client_for(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def post(self, user, path, body):
        return self.client_for(user).post(f"{API}/{path}?hospital={self.hospital.id}", body, format="json")

    def requisition(self, user=None):
        resp = self.post(user or self.pharmacist, "requisitions/", {
            "department": self.ward.id, "reason": "Monthly ward stock",
            "items": [{"medicine": self.saline.id, "quantity": 20}, {"medicine": self.gloves.id, "quantity": 100}],
        })
        self.assertEqual(resp.status_code, 201, resp.content)
        return PurchaseRequisition.objects.get(pk=resp.json()["id"])

    def approved(self):
        req = self.requisition()
        self.assertEqual(self.post(self.manager, f"requisitions/{req.id}/approve/", {}).status_code, 200)
        req.refresh_from_db()
        return req


class RequisitionTests(StoreCase):
    def test_raised_then_approved_by_someone_else_and_ordered(self):
        req = self.requisition(user=self.manager)
        self.assertEqual(req.status, "Submitted")
        self.assertEqual(self.post(self.manager, f"requisitions/{req.id}/approve/", {}).status_code, 400)
        self.assertEqual(self.post(self.store, f"requisitions/{req.id}/approve/", {}).status_code, 403)
        self.assertEqual(self.post(self.manager2, f"requisitions/{req.id}/approve/", {}).status_code, 200)
        self.assertEqual(self.post(self.manager2, f"requisitions/{req.id}/approve/", {}).status_code, 400)

        items = list(req.items.order_by("id"))
        missing = self.post(self.store, f"requisitions/{req.id}/order/",
                            {"supplier": self.supplier.id, "unit_costs": [{"item": items[0].id, "unit_cost": "28.00"}]})
        self.assertEqual(missing.status_code, 400)
        resp = self.post(self.store, f"requisitions/{req.id}/order/", {
            "supplier": self.supplier.id,
            "unit_costs": [{"item": items[0].id, "unit_cost": "28.00"}, {"item": items[1].id, "unit_cost": "4.50"}],
        })
        self.assertEqual(resp.status_code, 201, resp.content)
        req.refresh_from_db()
        self.assertEqual((req.status, req.purchase_order.status), ("Ordered", "Ordered"))
        self.assertEqual(sorted(i.quantity_ordered for i in req.purchase_order.items.all()), [20, 100])
        self.assertTrue(AuditLog.objects.filter(action="procurement.purchaserequisition.approved", user=self.manager2).exists())

    def test_rejection_needs_a_reason_and_a_rejected_one_cannot_be_ordered(self):
        req = self.requisition()
        self.assertEqual(self.post(self.manager, f"requisitions/{req.id}/reject/", {}).status_code, 400)
        self.assertEqual(self.post(self.manager, f"requisitions/{req.id}/reject/", {"note": "Stock enough"}).status_code, 200)
        item = req.items.first()
        resp = self.post(self.store, f"requisitions/{req.id}/order/",
                         {"supplier": self.supplier.id, "unit_costs": [{"item": item.id, "unit_cost": "1"}]})
        self.assertEqual(resp.status_code, 400)

    def test_requisition_only_for_this_hospitals_stock(self):
        foreign = Medicine.objects.create(name="Foreign", hospital=self.other, quantity=5, price=Decimal("1"))
        resp = self.post(self.pharmacist, "requisitions/", {"items": [{"medicine": foreign.id, "quantity": 1}]})
        self.assertEqual(resp.status_code, 400)


class QuotationTests(StoreCase):
    def quote(self, req, supplier, costs, valid_until=None):
        items = list(req.items.order_by("id"))
        return self.post(self.store, "quotations/", {
            "requisition": req.id, "supplier": supplier.id, "reference": f"Q-{supplier.id}",
            "valid_until": valid_until,
            "items": [{"requisition_item": item.id, "unit_cost": cost} for item, cost in zip(items, costs)],
        })

    def test_accepting_one_quotation_orders_at_its_prices_and_closes_the_others(self):
        req = self.approved()
        self.assertEqual(self.quote(req, self.supplier, ["29.00", "5.00"]).status_code, 201)
        cheaper = self.quote(req, self.supplier2, ["27.00", "4.00"])
        self.assertEqual(cheaper.status_code, 201, cheaper.content)
        self.assertEqual(cheaper.json()["total"], "940.00")
        resp = self.post(self.store, f"quotations/{cheaper.json()['id']}/accept/", {})
        self.assertEqual(resp.status_code, 201, resp.content)
        po = PurchaseOrder.objects.get()
        self.assertEqual(po.supplier, self.supplier2)
        self.assertEqual(sorted(str(i.unit_cost) for i in po.items.all()), ["27.00", "4.00"])
        self.assertEqual(sorted(SupplierQuotation.objects.values_list("status", flat=True)), ["Accepted", "Rejected"])

    def test_quotation_must_cover_every_line_and_not_be_expired(self):
        req = self.approved()
        partial = self.post(self.store, "quotations/", {"requisition": req.id, "supplier": self.supplier.id,
                                                        "reference": "Q1", "items": [
            {"requisition_item": req.items.first().id, "unit_cost": "1.00"}]})
        self.assertEqual(partial.status_code, 400)
        stale = self.quote(req, self.supplier, ["1", "1"], valid_until=str(hospital_today() - timedelta(days=1)))
        self.assertEqual(stale.status_code, 201)
        self.assertEqual(self.post(self.store, f"quotations/{stale.json()['id']}/accept/", {}).status_code, 400)

    def test_no_quotation_before_approval(self):
        req = self.requisition()
        self.assertEqual(self.quote(req, self.supplier, ["1", "1"]).status_code, 400)


class PurchaseCancelTests(StoreCase):
    def order(self):
        req = self.approved()
        items = list(req.items.order_by("id"))
        self.post(self.store, f"requisitions/{req.id}/order/", {
            "supplier": self.supplier.id,
            "unit_costs": [{"item": items[0].id, "unit_cost": "28"}, {"item": items[1].id, "unit_cost": "4"}]})
        req.refresh_from_db()
        return req, req.purchase_order

    def test_manager_cancels_with_a_reason_and_the_requisition_can_be_reordered(self):
        req, po = self.order()
        self.assertEqual(self.post(self.store, f"purchases/{po.id}/cancel/", {"reason": "Wrong supplier"}).status_code, 403)
        self.assertEqual(self.post(self.manager, f"purchases/{po.id}/cancel/", {}).status_code, 400)
        resp = self.post(self.manager, f"purchases/{po.id}/cancel/", {"reason": "Wrong supplier"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "Cancelled")
        req.refresh_from_db()
        self.assertEqual((req.status, req.purchase_order), ("Approved", None))
        self.assertTrue(AuditLog.objects.filter(action="procurement.purchaseorder.cancelled", user=self.manager).exists())

    def test_no_cancel_after_goods_arrive_and_no_status_edits(self):
        _, po = self.order()
        line = po.items.get(medicine=self.saline)
        received = self.post(self.store, f"purchases/{po.id}/receive/",
                             {"reference": "INV-1", "items": [{"purchase_item": line.id, "quantity_received": 5}]})
        self.assertEqual(received.status_code, 201, received.content)
        self.assertEqual(self.post(self.manager, f"purchases/{po.id}/cancel/", {"reason": "x"}).status_code, 400)
        patch = self.client_for(self.store).patch(f"{API}/purchases/{po.id}/?hospital={self.hospital.id}",
                                                  {"status": "Received"}, format="json")
        self.assertEqual(patch.status_code, 400)


class StockIssueTests(StoreCase):
    def issue(self, quantity, key="", department=None, medicine=None):
        return self.post(self.store, "stock-issues/", {"department": (department or self.ward).id,
                                                       "medicine": (medicine or self.saline).id, "quantity": quantity,
                                                       "received_by_name": "Sister Synthetic", "idempotency_key": key})

    def test_issue_lowers_stock_once_per_key_with_a_ledger_row(self):
        self.assertEqual(self.issue(10, key="iss-1").status_code, 201)
        self.assertEqual(self.issue(10, key="iss-1").status_code, 200)
        self.saline.refresh_from_db()
        self.assertEqual(self.saline.quantity, 30)
        self.assertEqual(StockIssue.objects.count(), 1)
        self.assertTrue(StockTransaction.objects.filter(transaction_type="OUT", reason="Issued to Ward A").exists())

    def test_never_below_zero_never_expired_never_another_hospital(self):
        self.assertEqual(self.issue(41).status_code, 400)
        self.assertIn(self.issue(1, department=self.foreign_ward).status_code, (400, 403))
        Medicine.objects.filter(pk=self.saline.pk).update(expiry_date=hospital_today() - timedelta(days=1))
        self.assertEqual(self.issue(1).status_code, 400)
        self.saline.refresh_from_db()
        self.assertEqual(self.saline.quantity, 40)

    def test_pharmacist_cannot_issue_from_the_store(self):
        resp = self.client_for(self.pharmacist).post(f"{API}/stock-issues/?hospital={self.hospital.id}", {
            "department": self.ward.id, "medicine": self.saline.id, "quantity": 1}, format="json")
        self.assertEqual(resp.status_code, 403)


class SupplierReturnAndConsignmentTests(StoreCase):
    def received(self, consignment=False):
        po = PurchaseOrder.objects.create(hospital=self.hospital, supplier=self.supplier, reference="PO-R",
                                          purchase_date=hospital_today(), is_consignment=consignment)
        line = po.items.create(medicine=self.gloves, quantity_ordered=10, unit_cost=Decimal("4.00"),
                               line_total=Decimal("40.00"))
        resp = self.post(self.store, f"purchases/{po.id}/receive/",
                         {"reference": "INV-R", "items": [{"purchase_item": line.id, "quantity_received": 10}]})
        self.assertEqual(resp.status_code, 201, resp.content)
        return GoodsReceiptItem.objects.get(goods_receipt__purchase=po)

    def test_return_lowers_stock_with_credit_and_never_more_than_received(self):
        item = self.received()
        resp = self.post(self.store, "supplier-returns/", {"receipt_item": item.id, "quantity": 4, "reason": "Torn packs"})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["credit_amount"], "16.00")
        self.gloves.refresh_from_db()
        self.assertEqual(self.gloves.quantity, 6)
        self.assertEqual(self.post(self.store, "supplier-returns/",
                                   {"receipt_item": item.id, "quantity": 7, "reason": "More"}).status_code, 400)

    def test_consignment_is_settled_for_what_was_used_and_the_rest_returned(self):
        plain = self.received()
        self.assertEqual(self.post(self.store, "consignment-settlements/",
                                   {"receipt_item": plain.id, "quantity": 1}).status_code, 400)
        item = self.received_consignment()
        settled = self.post(self.store, "consignment-settlements/", {"receipt_item": item.id, "quantity": 3,
                                                                     "reference": "Usage Nov"})
        self.assertEqual(settled.status_code, 201, settled.content)
        self.assertEqual(settled.json()["amount"], "12.00")
        self.assertEqual(self.post(self.store, "supplier-returns/",
                                   {"receipt_item": item.id, "quantity": 7, "reason": "Unused consignment"}).status_code, 201)
        self.assertEqual(self.post(self.store, "consignment-settlements/",
                                   {"receipt_item": item.id, "quantity": 1}).status_code, 400)
        self.assertEqual(ConsignmentSettlement.objects.count(), 1)

    def received_consignment(self):
        po = PurchaseOrder.objects.create(hospital=self.hospital, supplier=self.supplier, reference="PO-C",
                                          purchase_date=hospital_today(), is_consignment=True)
        line = po.items.create(medicine=self.gloves, quantity_ordered=10, unit_cost=Decimal("4.00"),
                               line_total=Decimal("40.00"))
        self.post(self.store, f"purchases/{po.id}/receive/",
                  {"reference": "INV-C", "items": [{"purchase_item": line.id, "quantity_received": 10}]})
        return GoodsReceiptItem.objects.get(goods_receipt__purchase=po)
