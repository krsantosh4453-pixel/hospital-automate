"""
Discharge readiness (E7) and the final bill of an inpatient stay (E12, H8).

A discharge is completed only when the checklist is ticked, a doctor has
finalized the discharge summary, the final bill exists, is not an
unexplained ₹0, and every bill of the stay is fully paid.

BUG-07: bed charges come from the price list, never from a rate typed at
the counter. Charges captured during the stay (consultations, laboratory)
collect on its running bill; creating the final bill adds the bed days to
that bill and marks it final.
"""

import math
from collections import OrderedDict
from datetime import timedelta
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
ZERO = Decimal("0.00")
INPATIENT = "inpatient"


def billable_days(admission, until=None):
    """Started days in hospital, at least one."""
    end = until or admission.discharge_date or timezone.now()
    seconds = max(0, (end - admission.admission_date).total_seconds())
    return max(1, math.ceil(seconds / SECONDS_PER_DAY))


def final_invoice(admission):
    """The live (not cancelled) final bill of this stay, if any."""
    from billing.models import Invoice

    return (admission.invoices.filter(is_final=True).exclude(status=Invoice.Status.CANCELLED)
            .order_by("-created_at", "-pk").first())


def stay_invoices(admission):
    """Every live bill of this stay: the running bill, the final bill and any later bill."""
    from billing.models import Invoice

    return admission.invoices.exclude(status=Invoice.Status.CANCELLED).order_by("created_at", "pk")


def is_waived(invoice):
    from billing.models import InvoiceWaiver

    return InvoiceWaiver.objects.filter(invoice=invoice).exists()


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
    blockers += _billing_blockers(admission, invoice)

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


def _billing_blockers(admission, invoice):
    if invoice is None:
        return ["The final bill has not been created."]
    blockers = []
    if invoice.total <= ZERO and not is_waived(invoice):
        blockers.append("The final bill comes to ₹0 without an approved waiver.")
    for bill in stay_invoices(admission):
        due = bill.balance_due
        if due <= ZERO:
            continue
        if bill.pk == invoice.pk:
            blockers.append(f"The final bill has ₹{due} still due.")
        else:
            blockers.append(f"Bill {bill.invoice_number} of this stay has ₹{due} still due.")
    return blockers


def invoice_brief(invoice):
    if invoice is None:
        return None
    return {
        "id": invoice.pk,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "total": str(invoice.total_amount),
        "balance_due": str(invoice.balance_due),
        "is_final": invoice.is_final,
        "waived": is_waived(invoice),
    }


def _decimal(value, name):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({name: "Enter an amount."})
    if not number.is_finite() or number < 0:
        raise ValidationError({name: "Enter an amount of zero or more."})
    return number


def _hospital_date(moment):
    """The hospital's calendar date of ``moment`` (settings run in UTC; prices follow the hospital)."""
    from zoneinfo import ZoneInfo

    from django.conf import settings

    return moment.astimezone(ZoneInfo(getattr(settings, "HOSPITAL_TIME_ZONE", "Asia/Kolkata"))).date()


def _bed_at(allocations, moment):
    """The bed occupied at ``moment``. Before the first bed, the first bed; after the last, the last."""
    for allocation in allocations:
        if allocation.allocated_at <= moment and (allocation.released_at is None or moment < allocation.released_at):
            return allocation.bed
    later = [allocation for allocation in allocations if allocation.allocated_at > moment]
    if later:
        return later[0].bed
    return allocations[-1].bed if allocations else None


def _bed_price(hospital_id, bed_type, day, cache):
    """The bed rate on ``day``; a day before the bed type had any price takes today's price."""
    from billing.models import ServicePrice
    from billing.price_list import price_for

    key = (bed_type.lower(), day)
    if key not in cache:
        cache[key] = (price_for(hospital_id, ServicePrice.Category.BED, applies_to=bed_type, day=day)
                      or price_for(hospital_id, ServicePrice.Category.BED, applies_to=bed_type))
    return cache[key]


