"""
F1: automatic UHIDs in the form PREFIX-YYYY-000001, numbered per hospital
per year (hospital calendar).

The number comes from UhidSequence through ``UPDATE ... SET last_value =
last_value + 1``. That UPDATE locks the row until the caller's transaction
ends, so concurrent registrations queue up instead of reading the same
value. The (hospital, lower(uhid)) unique constraint on PatientHospital is
the backstop. A rolled-back registration leaves a gap in the numbers; that
is expected and harmless.
"""

import re

from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from config.hospital_time import hospital_today

from .models import PatientHospital, UhidSequence

MAX_PREFIX_LENGTH = 10
NUMBER_WIDTH = 6
# Numbers already taken by hand-entered UHIDs are skipped, this many at most.
MAX_SKIPPED_NUMBERS = 50
_NOT_PREFIX_CHARACTERS = re.compile(r"[^A-Z0-9]")


def clean_prefix(value):
    return _NOT_PREFIX_CHARACTERS.sub("", str(value or "").upper())[:MAX_PREFIX_LENGTH]


def prefix_for(hospital):
    """The hospital's UHID prefix, else its code, else H<id>."""
    return clean_prefix(hospital.uhid_prefix) or clean_prefix(hospital.code) or f"H{hospital.pk}"


def format_uhid(prefix, year, number):
    return f"{prefix}-{year}-{number:0{NUMBER_WIDTH}d}"


def _bump(hospital, year):
    return UhidSequence.objects.filter(hospital=hospital, year=year).update(last_value=F("last_value") + 1)


def _next_number(hospital, year):
    if not _bump(hospital, year):
        try:
            with transaction.atomic():
                UhidSequence.objects.create(hospital=hospital, year=year, last_value=1)
            return 1
        except IntegrityError:
            # Another registration created this year's row first; continue from it.
            _bump(hospital, year)
    return UhidSequence.objects.values_list("last_value", flat=True).get(hospital=hospital, year=year)


def next_uhid(hospital):
    """
    The next free UHID of ``hospital``. Call it inside the transaction that
    saves the UHID: the sequence row stays locked until that transaction ends.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("next_uhid() must run inside a transaction.")
    prefix = prefix_for(hospital)
    year = hospital_today().year
    for _ in range(MAX_SKIPPED_NUMBERS):
        uhid = format_uhid(prefix, year, _next_number(hospital, year))
        if not PatientHospital.objects.filter(hospital=hospital, uhid__iexact=uhid).exists():
            return uhid
    raise ValidationError({"uhid": "Could not issue a UHID: too many numbers are already in use. Contact an administrator."})


@transaction.atomic
def ensure_uhid(patient, hospital):
    """
    The patient's membership at ``hospital``, with a UHID. Creates the
    membership, or fills in a blank UHID, when needed; never changes an
    existing UHID or reactivates a membership. Returns (membership, issued).
    """
    membership = PatientHospital.objects.select_for_update().filter(patient=patient, hospital=hospital).first()
    if membership is not None and membership.uhid:
        return membership, False
    uhid = next_uhid(hospital)
    if membership is None:
        try:
            with transaction.atomic():
                return PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=uhid), True
        except IntegrityError:
            # Registered at this hospital at the same moment by another request.
            membership = PatientHospital.objects.select_for_update().get(patient=patient, hospital=hospital)
            if membership.uhid:
                return membership, False
    membership.uhid = uhid
    membership.save(update_fields=["uhid"])
    return membership, True
