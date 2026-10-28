"""
Discharge readiness (E7) and the final bill of an inpatient stay (E12, H8).

A discharge is completed only when the checklist is ticked, a doctor has
finalized the discharge summary and the final bill is fully paid.
"""

import math
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

CHECKLIST = [
    ("medications_reconciled", "Medications reconciled"),
    ("patient_counselled", "Patient and family counselled"),
    ("follow_up_arranged", "Follow-up arranged"),
    ("documents_handed_over", "Documents handed over"),
]

SECONDS_PER_DAY = 24 * 60 * 60


def billable_days(admission, until=None):
    """Started days in hospital, at least one."""
    end = until or admission.discharge_date or timezone.now()
    seconds = max(0, (end - admission.admission_date).total_seconds())
    return max(1, math.ceil(seconds / SECONDS_PER_DAY))


def final_invoice(admission):
    """The live (not cancelled) final bill of this stay, if any."""
    from billing.models import Invoice

    return admission.invoices.exclude(status=Invoice.Status.CANCELLED).order_by("-created_at").first()


def readiness(admission):
    """What still stands between this admission and a completed discharge."""
    from .models import DischargePlan, DischargeSummary

    plan = DischargePlan.objects.filter(admission=admission).first()
    summary = DischargeSummary.objects.filter(admission=admission).first()
    invoice = final_invoice(admission)

    checklist = [
        {"field": field, "label": label, "done": bool(plan and getattr(plan, field))}
        for field, label in CHECKLIST
    ]
    blockers = []
    if admission.status != "Discharge Initiated":
        blockers.append("Discharge has not been started.")
    if plan is None:
        blockers.append("No discharge plan has been written.")
    blockers += [f"Checklist: {item['label']}." for item in checklist if not item["done"]]
    if summary is None or not summary.finalized:
        blockers.append("A doctor must finalize the discharge summary.")
    if invoice is None:
        blockers.append("The final bill has not been created.")
    elif invoice.balance_due > 0:
        blockers.append(f"The final bill has ₹{invoice.balance_due} still due.")

    return {
        "admission": admission.pk,
        "ready": not blockers,
        "blockers": blockers,
        "checklist": checklist,
        "plan": plan.pk if plan else None,
        "summary_finalized": bool(summary and summary.finalized),
        "final_invoice": invoice_brief(invoice),
        "days": billable_days(admission),
    }


def invoice_brief(invoice):
    if invoice is None:
        return None
    return {
        "id": invoice.pk,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "total": str(invoice.total_amount),
        "balance_due": str(invoice.balance_due),
    }


def _decimal(value, name):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({name: "Enter an amount."})
    if not number.is_finite() or number < 0:
        raise ValidationError({name: "Enter an amount of zero or more."})
    return number


def create_final_bill(admission, daily_rate, extra_items=()):
    """
    One final invoice per stay: bed charges for the billable days plus any
    extra lines. A cancelled final bill may be replaced; a live one may not.
    """
    from billing.models import Invoice, InvoiceItem
    from billing.services import line_subtotal, new_reference, recalculate

    if admission.status not in ("Discharge Initiated", "Discharged"):
        raise ValidationError("Start the discharge before creating the final bill.")

    rate = _decimal(daily_rate, "daily_rate")
    days = billable_days(admission)
    lines = [(f"Bed charges: {days} day(s)", days, rate)]
    for index, item in enumerate(extra_items or []):
        description = str(item.get("description", "")).strip()[:200]
        if not description:
            raise ValidationError({"items": f"Line {index + 1} needs a description."})
        try:
            quantity = int(item.get("quantity") or 1)
        except (TypeError, ValueError):
            quantity = 0
        if quantity < 1:
            raise ValidationError({"items": f"Line {index + 1} needs a quantity of at least 1."})
        lines.append((description, quantity, _decimal(item.get("unit_price"), "items")))

    with transaction.atomic():
        # Lock the stay so two clerks cannot both create its final bill.
        type(admission).objects.select_for_update().filter(pk=admission.pk).first()
        if final_invoice(admission) is not None:
            raise ValidationError("This stay already has a final bill.")
        invoice = Invoice.objects.create(
            patient=admission.patient,
            hospital=admission.hospital,
            admission=admission,
            invoice_number=new_reference("INV"),
        )
        for description, quantity, unit_price in lines:
            InvoiceItem.objects.create(
                invoice=invoice,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=line_subtotal(quantity, unit_price),
            )
        recalculate(invoice)
    return invoice
