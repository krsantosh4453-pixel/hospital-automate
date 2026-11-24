"""
B-2 / B-3: work that should be billed and is not.

Consultations are charged when the visit is completed and laboratory tests
when the result is verified (billing/charges.py). Only two kinds of work are
listed here, because only they are known to be unbilled:

* "unpriced": the capture ran and found no price, and audited it as
  ``billing.charge.unpriced``. Work done before automatic charging existed
  has no such record, so a hospital's earlier hand-made bills are never
  billed a second time.
* "cancelled": the charge was on a bill an Admin or Hospital Manager
  cancelled. It is shown with the bill and the reason, and is charged only
  when someone picks it, never by the bulk sweep, since the cancellation may
  have been deliberate.

Charging goes through the same capture functions, so each service is still
charged once only (keyed lines, locked rows). Listing never writes. Bed days
are not swept: the final bill of a stay charges them. The price is today's.
"""

import json
from datetime import timedelta

from django.db import transaction

from config.hospital_time import hospital_today

from .charges import capture_consultation, capture_imaging_study, capture_lab_test, imaging_price
from .models import Invoice, InvoiceItem, ServicePrice
from .price_list import price_for

Category = ServicePrice.Category
MAX_DAYS_BACK = 90
DEFAULT_DAYS_BACK = 30
UNPRICED = "unpriced"
CANCELLED = "cancelled"
VOID_MARK = "#void-"


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


def _key(kind, pk):
    if kind == "consultation":
        return f"visit:{pk}:consultation"
    return f"imaging:{pk}" if kind == "imaging" else f"labtest:{pk}"


def _parse_key(key):
    """("consultation", 12) for "visit:12:consultation#void-3", ("laboratory", 5) for "labtest:5…"."""
    base = key.split(VOID_MARK, 1)[0]
    parts = base.split(":")
    if parts[0] == "visit" and len(parts) == 3 and parts[2] == "consultation" and parts[1].isdigit():
        return "consultation", int(parts[1])
    if parts[0] == "labtest" and len(parts) == 2 and parts[1].isdigit():
        return "laboratory", int(parts[1])
    if parts[0] == "imaging" and len(parts) == 2 and parts[1].isdigit():
        return "imaging", int(parts[1])
    return None


def _cancel_reasons(invoice_ids):
    from audit.models import AuditLog

    reasons = {}
    for row in (AuditLog.objects.filter(action="billing.invoice.cancel", model_name="billing.Invoice",
                                        object_id__in=[str(i) for i in invoice_ids])
                .order_by("created_at").values("object_id", "details")):
        try:
            reasons[int(row["object_id"])] = json.loads(row["details"] or "{}").get("reason", "")
        except (ValueError, AttributeError):
            reasons[int(row["object_id"])] = ""
    return reasons


def _candidates(hospital_id, since):
    """{(kind, id): {"source", …}} of work known to be unbilled, newest source wins."""
    from audit.models import AuditLog

    found = {}
    model_kind = {"encounters.Visit": "consultation", "laboratory.LabTest": "laboratory",
                  "laboratory.ImagingStudy": "imaging"}
    for row in AuditLog.objects.filter(hospital_id=hospital_id, action="billing.charge.unpriced",
                                       model_name__in=list(model_kind), created_at__date__gte=since,
                                       ).values("model_name", "object_id"):
        if row["object_id"].isdigit():
            found[(model_kind[row["model_name"]], int(row["object_id"]))] = {"source": UNPRICED}

    voided = (InvoiceItem.objects.filter(invoice__hospital_id=hospital_id, invoice__status=Invoice.Status.CANCELLED,
                                         invoice__created_at__date__gte=since, charge_key__contains=VOID_MARK)
              .values("charge_key", "invoice_id", "invoice__invoice_number"))
    voided = list(voided)
    reasons = _cancel_reasons({row["invoice_id"] for row in voided})
    for row in voided:
        parsed = _parse_key(row["charge_key"])
        if parsed is not None:
            found[parsed] = {"source": CANCELLED, "cancelled_invoice": row["invoice__invoice_number"],
                             "cancel_reason": reasons.get(row["invoice_id"], "")}
    return found