def bed_day_lines(admission, until=None):
    """
    BUG-07: the bed charges of a stay. Each started day (``billable_days``) is
    charged at the price-list rate of the bed occupied at the start of that
    day, as priced on that day. Returns ``[{"price", "bed_type", "days"}]``
    in stay order, one entry per price row. Raises when a bed type has no price.
    """
    allocations = list(admission.bed_allocations.select_related("bed").order_by("allocated_at", "pk"))
    lines, cache, missing = OrderedDict(), {}, set()
    for index in range(billable_days(admission, until)):
        moment = admission.admission_date + timedelta(days=index)
        bed = _bed_at(allocations, moment)
        bed_type = (bed.bed_type if bed else "").strip()
        price = _bed_price(admission.hospital_id, bed_type, _hospital_date(moment), cache)
        if price is None:
            missing.add(bed_type or "general (default)")
            continue
        line = lines.setdefault(price.pk, {"price": price, "bed_type": bed_type, "days": 0})
        line["days"] += 1
    if missing:
        raise ValidationError({
            "daily_rate": f"The price list has no bed charge for: {', '.join(sorted(missing))}. "
                          "An Admin or Hospital Manager must add it before the final bill is created.",
        })
    return list(lines.values())


def bed_line_description(line):
    price = line["price"]
    kind = line["bed_type"] or "general"
    return f"Bed charges ({kind}, ₹{price.unit_price}/day): {line['days']} day(s)"


def bed_charge_preview(admission):
    """What the bed days of this stay come to now, for the billing screens."""
    try:
        lines = bed_day_lines(admission)
    except ValidationError as error:
        detail = error.detail.get("daily_rate") if isinstance(error.detail, dict) else error.detail
        return {"lines": [], "total": None, "error": str(detail[0] if isinstance(detail, list) else detail)}
    rows = [
        {
            "description": bed_line_description(line),
            "days": line["days"],
            "unit_price": str(line["price"].unit_price),
            "tax_rate": str(line["price"].tax_rate),
            "amount": str((line["price"].unit_price * line["days"]).quantize(Decimal("0.01"))),
        }
        for line in lines
    ]
    return {"lines": rows, "total": str(sum((Decimal(row["amount"]) for row in rows), ZERO)), "error": ""}


def _extra_lines(extra_items):
    lines = []
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
        unit_price = _decimal(item.get("unit_price"), "items")
        if unit_price <= 0:
            raise ValidationError({
                "items": f"Line {index + 1} needs a price above ₹0. Free care is recorded as a waiver.",
            })
        lines.append((description, quantity, unit_price))
    return lines


def _check_rate(lines, daily_rate):
    """An old client may still send ``daily_rate``; it must agree with the price list."""
    if daily_rate in (None, ""):
        return
    rate = _decimal(daily_rate, "daily_rate")
    listed = sorted({line["price"].unit_price for line in lines})
    if any(price != rate for price in listed):
        shown = ", ".join(f"₹{price}" for price in listed)
        raise ValidationError({
            "daily_rate": f"Bed charges come from the price list ({shown} per day). Leave the rate out.",
        })


def create_final_bill(admission, daily_rate=None, extra_items=()):
    """
    One final bill per stay: the running bill of the stay (or a new one) plus
    the bed days from the price list and any extra lines. A cancelled final
    bill may be replaced; a live one may not. A bill that comes to ₹0 is refused.
    """
    from billing.charges import bill_for, post_charge
    from billing.models import InvoiceItem
    from billing.services import line_subtotal, recalculate

    if admission.status not in ("Discharge Initiated", "Discharged"):
        raise ValidationError("Start the discharge before creating the final bill.")
    extras = _extra_lines(extra_items)

    with transaction.atomic():
        # Lock the stay so two clerks cannot both create its final bill.
        type(admission).objects.select_for_update().filter(pk=admission.pk).first()
        if final_invoice(admission) is not None:
            raise ValidationError("This stay already has a final bill.")
        beds = bed_day_lines(admission)
        _check_rate(beds, daily_rate)
        invoice = bill_for(admission.patient_id, admission.hospital_id, admission=admission)
        for line in beds:
            post_charge(invoice, f"admission:{admission.pk}:bed:{line['price'].pk}", line["price"],
                        bed_line_description(line), quantity=line["days"])
        for description, quantity, unit_price in extras:
            InvoiceItem.objects.create(
                invoice=invoice, description=description, quantity=quantity, unit_price=unit_price,
                subtotal=line_subtotal(quantity, unit_price), category=INPATIENT,
            )
        invoice.is_final = True
        invoice.save(update_fields=["is_final"])
        recalculate(invoice)
        if invoice.total <= ZERO:
            raise ValidationError("The final bill comes to ₹0. Check the charges; only an approved waiver may make it free.")
    return invoice
