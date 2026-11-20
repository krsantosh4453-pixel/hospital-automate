"""
BUG-01: how a patient account becomes a patient of a hospital without staff
help, and the date-of-birth rules shared by every registration path.

A patient picks a hospital at sign-up or later from the patient app. Only an
active hospital that accepts self-registration can be picked (so a patient can
never attach themselves to an arbitrary hospital id), and joining reuses the
hospital's own UHID rules (``ensure_uhid``): one membership per patient and
hospital, never a second patient record.
"""

from datetime import date

from rest_framework.exceptions import ValidationError

from hospital.models import Hospital
from patients.uhid import ensure_uhid

OLDEST_AGE_YEARS = 130


def self_registration_hospitals():
    """Hospitals a patient may choose themselves, by name."""
    return Hospital.objects.filter(is_active=True, allow_patient_self_registration=True).order_by("name", "pk")


def hospital_for_self_registration(raw_id):
    """The hospital ``raw_id`` names, if a patient may join it; raises ValidationError otherwise."""
    try:
        hospital_id = int(str(raw_id).strip())
    except (TypeError, ValueError):
        raise ValidationError({"hospital": "Choose a hospital from the list."})
    hospital = self_registration_hospitals().filter(pk=hospital_id).first()
    if hospital is None:
        raise ValidationError({"hospital": "This hospital does not accept patient registration in the app."})
    return hospital


def join_hospital(patient, raw_hospital_id):
    """Register ``patient`` at the hospital (idempotent). Returns (membership, created)."""
    hospital = hospital_for_self_registration(raw_hospital_id)
    return ensure_uhid(patient, hospital)


def parse_date_of_birth(raw, today):
    """A date of birth from ``YYYY-MM-DD``; raises ValidationError when missing or impossible."""
    text = str(raw or "").strip()[:10]
    if not text:
        raise ValidationError({"date_of_birth": "Date of birth is required."})
    try:
        value = date.fromisoformat(text)
    except ValueError:
        raise ValidationError({"date_of_birth": "Date of birth is not valid."})
    if value > today:
        raise ValidationError({"date_of_birth": "Date of birth cannot be in the future."})
    if today.year - value.year > OLDEST_AGE_YEARS:
        raise ValidationError({"date_of_birth": "Check the year of birth."})
    return value
