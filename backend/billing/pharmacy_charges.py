"""
F9: medicine dispensed against a prescription is billed on the patient's
invoice, in the same transaction as the dispensing.

* Each sale becomes one invoice line (InvoiceItem.pharmacy_sale is unique),
  so a sale is never charged twice.
* Lines go onto the prescription's open medicine bill (unpaid, no payments
  yet); once that bill has a payment or is cancelled, the next dispensing
  of the same prescription starts a new bill. Dispensing never records a
  payment: the bill stays Unpaid until money is taken at billing.
* A patient return lowers the line by the returned quantity. If the bill was
  already paid beyond its new total, the difference is refunded on the bill
  (reference RET-<n>), so total, payments and status stay consistent.

Callers hold the transaction; the invoice row is locked while it changes.
"""

from decimal import Decimal

from django.db import transaction

from .models import Invoice, InvoiceItem
from .services import ZERO, line_subtotal, money, net_paid, new_reference, recalculate, record_refund

MAX_DESCRIPTION = 200


def _description(sale):
    medicine = sale.medicine
    parts = [medicine.name]
    if medicine.batch:
        parts.append(f"batch {medicine.batch}")
    if sale.prescription_id:
        parts.append(f"RX-{sale.prescription_id:04d}")
    return " · ".join(parts)[:MAX_DESCRIPTION]


def _open_bill(prescription):
    """The prescription's medicine bill that can still take lines, locked; or None."""
    candidates = (Invoice.objects.select_for_update()
                  .filter(prescription=prescription, status=Invoice.Status.UNPAID)
                  .order_by("-created_at", "-pk"))
    for invoice in candidates:
        if not invoice.payments.exists():
            return invoice
    return None


def post_sales(prescription, sales):
    """Bill ``sales`` (of ``prescription``) on its open medicine bill, or a new one. Returns the invoice."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("post_sales() must run inside the dispensing transaction.")
    sales = [sale for sale in sales if not InvoiceItem.objects.filter(pharmacy_sale=sale).exists()]
    if not sales:
        return None
    invoice = _open_bill(prescription)
    if invoice is None:
        invoice = Invoice.objects.create(
            patient=prescription.patient,
            hospital=prescription.hospital,
            prescription=prescription,
            invoice_number=new_reference("INV"),
        )
    for sale in sales:
        InvoiceItem.objects.create(
            invoice=invoice,
            description=_description(sale),
            quantity=sale.quantity,
            unit_price=sale.unit_price,
            subtotal=line_subtotal(sale.quantity, sale.unit_price),
            tax_rate=sale.medicine.tax_rate,
            pharmacy_sale=sale,
        )
    return recalculate(invoice)


def _gross(invoice):
    total = ZERO
    for item in invoice.items.all():
        subtotal = line_subtotal(item.quantity, item.unit_price)
        total += subtotal + money(subtotal * Decimal(item.tax_rate or 0) / 100)
    return money(total)


def apply_return(sale_return, user=None):
    """
    Take a patient return off the bill of its sale. Returns a dict that says
    what changed ({"invoice", "refund", "discount_capped"}), or None when the
    sale was never billed or its bill is cancelled.
    """
    item = InvoiceItem.objects.filter(pharmacy_sale_id=sale_return.sale_id).first()
    if item is None:
        return None
    invoice = Invoice.objects.select_for_update().get(pk=item.invoice_id)
    if invoice.status == Invoice.Status.CANCELLED:
        return None
    item = InvoiceItem.objects.select_for_update().get(pk=item.pk)
    item.quantity = max(item.quantity - sale_return.quantity, 0)
    item.subtotal = line_subtotal(item.quantity, item.unit_price)
    item.save(update_fields=["quantity", "subtotal"])

    # A discount larger than what is left on the bill is cut down to it.
    gross = _gross(invoice)
    discount_capped = money(invoice.discount) > gross
    if discount_capped:
        invoice.discount = gross
        invoice.save(update_fields=["discount"])
    recalculate(invoice)

    refund = None
    over_paid = money(net_paid(invoice) - invoice.total)
    if over_paid > ZERO:
        refund, _ = record_refund(invoice, over_paid, f"Pharmacy return RET-{sale_return.pk}", user=user,
                                  idempotency_key=f"pharmacy-return-{sale_return.pk}")
    invoice.refresh_from_db()
    return {"invoice": invoice, "refund": refund, "discount_capped": discount_capped}


def bill_summary(invoice):
    if invoice is None:
        return None
    return {
        "id": invoice.pk,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "total": str(money(invoice.total)),
        "balance_due": str(money(invoice.balance_due)),
    }
