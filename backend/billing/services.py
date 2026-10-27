"""
Billing rules. Every amount is computed here in Decimal from stored line
items; totals, tax, status and balances sent by a client are ignored.
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def line_subtotal(quantity, unit_price):
    return money(Decimal(quantity or 0) * Decimal(unit_price or 0))


def net_paid(invoice):
    """Payments minus refunds recorded against the invoice."""
    from .models import Payment

    # List views prefetch payments; use them instead of one query per invoice.
    prefetched = getattr(invoice, "_prefetched_objects_cache", {}).get("payments")
    if prefetched is not None:
        total = ZERO
        for payment in prefetched:
            total += payment.amount if payment.kind == Payment.Kind.PAYMENT else -payment.amount
        return money(total)

    rows = invoice.payments.values("kind").annotate(total=Sum("amount"))
    sums = {row["kind"]: row["total"] or ZERO for row in rows}
    return money(sums.get(Payment.Kind.PAYMENT, ZERO) - sums.get(Payment.Kind.REFUND, ZERO))


def _status_for(invoice, paid):
    from .models import Invoice

    if invoice.status == Invoice.Status.CANCELLED:
        return invoice.status
    if invoice.total <= ZERO or paid >= invoice.total:
        return Invoice.Status.PAID if paid > ZERO or invoice.total <= ZERO else Invoice.Status.UNPAID
    if paid > ZERO:
        return Invoice.Status.PARTIALLY_PAID
    return Invoice.Status.UNPAID


def recalculate(invoice, save=True):
    """Recompute subtotal-derived tax and total, then the payment status."""
    subtotal = ZERO
    tax = ZERO
    for item in invoice.items.all():
        item_subtotal = line_subtotal(item.quantity, item.unit_price)
        if item.subtotal != item_subtotal:
            item.subtotal = item_subtotal
            item.save(update_fields=["subtotal"])
        subtotal += item_subtotal
        tax += money(item_subtotal * Decimal(item.tax_rate or 0) / 100)
    discount = money(invoice.discount)
    if discount < ZERO:
        raise ValidationError({"discount": "Discount cannot be negative."})
    if discount > subtotal + tax:
        raise ValidationError({"discount": "Discount cannot exceed the bill amount."})
    invoice.tax = money(tax)
    invoice.total = money(subtotal + tax - discount)
    invoice.status = _status_for(invoice, net_paid(invoice))
    if save:
        invoice.save(update_fields=["tax", "total", "status"])
    return invoice


def new_reference(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def _locked(invoice):
    from .models import Invoice

    return Invoice.objects.select_for_update().get(pk=invoice.pk)


@transaction.atomic
def record_payment(invoice, amount, method="Cash", user=None, idempotency_key="", reference=""):
    """
    Record money received. The invoice row is locked so two concurrent
    payments cannot both pass the balance check. Re-sending the same
    idempotency key returns the original payment instead of charging twice.
    """
    from .models import Invoice, Payment

    invoice = _locked(invoice)
    if idempotency_key:
        existing = invoice.payments.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing, False
    amount = money(amount)
    if amount <= ZERO:
        raise ValidationError({"amount": "Amount must be greater than zero."})
    if invoice.status == Invoice.Status.CANCELLED:
        raise ValidationError({"invoice": "This invoice is cancelled."})
    balance = money(invoice.total - net_paid(invoice))
    if amount > balance:
        raise ValidationError({"amount": f"Amount exceeds the outstanding balance ({balance})."})
    payment = Payment.objects.create(
        invoice=invoice,
        kind=Payment.Kind.PAYMENT,
        amount=amount,
        payment_method=method or "Cash",
        receipt_number=new_reference("RCPT"),
        idempotency_key=idempotency_key or "",
        reference=reference or "",
        received_by=user if getattr(user, "is_authenticated", False) else None,
    )
    recalculate(invoice)
    return payment, True


@transaction.atomic
def record_refund(invoice, amount, reason, method="Cash", user=None):
    from .models import Payment

    invoice = _locked(invoice)
    amount = money(amount)
    if amount <= ZERO:
        raise ValidationError({"amount": "Amount must be greater than zero."})
    if not (reason or "").strip():
        raise ValidationError({"reason": "A refund reason is required."})
    paid = net_paid(invoice)
    if amount > paid:
        raise ValidationError({"amount": f"Refund exceeds the amount paid ({paid})."})
    refund = Payment.objects.create(
        invoice=invoice,
        kind=Payment.Kind.REFUND,
        amount=amount,
        payment_method=method or "Cash",
        receipt_number=new_reference("RFND"),
        reference=reason.strip()[:200],
        received_by=user if getattr(user, "is_authenticated", False) else None,
    )
    recalculate(invoice)
    return refund
