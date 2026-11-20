"""
BUG-07: the hospital price list (tariff). Finding the price of a service on
a day, adding a new price, and pricing an invoice line from the list.

Prices are never edited. A new price for the same service starts today or
later and closes the current one the day before, so a bill always shows the
price that applied when it was charged.
"""

from datetime import timedelta

from django.db import transaction
from rest_framework.exceptions import ValidationError

from config.hospital_time import hospital_today

from .models import ServicePrice

Category = ServicePrice.Category


def _same_service(hospital_id, category, applies_to, doctor_id):
    return ServicePrice.objects.filter(
        hospital_id=hospital_id, category=category, applies_to__iexact=(applies_to or "").strip(), doctor_id=doctor_id,
    )


def effective_on(queryset, day):
    """Rows of ``queryset`` in force on ``day``."""
    return queryset.filter(effective_from__lte=day).exclude(effective_to__lt=day)


def price_for(hospital_id, category, applies_to="", doctor_id=None, day=None):
    """
    The price row for a service on ``day`` (default: today), or None.

    Consultation: the doctor's own fee for the visit type, then the doctor's
    fee, then the hospital's fee for the visit type, then its default.
    Bed: the bed type's rate, then the default rate. Laboratory and the other
    categories: an exact match of ``applies_to`` (the test or service name).
    """
    day = day or hospital_today()
    rows = effective_on(ServicePrice.objects.filter(hospital_id=hospital_id, category=category), day)
    wanted = (applies_to or "").strip()
    if category == Category.CONSULTATION:
        candidates = [(doctor_id, wanted), (doctor_id, ""), (None, wanted), (None, "")] if doctor_id else [
            (None, wanted), (None, "")]
    elif category == Category.BED:
        candidates = [(None, wanted), (None, "")]
    else:
        candidates = [(None, wanted)] if wanted else []
    for doctor, name in candidates:
        row = rows.filter(doctor_id=doctor, applies_to__iexact=name).order_by("-effective_from", "-pk").first()
        if row is not None:
            return row
    return None


@transaction.atomic
def add_price(hospital, user=None, **fields):
    """
    Save a new price row. It must start today or later (bills already issued
    keep their price), after the current price of the same service starts;
    the current price then ends the day before.
    """
    from hospital.models import Hospital

    # The hospital row serialises new prices: with no row yet for a service,
    # locking its rows would lock nothing and two first prices could both land.
    Hospital.objects.select_for_update().filter(pk=hospital.pk).first()
    start = fields["effective_from"]
    if start < hospital_today():
        raise ValidationError({"effective_from": "A price cannot start in the past; bills already issued keep their price."})
    doctor = fields.get("doctor")
    same = _same_service(hospital.pk, fields["category"], fields.get("applies_to"), getattr(doctor, "pk", None))
    # Lock the service's rows so two new prices cannot both close the same one.
    current = list(same.select_for_update().order_by("-effective_from", "-pk"))
    latest = current[0] if current else None
    if latest is not None and start <= latest.effective_from:
        raise ValidationError({
            "effective_from": f"This service already has a price from {latest.effective_from}; "
                              "a new price must start after that.",
        })
    for row in current:
        if row.effective_to is None or row.effective_to >= start:
            ServicePrice.objects.filter(pk=row.pk).update(effective_to=start - timedelta(days=1))
    return ServicePrice.objects.create(hospital=hospital, created_by=_user(user), **fields)


def retire(price, end):
    """End a price on ``end`` (today or later). The row is otherwise unchanged."""
    if end < hospital_today() or end < price.effective_from:
        raise ValidationError({"effective_to": "Give today or a later date, on or after the price starts."})
    if price.effective_to is not None and price.effective_to < end:
        raise ValidationError({"effective_to": f"This price already ended on {price.effective_to}."})
    ServicePrice.objects.filter(pk=price.pk).update(effective_to=end)
    price.refresh_from_db()
    return price


def price_line(item, hospital_id):
    """
    Fill an invoice line (a dict of validated data) from its ``service_price``.
    The list decides the description, price and GST; a different price sent
    by the client is refused rather than silently replaced.
    """
    price = item.get("service_price")
    if price is None:
        return item
    if price.hospital_id != hospital_id:
        raise ValidationError({"service_price": "This price belongs to another hospital."})
    today = hospital_today()
    if price.effective_from > today or (price.effective_to is not None and price.effective_to < today):
        raise ValidationError({"service_price": f"{price.name} is not priced for today."})
    sent = item.get("unit_price")
    if sent is not None and sent != price.unit_price:
        raise ValidationError({"unit_price": f"{price.name} costs ₹{price.unit_price} on the price list."})
    return {
        **item,
        "description": (item.get("description") or "").strip() or price.name,
        "unit_price": price.unit_price,
        "tax_rate": price.tax_rate,
        "category": price.category,
    }


def _user(user):
    return user if getattr(user, "is_authenticated", False) else None