def _live_keys(keys):
    """Keys already charged on a bill that is not cancelled (one query, no writes)."""
    return set(InvoiceItem.objects.filter(charge_key__in=list(keys))
               .exclude(invoice__status=Invoice.Status.CANCELLED).values_list("charge_key", flat=True))


def find_unbilled(hospital_id, since):
    """Rows of uncharged work, oldest first, each saying where it came from and whether it is priced today."""
    from encounters.models import Visit
    from laboratory.models import ImagingStudy, LabTest

    candidates = _candidates(hospital_id, since)
    live = _live_keys(_key(kind, pk) for kind, pk in candidates)
    open_ = {k: v for k, v in candidates.items() if _key(*k) not in live}
    visit_ids = [pk for kind, pk in open_ if kind == "consultation"]
    test_ids = [pk for kind, pk in open_ if kind == "laboratory"]
    visits = Visit.objects.filter(hospital_id=hospital_id, status="Completed").in_bulk(visit_ids)
    tests = LabTest.objects.filter(hospital_id=hospital_id, status__in=LabTest.DONE_STATUSES).in_bulk(test_ids)
    studies = ImagingStudy.objects.filter(hospital_id=hospital_id, status=ImagingStudy.Status.REPORTED).in_bulk(
        [pk for kind, pk in open_ if kind == "imaging"])

    prices = {}

    def priced(*args):
        if args not in prices:
            prices[args] = price_for(hospital_id, *args[:1], applies_to=args[1],
                                     **({"doctor_id": args[2]} if len(args) > 2 else {})) is not None
        return prices[args]

    rows = []
    for (kind, pk), source in open_.items():
        if kind == "consultation" and pk in visits:
            visit = visits[pk]
            rows.append({"kind": kind, "id": pk, "patient": visit.patient_id, "service": visit.visit_type,
                         "date": str(visit.visit_date.date()),
                         "priced": priced(Category.CONSULTATION, visit.visit_type, visit.doctor_id), **source})
        elif kind == "laboratory" and pk in tests:
            test = tests[pk]
            rows.append({"kind": kind, "id": pk, "patient": test.patient_id, "service": test.name,
                         "date": str((test.verified_at or test.released_at).date()) if (test.verified_at or test.released_at) else "",
                         "priced": priced(Category.LABORATORY, test.name), **source})
        elif kind == "imaging" and pk in studies:
            study = studies[pk]
            rows.append({"kind": kind, "id": pk, "patient": study.patient_id,
                         "service": f"{study.modality} {study.body_part}".strip(),
                         "date": str(study.reported_at.date()) if study.reported_at else "",
                         "priced": imaging_price(study) is not None, **source})
    return sorted(rows, key=lambda r: (r["date"], r["kind"], r["id"]))


def charge_unbilled(hospital_id, since, selected=None):
    """
    Charge unbilled work; one transaction per service, so one failure never
    undoes the others. Without ``selected`` only priced "unpriced" work is
    charged; with ``selected`` (a set of (kind, id)) exactly those rows,
    including ones from a cancelled bill. Returns (charged, not charged).
    """
    from laboratory.models import ImagingStudy, LabTest

    charged, left = [], []
    for row in find_unbilled(hospital_id, since):
        wanted = (row["kind"], row["id"]) in selected if selected is not None else row["source"] == UNPRICED
        if not wanted or not row["priced"]:
            left.append(row)
            continue
        with transaction.atomic():
            if row["kind"] == "consultation":
                item = capture_consultation(row["id"])
            elif row["kind"] == "imaging":
                study = ImagingStudy.objects.select_for_update(of=("self",)).select_related("visit").get(pk=row["id"])
                item = capture_imaging_study(study)
            else:
                test = LabTest.objects.select_for_update(of=("self",)).select_related("visit").get(pk=row["id"])
                item = capture_lab_test(test)
        if item is not None:
            charged.append({**row, "invoice": item.invoice.invoice_number, "amount": str(item.subtotal)})
    return charged, left
