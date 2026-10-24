"""Tests for the procurement (purchase / GRN) backend.

Covers:
  * Supplier CRUD + hospital scoping + per-hospital uniqueness
  * PurchaseOrder create (nested items) + server-side line_total
  * Atomic nested-create rollback on item failure
  * Cross-hospital protection (supplier + medicine)
  * Atomic GRN receive (stock up, ledger, line update, status)
  * Over-receipt rejection with no side effects (incl. cumulative)
  * Idempotency via a REQUIRED, persisted receipt reference
  * Multi-item partial / full status transitions
  * Object-level scoping (no IDOR without ?hospital=)
  * Authentication required for writes
  * Receive field fallbacks (unit_cost / batch / expiry_date)
  * Medicine with hospital=None is rejected
  * Read-only GRN / GRN-item / stock ledger endpoints
"""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import serializers as drf_serializers
from rest_framework.test import APIClient

from hospital.models import Hospital
from pharmacy.models import Medicine
from users.models import StaffProfile, StaffHospitalMembership, StaffRole

from .models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseItem,
    PurchaseOrder,
    StockTransaction,
    Supplier,
)
from .services import receive_purchase


def results(response):
    """Unwrap DRF pagination if present."""
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def error_details(response):
    """Extract field errors from custom exception handler format.

    The custom handler wraps errors as:
    {"error": True, "status_code": 400, "message": "...", "details": {"field": [...], ...}}
    OR (older format):
    {"error": {"code": "...", "message": "...", "details": {"field": [...], ...}}}
    """
    data = response.data
    if isinstance(data, dict) and "error" in data:
        error_obj = data["error"]
        if isinstance(error_obj, dict):
            return error_obj.get("details", {})
        elif error_obj is True:
            return data.get("details", {})
    return data


class ProcurementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create a staff user with INVENTORY_STAFF role and hospital membership
        self.user = get_user_model().objects.create_user(
            username="procurement-tester",
            password="test-pass-123",
            email="procurement@hospital.com",
        )
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            role=StaffRole.INVENTORY_STAFF,
            employee_id="EMP-INV-001",
            is_active_staff=True,
        )
        self.hospital_a = Hospital.objects.create(name="Hospital A")
        self.hospital_b = Hospital.objects.create(name="Hospital B")

        StaffHospitalMembership.objects.create(
            staff=self.staff_profile,
            hospital=self.hospital_a,
            role=StaffRole.INVENTORY_STAFF,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

        self.supplier_a = Supplier.objects.create(
            name="Acme Pharma",
            hospital=self.hospital_a,
            phone="9000000001",
        )
        self.supplier_b = Supplier.objects.create(
            name="Beta Distributors",
            hospital=self.hospital_b,
        )

        self.medicine_a = Medicine.objects.create(
            name="Paracetamol",
            hospital=self.hospital_a,
            category="Tablet",
            batch="PCM1",
            quantity=100,
            price=Decimal("2.50"),
        )
        self.medicine_b = Medicine.objects.create(
            name="Amoxicillin",
            hospital=self.hospital_b,
            category="Capsule",
            batch="AMX1",
            quantity=50,
            price=Decimal("6.00"),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def scoped(self, path):
        return f"{path}?hospital={self.hospital_a.id}"

    def purchases_url(self):
        return self.scoped("/api/procurement/purchases/")

    def suppliers_url(self):
        return self.scoped("/api/procurement/suppliers/")

    def purchase_payload(self, reference="PO-100", supplier=None, items=None):
        supplier = supplier or self.supplier_a
        items = items or [
            {
                "medicine": self.medicine_a.id,
                "batch": "B1",
                "quantity_ordered": 10,
                "unit_cost": "2.00",
            }
        ]
        return {
            "supplier": supplier.id,
            "reference": reference,
            "purchase_date": "2026-09-14",
            "items": items,
        }

    def make_order_with_item(self, quantity=10, reference="PO-200"):
        """Create a PurchaseOrder + one line directly via the ORM."""
        order = PurchaseOrder.objects.create(
            hospital=self.hospital_a,
            supplier=self.supplier_a,
            reference=reference,
            purchase_date=date(2026, 9, 14),
        )
        item = PurchaseItem.objects.create(
            purchase=order,
            medicine=self.medicine_a,
            batch="B1",
            quantity_ordered=quantity,
            unit_cost=Decimal("2.00"),
            line_total=Decimal("2.00") * quantity,
        )
        return order, item

    def make_order_with_two_items(self, quantity=10, reference="PO-MULTI"):
        order = PurchaseOrder.objects.create(
            hospital=self.hospital_a,
            supplier=self.supplier_a,
            reference=reference,
            purchase_date=date(2026, 9, 14),
        )
        item1 = PurchaseItem.objects.create(
            purchase=order,
            medicine=self.medicine_a,
            batch="B1",
            quantity_ordered=quantity,
            unit_cost=Decimal("2.00"),
            line_total=Decimal("2.00") * quantity,
        )
        item2 = PurchaseItem.objects.create(
            purchase=order,
            medicine=self.medicine_a,
            batch="B2",
            quantity_ordered=quantity,
            unit_cost=Decimal("3.00"),
            line_total=Decimal("3.00") * quantity,
        )
        return order, item1, item2

    def receive_url(self, order):
        return self.scoped(
            f"/api/procurement/purchases/{order.id}/receive/"
        )

    # ------------------------------------------------------------------
    # Supplier
    # ------------------------------------------------------------------
    def test_supplier_crud(self):
        create = self.client.post(
            self.suppliers_url(),
            {
                "name": "Gamma Supplies",
                "contact_person": "Ravi",
                "phone": "9000000002",
                "email": "gamma@example.com",
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        supplier_id = create.data["id"]
        self.assertEqual(create.data["hospital"], self.hospital_a.id)

        # Detail access MUST be hospital-scoped.
        detail = self.client.get(
            self.scoped(f"/api/procurement/suppliers/{supplier_id}/")
        )
        self.assertEqual(detail.status_code, 200)

        patch = self.client.patch(
            self.scoped(f"/api/procurement/suppliers/{supplier_id}/"),
            {"phone": "9000000003"},
            format="json",
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.data["phone"], "9000000003")

        delete = self.client.delete(
            self.scoped(f"/api/procurement/suppliers/{supplier_id}/")
        )
        self.assertEqual(delete.status_code, 204)

    def test_supplier_list_filter_by_hospital(self):
        response = self.client.get(self.suppliers_url())
        self.assertEqual(response.status_code, 200)
        rows = results(response)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Acme Pharma")
        self.assertEqual(rows[0]["hospital"], self.hospital_a.id)

    def test_supplier_requires_hospital(self):
        # No ?hospital= and no explicit hospital -> clean 400, not 500.
        response = self.client.post(
            "/api/procurement/suppliers/",
            {"name": "Homeless Supplier"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("hospital", error_details(response))

    def test_supplier_name_unique_per_hospital(self):
        # Same name in the same hospital is rejected at the DB level.
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Supplier.objects.create(
                    name="Acme Pharma",
                    hospital=self.hospital_a,
                )

        # Same name in a different hospital is fine.
        other = Supplier.objects.create(
            name="Acme Pharma",
            hospital=self.hospital_b,
        )
        self.assertEqual(other.hospital_id, self.hospital_b.id)

    # ------------------------------------------------------------------
    # Purchase orders / items
    # ------------------------------------------------------------------
    def test_purchase_create_with_nested_items(self):
        response = self.client.post(
            self.purchases_url(),
            self.purchase_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["reference"], "PO-100")
        self.assertEqual(response.data["status"], "Ordered")
        self.assertEqual(response.data["supplier"], self.supplier_a.id)
        self.assertEqual(len(response.data["items"]), 1)

        order = PurchaseOrder.objects.get(pk=response.data["id"])
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().medicine_id, self.medicine_a.id)

    def test_purchase_line_total_is_computed(self):
        response = self.client.post(
            self.purchases_url(),
            self.purchase_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        item = PurchaseItem.objects.get(purchase_id=response.data["id"])
        # 10 x 2.00 == 20.00
        self.assertEqual(item.line_total, Decimal("20.00"))
        self.assertEqual(item.quantity_remaining, 10)

    def test_purchase_create_rolls_back_when_item_creation_fails(self):
        """A failing nested line must roll back the whole purchase."""
        payload = self.purchase_payload(
            items=[
                {
                    "medicine": self.medicine_a.id,
                    "batch": "B1",
                    "quantity_ordered": 5,
                    "unit_cost": "1.00",
                },
                {
                    "medicine": self.medicine_a.id,
                    "batch": "B2",
                    "quantity_ordered": 5,
                    "unit_cost": "1.00",
                },
            ]
        )

        real_create = PurchaseItem.objects.create
        calls = {"n": 0}

        def flaky_create(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise drf_serializers.ValidationError("simulated failure")
            return real_create(*args, **kwargs)

        with mock.patch.object(
            PurchaseItem.objects, "create", side_effect=flaky_create
        ):
            response = self.client.post(
                self.purchases_url(), payload, format="json"
            )

        self.assertEqual(response.status_code, 400)
        # The header created before the failing line must NOT persist.
        self.assertEqual(PurchaseOrder.objects.count(), 0)
        self.assertEqual(PurchaseItem.objects.count(), 0)

    def test_purchase_rejects_supplier_from_other_hospital(self):
        response = self.client.post(
            self.purchases_url(),
            self.purchase_payload(supplier=self.supplier_b),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("supplier", error_details(response))

    def test_purchase_rejects_medicine_from_other_hospital(self):
        payload = self.purchase_payload(
            items=[
                {
                    "medicine": self.medicine_b.id,
                    "quantity_ordered": 5,
                    "unit_cost": "3.00",
                }
            ]
        )
        response = self.client.post(
            self.purchases_url(), payload, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("items", error_details(response))

    def test_purchase_list_filter_by_hospital(self):
        self.client.post(
            self.purchases_url(),
            self.purchase_payload(reference="PO-A1"),
            format="json",
        )
        self.client.post(
            self.purchases_url(),
            self.purchase_payload(reference="PO-A2"),
            format="json",
        )

        # A purchase in another hospital must not leak in.
        order_b = PurchaseOrder.objects.create(
            hospital=self.hospital_b,
            supplier=self.supplier_b,
            reference="PO-B1",
            purchase_date=date(2026, 9, 14),
        )

        response = self.client.get(self.purchases_url())
        self.assertEqual(response.status_code, 200)
        rows = results(response)
        references = {row["reference"] for row in rows}
        self.assertEqual(references, {"PO-A1", "PO-A2"})
        self.assertNotIn(order_b.reference, references)

    def test_purchase_item_cross_hospital_rejected(self):
        order, _ = self.make_order_with_item()
        response = self.client.post(
            "/api/procurement/purchase-items/",
            {
                "purchase": order.id,
                "medicine": self.medicine_b.id,
                "quantity_ordered": 5,
                "unit_cost": "1.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("medicine", error_details(response))

    def test_purchase_reference_unique_per_hospital(self):
        PurchaseOrder.objects.create(
            hospital=self.hospital_a,
            supplier=self.supplier_a,
            reference="PO-UNI",
            purchase_date=date(2026, 9, 14),
        )

        # Same reference + same hospital -> DB error.
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                PurchaseOrder.objects.create(
                    hospital=self.hospital_a,
                    supplier=self.supplier_a,
                    reference="PO-UNI",
                    purchase_date=date(2026, 9, 14),
                )

        # Same reference in another hospital is allowed.
        other = PurchaseOrder.objects.create(
            hospital=self.hospital_b,
            supplier=self.supplier_b,
            reference="PO-UNI",
            purchase_date=date(2026, 9, 14),
        )
        self.assertEqual(other.hospital_id, self.hospital_b.id)

    # ------------------------------------------------------------------
    # Atomic GRN receive
    # ------------------------------------------------------------------
    def test_receive_increases_stock_and_creates_grn(self):
        order, item = self.make_order_with_item(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-1",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 10}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["reference"], "GRN-1")
        self.assertEqual(response.data["supplier"], self.supplier_a.id)

        self.assertEqual(GoodsReceipt.objects.count(), 1)
        self.assertEqual(GoodsReceiptItem.objects.count(), 1)

        after = Medicine.objects.get(pk=self.medicine_a.pk).quantity
        self.assertEqual(after, before + 10)

    def test_receive_creates_stock_transaction(self):
        order, item = self.make_order_with_item(quantity=6)

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-2",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 6}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        ledger = StockTransaction.objects.filter(
            reference="GRN-2",
            transaction_type=StockTransaction.TYPE_IN,
        )
        self.assertEqual(ledger.count(), 1)
        self.assertEqual(ledger.first().quantity, 6)
        self.assertEqual(ledger.first().hospital_id, self.hospital_a.id)

    def test_receive_updates_quantity_received(self):
        order, item = self.make_order_with_item(quantity=10)

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-3",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 4}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        item.refresh_from_db()
        self.assertEqual(item.quantity_received, 4)
        self.assertEqual(item.quantity_remaining, 6)

    def test_receive_sets_status_received_when_complete(self):
        order, item = self.make_order_with_item(quantity=10)

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-4",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 10}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        order.refresh_from_db()
        self.assertEqual(order.status, PurchaseOrder.STATUS_RECEIVED)

    def test_receive_sets_status_partial_on_partial_receipt(self):
        order, item = self.make_order_with_item(quantity=10)

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-5",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 3}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        order.refresh_from_db()
        self.assertEqual(order.status, PurchaseOrder.STATUS_PARTIAL)

    def test_multi_item_partial_then_full_status(self):
        order, item1, item2 = self.make_order_with_two_items(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        # First receipt: item1 fully, item2 partially -> Partial.
        first = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-M1",
                "items": [
                    {"purchase_item": item1.id, "quantity_received": 10},
                    {"purchase_item": item2.id, "quantity_received": 4},
                ],
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        order.refresh_from_db()
        self.assertEqual(order.status, PurchaseOrder.STATUS_PARTIAL)
        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before + 14
        )

        # Second receipt completes the remaining line -> Received.
        second = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-M2",
                "items": [
                    {"purchase_item": item2.id, "quantity_received": 6}
                ],
            },
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.data)
        order.refresh_from_db()
        self.assertEqual(order.status, PurchaseOrder.STATUS_RECEIVED)

    def test_receive_applies_unit_cost_batch_expiry_fallbacks(self):
        order = PurchaseOrder.objects.create(
            hospital=self.hospital_a,
            supplier=self.supplier_a,
            reference="PO-FB",
            purchase_date=date(2026, 9, 14),
        )
        item = PurchaseItem.objects.create(
            purchase=order,
            medicine=self.medicine_a,
            batch="BATCH-X",
            expiry_date=date(2027, 1, 31),
            quantity_ordered=5,
            unit_cost=Decimal("4.25"),
            line_total=Decimal("4.25") * 5,
        )

        # Only the required fields are sent; the rest must be inherited
        # from the purchase line.
        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-FB",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 5}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        grn_item = GoodsReceiptItem.objects.get(
            goods_receipt__reference="GRN-FB"
        )
        self.assertEqual(grn_item.batch, "BATCH-X")
        self.assertEqual(grn_item.unit_cost, Decimal("4.25"))
        self.assertEqual(grn_item.expiry_date, date(2027, 1, 31))

    # ------------------------------------------------------------------
    # Safety guarantees
    # ------------------------------------------------------------------
    def test_over_receipt_is_rejected_without_stock_change(self):
        order, item = self.make_order_with_item(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-6",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 11}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        # Nothing changed: stock, receipt, ledger, line.
        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before
        )
        self.assertEqual(GoodsReceipt.objects.count(), 0)
        self.assertEqual(GoodsReceiptItem.objects.count(), 0)
        self.assertEqual(StockTransaction.objects.count(), 0)
        item.refresh_from_db()
        self.assertEqual(item.quantity_received, 0)

    def test_cumulative_over_receipt_is_rejected(self):
        order, item = self.make_order_with_item(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        first = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-C1",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 6}
                ],
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before + 6
        )

        # 6 already received of 10 -> another 6 exceeds the line.
        second = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-C2",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 6}
                ],
            },
            format="json",
        )
        self.assertEqual(second.status_code, 400)
        self.assertIn("items", error_details(second))

        # Stock only reflects the first successful receipt.
        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before + 6
        )
        self.assertEqual(GoodsReceipt.objects.count(), 1)

    def test_receive_requires_a_reference(self):
        order, item = self.make_order_with_item(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        response = self.client.post(
            self.receive_url(order),
            {"items": [{"purchase_item": item.id, "quantity_received": 3}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("reference", error_details(response))

        # No stock movement, no receipt.
        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before
        )
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_receive_replay_without_reference_never_double_increments(self):
        order, item = self.make_order_with_item(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        # Two identical, reference-less submissions must BOTH be rejected.
        payload = {
            "items": [{"purchase_item": item.id, "quantity_received": 3}]
        }
        first = self.client.post(
            self.receive_url(order), payload, format="json"
        )
        second = self.client.post(
            self.receive_url(order), payload, format="json"
        )

        self.assertEqual(first.status_code, 400)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before
        )
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_receive_is_idempotent_by_reference(self):
        order, item = self.make_order_with_item(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        payload = {
            "reference": "INV-777",
            "items": [{"purchase_item": item.id, "quantity_received": 4}],
        }
        first = self.client.post(
            self.receive_url(order), payload, format="json"
        )
        self.assertEqual(first.status_code, 201, first.data)

        after_first = Medicine.objects.get(pk=self.medicine_a.pk).quantity
        self.assertEqual(after_first, before + 4)

        # Replaying the same reference must NOT double-increment stock.
        second = self.client.post(
            self.receive_url(order), payload, format="json"
        )
        self.assertEqual(second.status_code, 400)
        self.assertIn("reference", error_details(second))

        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity,
            after_first,
        )
        self.assertEqual(GoodsReceipt.objects.count(), 1)

    def test_goods_receipt_reference_unique_per_hospital(self):
        order, item = self.make_order_with_item(quantity=5)
        self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-UNI",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 1}
                ],
            },
            format="json",
        )

        with self.assertRaises(IntegrityError):
            GoodsReceipt.objects.create(
                hospital=self.hospital_a,
                purchase=order,
                supplier=self.supplier_a,
                reference="GRN-UNI",
                receipt_date=date(2026, 9, 14),
            )

    def test_receive_duplicate_purchase_item_rejected(self):
        order, item = self.make_order_with_item(quantity=10)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-DUP",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 2},
                    {"purchase_item": item.id, "quantity_received": 2},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("items", error_details(response))

        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before
        )
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_receive_cancelled_purchase_is_rejected(self):
        order, item = self.make_order_with_item(quantity=10)
        order.status = PurchaseOrder.STATUS_CANCELLED
        order.save(update_fields=["status"])

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-8",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 1}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_receive_rejects_cross_hospital_purchase(self):
        order, item = self.make_order_with_item(quantity=10)

        # Scoping to another hospital hides the order (404).
        response = self.client.post(
            f"/api/procurement/purchases/{order.id}/receive/"
            f"?hospital={self.hospital_b.id}",
            {
                "reference": "GRN-9",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 1}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        # Defence in depth: the service itself rejects a mismatched scope.
        with self.assertRaises(drf_serializers.ValidationError):
            receive_purchase(
                purchase=order,
                payload={
                    "reference": "GRN-9B",
                    "items": [
                        {"purchase_item": item.id, "quantity_received": 1}
                    ],
                },
                scoped_hospital=self.hospital_b,
            )

        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_receive_rejects_medicine_without_hospital(self):
        orphan = Medicine.objects.create(
            name="Unassigned Medicine",
            hospital=None,
            batch="ORPHAN",
            quantity=5,
            price=Decimal("1.00"),
        )
        order = PurchaseOrder.objects.create(
            hospital=self.hospital_a,
            supplier=self.supplier_a,
            reference="PO-ORPHAN",
            purchase_date=date(2026, 9, 14),
        )
        item = PurchaseItem.objects.create(
            purchase=order,
            medicine=orphan,
            batch="ORPHAN",
            quantity_ordered=5,
            unit_cost=Decimal("1.00"),
            line_total=Decimal("5.00"),
        )

        response = self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-ORPHAN",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 5}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(GoodsReceipt.objects.count(), 0)
        self.assertEqual(
            Medicine.objects.get(pk=orphan.pk).quantity, 5
        )

    def test_purchase_rejects_medicine_without_hospital(self):
        orphan = Medicine.objects.create(
            name="Unassigned Medicine",
            hospital=None,
            batch="ORPHAN",
            quantity=5,
            price=Decimal("1.00"),
        )
        payload = self.purchase_payload(
            items=[
                {
                    "medicine": orphan.id,
                    "quantity_ordered": 2,
                    "unit_cost": "1.00",
                }
            ]
        )
        response = self.client.post(
            self.purchases_url(), payload, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("items", error_details(response))

    # ------------------------------------------------------------------
    # Object-level scoping (no IDOR) + authentication
    # ------------------------------------------------------------------
    def test_detail_without_hospital_param_is_not_exposed(self):
        # The shared client is authenticated, but no ?hospital= is given.
        response = self.client.get(
            f"/api/procurement/suppliers/{self.supplier_a.id}/"
        )
        self.assertEqual(response.status_code, 403)

        # Same rule for a purchase order detail.
        order, _ = self.make_order_with_item()
        detail = self.client.get(
            f"/api/procurement/purchases/{order.id}/"
        )
        self.assertEqual(detail.status_code, 403)

    def test_list_without_hospital_param_is_empty(self):
        response = self.client.get("/api/procurement/suppliers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results(response)), 0)

    def test_unscoped_update_of_another_hospital_is_blocked(self):
        # PATCH without ?hospital= cannot reach any hospital's record.
        response = self.client.patch(
            f"/api/procurement/suppliers/{self.supplier_b.id}/",
            {"phone": "111"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.supplier_b.refresh_from_db()
        self.assertEqual(self.supplier_b.phone, "")

    def test_cross_hospital_hospital_param_cannot_read_other(self):
        # Scoping to hospital_a must NOT expose hospital_b's supplier.
        response = self.client.get(
            f"/api/procurement/suppliers/{self.supplier_b.id}/"
            f"?hospital={self.hospital_a.id}"
        )
        self.assertEqual(response.status_code, 403)

    def test_writes_require_authentication(self):
        anon = APIClient()

        # Unsafe write without credentials is rejected.
        create = anon.post(
            self.suppliers_url(),
            {"name": "Anon Supplier"},
            format="json",
        )
        self.assertIn(create.status_code, (401, 403))

        # Procurement data is not public: anonymous reads are rejected too.
        listed = anon.get(self.suppliers_url())
        self.assertIn(listed.status_code, (401, 403))

        # The stock-mutating receive action is not publicly writable.
        order, item = self.make_order_with_item(quantity=5)
        before = Medicine.objects.get(pk=self.medicine_a.pk).quantity
        receive = anon.post(
            self.receive_url(order),
            {
                "reference": "GRN-ANON",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 5}
                ],
            },
            format="json",
        )
        self.assertIn(receive.status_code, (401, 403))
        self.assertEqual(
            Medicine.objects.get(pk=self.medicine_a.pk).quantity, before
        )
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    # ------------------------------------------------------------------
    # Read-only endpoints
    # ------------------------------------------------------------------
    def test_grn_and_ledger_endpoints_are_read_only(self):
        order, item = self.make_order_with_item(quantity=5)
        self.client.post(
            self.receive_url(order),
            {
                "reference": "GRN-10",
                "items": [
                    {"purchase_item": item.id, "quantity_received": 5}
                ],
            },
            format="json",
        )

        grns = self.client.get(self.scoped("/api/procurement/grns/"))
        self.assertEqual(grns.status_code, 200)
        self.assertEqual(len(results(grns)), 1)

        grn_items = self.client.get(
            self.scoped("/api/procurement/grn-items/")
        )
        self.assertEqual(grn_items.status_code, 200)
        self.assertEqual(len(results(grn_items)), 1)

        ledger = self.client.get(
            self.scoped("/api/procurement/stock-transactions/")
        )
        self.assertEqual(ledger.status_code, 200)
        self.assertEqual(len(results(ledger)), 1)

        # Write verbs are not exposed on append-only resources (403 or 405 both acceptable).
        for url in [
            "/api/procurement/grns/",
            "/api/procurement/grn-items/",
            "/api/procurement/stock-transactions/",
        ]:
            response = self.client.post(url, {}, format="json")
            self.assertIn(response.status_code, (403, 405), f"URL {url} returned {response.status_code}")
