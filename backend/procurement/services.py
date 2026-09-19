from django.db import IntegrityError, transaction

from django.utils import timezone
from django.db.models import F
from rest_framework import serializers

from pharmacy.models import Medicine

from .models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseItem,
    PurchaseOrder,
    StockTransaction,
)


def _recompute_purchase_status(purchase):
    """Derive the PurchaseOrder status from its items.

    Returns one of Ordered / Partial / Received.
    """
    items = list(purchase.items.all())
    if not items:
        return PurchaseOrder.STATUS_ORDERED

    if all(
        item.quantity_received >= item.quantity_ordered
        for item in items
    ):
        return PurchaseOrder.STATUS_RECEIVED

    if any(item.quantity_received > 0 for item in items):
        return PurchaseOrder.STATUS_PARTIAL

    return PurchaseOrder.STATUS_ORDERED


@transaction.atomic
def receive_purchase(purchase, payload, scoped_hospital=None):
    """Atomically receive stock against a PurchaseOrder (GRN).

    Every step runs inside a single ``transaction.atomic`` block. If
    ANY validation fails, or ANY write raises, the entire operation
    rolls back: ``Medicine.quantity`` stays unchanged, no partial
    GoodsReceipt / GoodsReceiptItem / StockTransaction rows are left
    behind, and no PurchaseItem is updated.

    Idempotency:
        ``GoodsReceipt.reference`` is unique per hospital. A repeated
        request that reuses the same reference raises a validation
        error and is rejected BEFORE any stock is touched. A stable
        ``reference`` is REQUIRED (e.g. the supplier invoice number);
        without it a replayed request would be indistinguishable from a
        brand-new receipt and could double-increment stock.
    """
    # 1. Validate the PurchaseOrder state.
    if purchase.status == PurchaseOrder.STATUS_CANCELLED:
        raise serializers.ValidationError(
            {"status": "A cancelled purchase order cannot be received."}
        )
    if purchase.status == PurchaseOrder.STATUS_RECEIVED:
        raise serializers.ValidationError(
            {"status": "This purchase order has already been received."}
        )

    # 2. Validate hospital scoping.
    if scoped_hospital is not None and purchase.hospital_id != scoped_hospital.pk:
        raise serializers.ValidationError(
            {"hospital": "Purchase order does not belong to the selected hospital."}
        )

    hospital = purchase.hospital

    # 3. Validate every received medicine and quantity.
    #
    # ``payload`` normally comes from GoodsReceiptReceiveSerializer, but
    # receive_purchase can also be called directly, so validate the
    # input defensively and raise a controlled error instead of a
    # KeyError (which would surface as an HTTP 500).
    lines = payload.get("items")
    if not lines:
        raise serializers.ValidationError(
            {"items": "At least one received item is required."}
        )

    seen_purchase_items = set()
    for line in lines:
        purchase_item_id = line["purchase_item"]
        if purchase_item_id in seen_purchase_items:
            raise serializers.ValidationError(
                {
                    "items": (
                        "Duplicate purchase item in a single receipt: "
                        f"{purchase_item_id}."
                    )
                }
            )
        seen_purchase_items.add(purchase_item_id)

    purchase_items = {
        item.pk: item
        for item in PurchaseItem.objects.select_related("medicine").filter(
            pk__in=seen_purchase_items,
            purchase=purchase,
        )
    }

    if len(purchase_items) != len(seen_purchase_items):
        raise serializers.ValidationError(
            {"items": "One or more purchase items are invalid for this order."}
        )

    # Validate quantities against the remaining amount (prevents
    # over-receiving) and medicine ownership.
    for line in lines:
        purchase_item = purchase_items[line["purchase_item"]]
        medicine = purchase_item.medicine

        # A medicine must be assigned to exactly this hospital. A
        # medicine with no hospital cannot be safely stocked, so it is
        # rejected rather than silently updated.
        if medicine.hospital_id != hospital.pk:
            raise serializers.ValidationError(
                {
                    "items": (
                        f"Medicine '{medicine.name}' does not belong to "
                        "this hospital."
                    )
                }
            )

        received = line["quantity_received"]
        remaining = purchase_item.quantity_ordered - purchase_item.quantity_received

        if received > remaining:
            raise serializers.ValidationError(
                {
                    "items": (
                        f"Cannot receive {received} of '{medicine.name}'. "
                        f"Only {max(remaining, 0)} remaining."
                    )
                }
            )

    # 4. Resolve the (idempotent) receipt reference.
    #
    # A stable, client-supplied reference is REQUIRED. It is the
    # idempotency key that prevents the same receipt from being applied
    # twice and double-incrementing stock. We never generate one
    # implicitly, because a generated reference would make a replayed
    # request look brand new and stock would be added again.
    reference = (payload.get("reference") or "").strip()
    if not reference:
        raise serializers.ValidationError(
            {
                "reference": (
                    "A unique receipt reference is required; it makes "
                    "receiving idempotent."
                )
            }
        )

    if GoodsReceipt.objects.filter(
        hospital=hospital, reference=reference
    ).exists():
        raise serializers.ValidationError(
            {
                "reference": (
                    "A receipt with this reference already exists for "
                    "this hospital."
                )
            }
        )

    # 5. Create the GoodsReceipt header.
    receipt_date = payload.get("receipt_date")
    if receipt_date is None:
        receipt_date = timezone.now().date()

    try:
        receipt = GoodsReceipt.objects.create(
            hospital=hospital,
            purchase=purchase,
            supplier=purchase.supplier,
            reference=reference,
            receipt_date=receipt_date,
            received_by=payload.get("received_by", "") or "",
            note=payload.get("note", "") or "",
        )
    except IntegrityError:
        # DB-level idempotency guard (concurrent duplicate).
        raise serializers.ValidationError(
            {
                "reference": (
                    "A receipt with this reference already exists for "
                    "this hospital."
                )
            }
        )

    # 6-10. Create items, increase stock, write ledger, update lines.
    for line in lines:
        purchase_item = purchase_items[line["purchase_item"]]
        medicine = purchase_item.medicine
        received = line["quantity_received"]

        unit_cost = line.get("unit_cost")
        if unit_cost is None:
            unit_cost = purchase_item.unit_cost

        batch = line.get("batch")
        if batch is None:
            batch = purchase_item.batch

        expiry_date = line.get("expiry_date")
        if expiry_date is None:
            expiry_date = purchase_item.expiry_date

        # 7. GoodsReceiptItem.
        GoodsReceiptItem.objects.create(
            goods_receipt=receipt,
            medicine=medicine,
            batch=batch or "",
            expiry_date=expiry_date,
            quantity_received=received,
            unit_cost=unit_cost,
        )

        # 8. Atomic stock increase (SQLite-safe: no SELECT FOR UPDATE).
        updated = Medicine.objects.filter(
            pk=medicine.pk,
            hospital=hospital,
        ).update(quantity=F("quantity") + received)

        if updated != 1:
            # Rollback everything.
            raise serializers.ValidationError(
                {
                    "items": (
                        f"Failed to update stock for '{medicine.name}'."
                    )
                }
            )

        # 9. Append-only ledger row.
        StockTransaction.objects.create(
            medicine=medicine,
            hospital=hospital,
            transaction_type=StockTransaction.TYPE_IN,
            quantity=received,
            reason="Goods receipt",
            reference=receipt.reference,
        )

        # 10. Update the received quantity on the order line.
        purchase_item.quantity_received += received
        purchase_item.save(update_fields=["quantity_received"])

    # 11. Update the purchase order status.
    purchase.status = _recompute_purchase_status(purchase)
    purchase.save(update_fields=["status"])

    return receipt
