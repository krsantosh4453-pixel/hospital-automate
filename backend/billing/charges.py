"""
BUG-07: charges captured from the work itself, priced from the price list.

* A consultation is charged when its visit is Completed.
* A laboratory investigation is charged when its result is verified, so a
  test that was ordered but never performed is never billed.
* Bed days are charged on the final bill of a stay (ipd/discharge.py).

Every charge has a key naming the service ("visit:12:consultation",
"labtest:5"). The key is unique on bill lines and the service row is locked
by the caller, so a retried or concurrent request never charges twice.

A charge goes on an open bill (Unpaid, no payments yet): the running bill of
the patient's stay while they are admitted, else the bill of the visit. When
there is none, a new bill is started. A service with no price on the list is
not billed: it is logged and audited as "billing.charge.unpriced" so billing
can add the price and charge it by hand; the clinical work is never blocked.

Callers hold the transaction.
"""

import logging

from django.db import IntegrityError, transaction

from audit.services import record_audit

from .models import Invoice, InvoiceItem, ServicePrice
from .numbering import next_invoice_number
from .price_list import price_for
from .services import line_subtotal, recalculate

logger = logging.getLogger(__name__)

Category = ServicePrice.Category
ACTIVE_STAY = ("Admitted", "Discharge Initiated")
VISIT_COMPLETED = "Completed"
MAX_DESCRIPTION = 200
MAX_KEY = 120


def _require_transaction():
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("Charges must be captured inside the transaction of the work they bill.")


def active_admission(patient_id, hospital_id):
    from ipd.models import Admission

    return (Admission.objects.filter(patient_id=patient_id, hospital_id=hospital_id, status__in=ACTIVE_STAY)
            .order_by("-admission_date", "-pk").first())


def _open(queryset):
    """The newest bill of ``queryset`` that can still take lines, locked; or None."""
    for invoice in queryset.select_for_update().filter(status=Invoice.Status.UNPAID).order_by("-created_at", "-pk"):
        if not invoice.payments.exists():
            return invoice
    return None


def bill_for(patient_id, hospital_id, visit=None, admission=None):
    """The open bill a charge goes on (locked), or a new one."""
    from patients.models import Patient

    # The patient row serialises bill creation: two charges at the same moment
    # with no open bill would otherwise each start one.
    Patient.objects.select_for_update().filter(pk=patient_id).first()
    admission = admission or active_admission(patient_id, hospital_id)
    if admission is not None:
        invoice = _open(Invoice.objects.filter(admission=admission, is_final=False))
        fields = {"admission": admission}
    elif visit is not None:
        invoice = _open(Invoice.objects.filter(visit=visit, admission__isnull=True, prescription__isnull=True))
        fields = {"visit": visit}
    else:
        invoice, fields = None, {}
    if invoice is None:
        invoice = Invoice.objects.create(
            patient_id=patient_id, hospital_id=hospital_id,
            invoice_number=next_invoice_number(hospital_id), **fields,
        )
    return invoice


def _live_line(key):
    """
    The line already charging ``key`` on a bill that is not cancelled, or None.
    A cancelled bill still holding the key (cancelled outside the cancel
    action) gives it up here, so the service can be charged again.
    """
    for item in InvoiceItem.objects.select_related("invoice").filter(charge_key=key):
        if item.invoice.status != Invoice.Status.CANCELLED:
            return item
        release_charges(item.invoice)
    return None


def is_charged(key):
    return _live_line(key) is not None


def post_charge(invoice, key, price, description, quantity=1):
    """Put the line for ``key`` on ``invoice``. Returns ``(item, created)``."""
    existing = _live_line(key)
    if existing is not None:
        return existing, False
    try:
        with transaction.atomic():
            item = InvoiceItem.objects.create(
                invoice=invoice,
                description=description[:MAX_DESCRIPTION],
                quantity=quantity,
                unit_price=price.unit_price,
                subtotal=line_subtotal(quantity, price.unit_price),
                tax_rate=price.tax_rate,
                service_price=price,
                category=price.category,
                charge_key=key,
            )
    except IntegrityError:
        # Another request billed the same service a moment ago.
        return InvoiceItem.objects.get(charge_key=key), False
    recalculate(invoice)
    record_audit(None, "billing.charge.captured", item, hospital=invoice.hospital_id,
                 details={"charge_key": key, "invoice": invoice.invoice_number, "quantity": quantity,
                          "unit_price": str(price.unit_price), "price_code": price.code})
    return item, True


def _unpriced(obj, category, name):
    logger.warning("No %s price for %r at hospital %s; %s not billed.", category, name,
                   getattr(obj, "hospital_id", None), obj)
    record_audit(None, "billing.charge.unpriced", obj,
                 details={"category": category, "service": name, "note": "No price on the price list."})
    return None


def _doctor_label(name):
    name = (name or "").strip()
    return name if name.lower().startswith(("dr ", "dr.")) else f"Dr {name}"


def capture_consultation(visit_id):
    """Charge a completed consultation once. Returns the bill line, or None."""
    from encounters.models import Visit

    _require_transaction()
    # Lock the visit row only: PostgreSQL cannot lock the nullable side of a join.
    visit = Visit.objects.select_for_update(of=("self",)).select_related("doctor").get(pk=visit_id)
    key = f"visit:{visit.pk}:consultation"
    if visit.status != VISIT_COMPLETED or is_charged(key):
        return None
    price = price_for(visit.hospital_id, Category.CONSULTATION, applies_to=visit.visit_type, doctor_id=visit.doctor_id)
    if price is None:
        return _unpriced(visit, Category.CONSULTATION, visit.visit_type)
    doctor = _doctor_label(visit.doctor.name) if visit.doctor_id else ""
    description = " · ".join(part for part in (f"Consultation ({visit.visit_type})", doctor) if part)
    invoice = bill_for(visit.patient_id, visit.hospital_id, visit=visit)
    item, _ = post_charge(invoice, key, price, description)
    return item


def capture_lab_test(lab_test):
    """Charge a verified investigation once (the caller holds the test locked)."""
    _require_transaction()
    key = f"labtest:{lab_test.pk}"
    if is_charged(key):
        return None
    if lab_test.hospital_id is None:
        return _unpriced(lab_test, Category.LABORATORY, lab_test.name)
    price = price_for(lab_test.hospital_id, Category.LABORATORY, applies_to=lab_test.name)
    if price is None:
        return _unpriced(lab_test, Category.LABORATORY, lab_test.name)
    visit = lab_test.visit if lab_test.visit_id and lab_test.visit.patient_id == lab_test.patient_id else None
    invoice = bill_for(lab_test.patient_id, lab_test.hospital_id, visit=visit)
    item, _ = post_charge(invoice, key, price, f"Laboratory: {lab_test.name} (LAB-{lab_test.pk})")
    return item


def release_charges(invoice):
    """
    A cancelled bill no longer charges its services: its keys get a void
    suffix, so a replacement bill can charge them again. Lines are kept.
    """
    for item in invoice.items.exclude(charge_key=""):
        if "#void-" in item.charge_key:
            continue
        void_key = f"{item.charge_key}#void-{invoice.pk}"[:MAX_KEY]
        InvoiceItem.objects.filter(pk=item.pk).update(charge_key=void_key)
