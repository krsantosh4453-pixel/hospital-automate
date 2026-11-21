"""
B-2 / B-3: work that should be billed and is not.

Consultations are charged when the visit is completed and laboratory tests
when the result is verified (billing/charges.py). Work done while the
service had no price, or left on a bill that was later cancelled, has no live
charge. This lists it and, on request, charges it through the same capture
functions, so each service is still charged once only (keyed lines, locked
rows). Bed days are not swept: the final bill of a stay charges them.

The price is today's price-list entry, because the reason the work is
unbilled is usually that no price existed on the day.
"""

from datetime import timedelta

from django.db import transaction

from config.hospital_time import hospital_today

from .charges import capture_consultation, capture_lab_test, is_charged
from .models import ServicePrice
from .price_list import price_for

Category = ServicePrice.Category
MAX_DAYS_BACK = 90
DEFAULT_DAYS_BACK = 30


def since_day(value):
    """The first day swept: ``value`` (a date) or 30 days ago; never over 90 days back."""
    today = hospital_today()
    earliest = today - timedelta(days=MAX_DAYS_BACK)
    day = value or (today - timedelta(days=DEFAULT_DAYS_BACK))
    if day < earliest:
        raise ValueError(f"Look back at most {MAX_DAYS_BACK} days (from {earliest}).")
    if day > today:
        raise ValueError("The start day cannot be in the future.")
    return day


def _visits(hospital_id, since):
    from encounters.models import Visit

    return (Visit.objects.filter(hospital_id=hospital_id, status="Completed", visit_date__date__gte=since)
            .order_by("visit_date", "pk"))


def _lab_tests(hospital_id, since):
    from laboratory.models import LabTest

    return (LabTest.objects.filter(hospital_id=hospital_id, status__in=LabTest.DONE_STATUSES,
                                   verified_at__date__gte=since)
            .order_by("verified_at", "pk"))


def find_unbilled(hospital_id, since):
    """Rows of uncharged work, oldest first, each saying whether a price exists today."""
    rows = []
    for visit in _visits(hospital_id, since):
        if is_charged(f"visit:{visit.pk}:consultation"):
            continue
        price = price_for(hospital_id, Category.CONSULTATION, applies_to=visit.visit_type, doctor_id=visit.doctor_id)
        rows.append({"kind": "consultation", "id": visit.pk, "patient": visit.patient_id,
                     "service": visit.visit_type, "date": str(visit.visit_date.date()),
                     "priced": price is not None})
    for test in _lab_tests(hospital_id, since):
        if is_charged(f"labtest:{test.pk}"):
            continue
        price = price_for(hospital_id, Category.LABORATORY, applies_to=test.name)
        rows.append({"kind": "laboratory", "id": test.pk, "patient": test.patient_id, "service": test.name,
                     "date": str(test.verified_at.date()), "priced": price is not None})
    return rows


def charge_unbilled(hospital_id, since):
    """
    Charge every priced row of ``find_unbilled``; one transaction per service,
    so one failure never undoes the others. Returns (charged, still unpriced).
    """
    from laboratory.models import LabTest

    charged, unpriced = [], []
    for row in find_unbilled(hospital_id, since):
        if not row["priced"]:
            unpriced.append(row)
            continue
        with transaction.atomic():
            if row["kind"] == "consultation":
                item = capture_consultation(row["id"])
            else:
                test = LabTest.objects.select_for_update(of=("self",)).select_related("visit").get(pk=row["id"])
                item = capture_lab_test(test)
        if item is not None:
            charged.append({**row, "invoice": item.invoice.invoice_number, "amount": str(item.subtotal)})
    return charged, unpriced
