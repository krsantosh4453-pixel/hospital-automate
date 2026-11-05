"""
Store workflows beyond plain purchase orders: requisition approval (I2),
quotations, purchase order cancellation, issue to departments, returns to
suppliers and consignment settlement (I4).

Every function runs in one transaction and locks the row whose balance it
checks, so concurrent requests cannot approve twice, over-issue or return
more than was received. Stock never goes below zero: decreases use a
guarded UPDATE that matches only while enough stock is left.
"""

import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework import serializers

from config.hospital_time import hospital_today
from pharmacy.models import Medicine

from .models import (
    ConsignmentSettlement,
    GoodsReceiptItem,
    PurchaseItem,
    PurchaseOrder,
    PurchaseRequisition,
    StockIssue,
    StockTransaction,
    SupplierQuotation,
    SupplierReturn,
)

CENT = Decimal("0.01")


def new_reference(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def _user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _fail(field, message):
    raise serializers.ValidationError({field: message})


def _take_stock(medicine, quantity, reason, reference):
    """Decrease stock by ``quantity`` or refuse; writes the ledger row."""
    if not Medicine.objects.filter(pk=medicine.pk, quantity__gte=quantity).update(quantity=F("quantity") - quantity):
        medicine.refresh_from_db(fields=["quantity"])
        _fail("quantity", f"Only {medicine.quantity} of {medicine.name} is in stock.")
    StockTransaction.objects.create(medicine=medicine, hospital_id=medicine.hospital_id,
                                    transaction_type=StockTransaction.TYPE_OUT, quantity=quantity,
                                    reason=reason[:255], reference=reference[:100])


# Requisitions (I2)

@transaction.atomic
def decide_requisition(requisition, user, approve, note=""):
    req = PurchaseRequisition.objects.select_for_update().get(pk=requisition.pk)
    if req.status != PurchaseRequisition.SUBMITTED:
        _fail("status", f"This requisition is {req.status.lower()}, not awaiting a decision.")
    if req.requested_by_id and req.requested_by_id == getattr(user, "pk", None):
        _fail("status", "Someone other than the requester must approve or reject it.")
    if not approve and not (note or "").strip():
        _fail("note", "Say why the requisition is rejected.")
    req.status = PurchaseRequisition.APPROVED if approve else PurchaseRequisition.REJECTED
    req.decided_by, req.decided_at, req.decision_note = _user(user), timezone.now(), (note or "").strip()[:255]
    req.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
    return req


@transaction.atomic
def order_requisition(requisition, supplier, unit_costs, user=None, reference=""):
    """Place a purchase order for an approved requisition. ``unit_costs``: requisition item id -> cost."""
    req = PurchaseRequisition.objects.select_for_update().get(pk=requisition.pk)
    if req.status != PurchaseRequisition.APPROVED:
        _fail("status", "Only an approved requisition can be ordered.")
    if supplier.hospital_id != req.hospital_id or not supplier.is_active:
        _fail("supplier", "Choose an active supplier of this hospital.")
    items = list(req.items.select_related("medicine"))
    missing = [item.medicine.name for item in items if item.pk not in unit_costs]
    if missing:
        _fail("unit_costs", f"Give a unit cost for: {', '.join(missing)}.")
    try:
        with transaction.atomic():
            po = PurchaseOrder.objects.create(hospital_id=req.hospital_id, supplier=supplier,
                                              reference=(reference or new_reference("PO"))[:100],
                                              purchase_date=hospital_today(), status=PurchaseOrder.STATUS_ORDERED)
    except IntegrityError:
        _fail("reference", "A purchase order with this reference already exists.")
    for item in items:
        cost = Decimal(unit_costs[item.pk]).quantize(CENT)
        if cost < 0:
            _fail("unit_costs", "Costs cannot be negative.")
        PurchaseItem.objects.create(purchase=po, medicine=item.medicine, quantity_ordered=item.quantity,
                                    unit_cost=cost, line_total=(cost * item.quantity).quantize(CENT))
    req.status, req.purchase_order = PurchaseRequisition.ORDERED, po
    req.save(update_fields=["status", "purchase_order"])
    return po


@transaction.atomic
def accept_quotation(quotation, user=None):
    quote = SupplierQuotation.objects.select_for_update().select_related("supplier").get(pk=quotation.pk)
    if quote.status != SupplierQuotation.RECEIVED:
        _fail("status", "This quotation has already been decided.")
    if quote.valid_until and quote.valid_until < hospital_today():
        _fail("valid_until", f"This quotation expired on {quote.valid_until}.")
    costs = {line.requisition_item_id: line.unit_cost for line in quote.items.all()}
    po = order_requisition(quote.requisition, quote.supplier, costs, user=user)
    quote.status = SupplierQuotation.ACCEPTED
    quote.save(update_fields=["status"])
    (SupplierQuotation.objects.filter(requisition_id=quote.requisition_id, status=SupplierQuotation.RECEIVED)
     .exclude(pk=quote.pk).update(status=SupplierQuotation.REJECTED))
    return po


# Purchase orders

@transaction.atomic
def cancel_purchase(purchase, user, reason):
    po = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
    if po.status == PurchaseOrder.STATUS_CANCELLED:
        _fail("status", "This purchase order is already cancelled.")
    if po.items.filter(quantity_received__gt=0).exists():
        _fail("status", "Goods have been received on this order; return them to the supplier instead.")
    if not (reason or "").strip():
        _fail("reason", "A cancellation reason is required.")
    po.status, po.cancelled_at, po.cancelled_by = PurchaseOrder.STATUS_CANCELLED, timezone.now(), _user(user)
    po.cancel_reason = reason.strip()[:255]
    po.save(update_fields=["status", "cancelled_at", "cancelled_by", "cancel_reason"])
    # Its requisition can be ordered again, from another supplier if need be.
    PurchaseRequisition.objects.filter(purchase_order=po).update(status=PurchaseRequisition.APPROVED, purchase_order=None)
    return po


# Issue to departments

@transaction.atomic
def issue_stock(hospital, department, medicine, quantity, user=None, received_by_name="", note="", idempotency_key=""):
    if idempotency_key:
        existing = StockIssue.objects.filter(hospital=hospital, idempotency_key=idempotency_key).first()
        if existing:
            return existing, False
    if department.hospital_id != hospital.pk or medicine.hospital_id != hospital.pk:
        _fail("department", "The department and the stock must belong to this hospital.")
    if medicine.expiry_date and medicine.expiry_date < hospital_today():
        _fail("medicine", f"This batch expired on {medicine.expiry_date}; it cannot be issued.")
    if quantity < 1:
        _fail("quantity", "Quantity must be at least 1.")
    try:
        with transaction.atomic():
            issue = StockIssue.objects.create(hospital=hospital, department=department, medicine=medicine,
                                              quantity=quantity, received_by_name=(received_by_name or "")[:150],
                                              note=(note or "")[:255], idempotency_key=idempotency_key or "",
                                              issued_by=_user(user))
    except IntegrityError:
        return StockIssue.objects.get(hospital=hospital, idempotency_key=idempotency_key), False
    _take_stock(medicine, quantity, f"Issued to {department.name}", f"ISS-{issue.pk}")
    return issue, True


# Returns to suppliers and consignment settlement (I4)

def _received_left(item):
    """Quantity of a receipt line not yet returned or (consignment) settled."""
    returned = item.returns.aggregate(total=Sum("quantity"))["total"] or 0
    settled = item.settlements.aggregate(total=Sum("quantity"))["total"] or 0
    return item.quantity_received - returned - settled


def _locked_receipt_item(receipt_item):
    # of=("self",): PostgreSQL cannot lock the nullable side of the outer join to the order.
    return (GoodsReceiptItem.objects.select_for_update(of=("self",))
            .select_related("medicine", "goods_receipt__purchase").get(pk=receipt_item.pk))


@transaction.atomic
def return_to_supplier(receipt_item, quantity, reason, user=None):
    item = _locked_receipt_item(receipt_item)
    if not (reason or "").strip():
        _fail("reason", "A return reason is required.")
    left = _received_left(item)
    if quantity < 1 or quantity > left:
        _fail("quantity", f"Between 1 and {left} of this receipt can be returned.")
    returned = SupplierReturn.objects.create(
        hospital_id=item.goods_receipt.hospital_id, receipt_item=item, quantity=quantity, reason=reason.strip()[:255],
        credit_amount=(item.unit_cost * quantity).quantize(CENT), returned_by=_user(user),
    )
    _take_stock(item.medicine, quantity, "Returned to supplier", f"SRET-{returned.pk} {item.goods_receipt.reference}")
    return returned


@transaction.atomic
def settle_consignment(receipt_item, quantity, user=None, reference=""):
    item = _locked_receipt_item(receipt_item)
    purchase = item.goods_receipt.purchase
    if not (purchase and purchase.is_consignment):
        _fail("receipt_item", "Only stock received on a consignment order is settled.")
    left = _received_left(item)
    if quantity < 1 or quantity > left:
        _fail("quantity", f"Between 1 and {left} of this consignment can be settled.")
    return ConsignmentSettlement.objects.create(
        hospital_id=item.goods_receipt.hospital_id, receipt_item=item, quantity=quantity,
        amount=(item.unit_cost * quantity).quantize(CENT), reference=(reference or "")[:100], settled_by=_user(user),
    )
