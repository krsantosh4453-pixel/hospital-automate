"""
Prescription dispensing rules: partial dispensing (what is still owed per
line), same-salt brand substitution (F8) and patient returns (F5).
Callers hold a transaction; the rows that guard a decision are locked here.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from rest_framework import serializers

from config.hospital_time import hospital_today
from procurement.models import StockTransaction

from .models import Medicine, Sale, SaleReturn

PARTIALLY_DISPENSED = "Partially Dispensed"
NOT_SAME_SALT = (
    "{given} is not the same salt as the prescribed {prescribed}; "
    "ask the prescribing doctor to change the prescription."
)


CANCELLED = "Cancelled"
PENDING_VERIFICATION = "Pending Verification"
NOT_DISPENSABLE = {
    CANCELLED: "This prescription was cancelled; it cannot be dispensed.",
    PENDING_VERIFICATION: (
        "This paper prescription must be verified by a second pharmacist or an Admin before it is dispensed."
    ),
}


def check_dispensable(prescription):
    """Refuses a cancelled prescription or an unverified paper transcription (F13)."""
    reason = NOT_DISPENSABLE.get(prescription.status)
    if reason:
        raise serializers.ValidationError({"prescription": reason})


def dispensed_quantities(prescription):
    """Quantity already issued for each prescription item id."""
    rows = (Sale.objects.filter(prescription=prescription, prescription_item__isnull=False)
            .values("prescription_item").annotate(total=Sum("quantity")))
    return {row["prescription_item"]: row["total"] for row in rows}


def remaining_quantities(prescription, items):
    done = dispensed_quantities(prescription)
    return {pk: max(item.quantity - done.get(pk, 0), 0) for pk, item in items.items()}


def _salt(text):
    return " ".join(str(text or "").lower().split())


def prescribed_salt(hospital_id, prescribed_name):
    """The generic name stocked under the prescribed brand at this hospital, or ''."""
    generic = (Medicine.objects.filter(hospital_id=hospital_id, name__iexact=prescribed_name.strip())
               .exclude(generic_name="").values_list("generic_name", flat=True).first())
    return _salt(generic)


def substitution_for(item, medicine, reason, may_substitute):
    """
    '' when ``medicine`` is the prescribed one; the prescribed name when it is
    an allowed same-salt substitute. Refuses anything else: a different salt,
    an unknown prescribed salt, no reason, or a user who is not a pharmacist.
    """
    if medicine.name.strip().lower() == item.name.strip().lower():
        return ""
    if not may_substitute:
        raise serializers.ValidationError({"lines": "Only a pharmacist can give a substitute brand."})
    if not (reason or "").strip():
        raise serializers.ValidationError({"lines": f"Say why {medicine.name} is given instead of {item.name}."})
    wanted = prescribed_salt(medicine.hospital_id, item.name)
    if not wanted or wanted != _salt(medicine.generic_name):
        raise serializers.ValidationError({"lines": NOT_SAME_SALT.format(given=medicine.name, prescribed=item.name)})
    return item.name.strip()[:200]


@transaction.atomic
def record_return(sale, quantity, reason, restock, user=None):
    """Take back ``quantity`` of a sale; restock it only if fit and not expired."""
    sale = Sale.objects.select_for_update().select_related("medicine").get(pk=sale.pk)
    if not (reason or "").strip():
        raise serializers.ValidationError({"reason": "A return reason is required."})
    if quantity is None or int(quantity) < 1:
        raise serializers.ValidationError({"quantity": "Quantity must be at least 1."})
    quantity = int(quantity)
    already = sale.returns.aggregate(total=Sum("quantity"))["total"] or 0
    if quantity > sale.quantity - already:
        raise serializers.ValidationError(
            {"quantity": f"Only {sale.quantity - already} of this sale can still be returned."})
    medicine = sale.medicine
    if restock and medicine.expiry_date and medicine.expiry_date < hospital_today():
        raise serializers.ValidationError(
            {"restock": f"This batch expired on {medicine.expiry_date}; record the return as discarded."})
    returned = SaleReturn.objects.create(
        sale=sale, hospital_id=sale.hospital_id, quantity=quantity, restocked=bool(restock),
        reason=reason.strip()[:255], refund_amount=(Decimal(quantity) * sale.unit_price).quantize(Decimal("0.01")),
        returned_by=user if getattr(user, "is_authenticated", False) else None,
    )
    if restock:
        Medicine.objects.filter(pk=medicine.pk).update(quantity=F("quantity") + quantity)
        StockTransaction.objects.create(
            medicine=medicine, hospital_id=sale.hospital_id, transaction_type=StockTransaction.TYPE_IN,
            quantity=quantity, reason="Patient return", reference=f"RET-{returned.pk} SALE-{sale.pk}",
        )
    return returned
