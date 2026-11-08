"""
P1-05: GST invoice numbers, INV/26-27/000001: consecutive per hospital per
financial year (April to March), 16 characters at most as GST invoices need.

The number comes from InvoiceSequence through ``UPDATE ... SET last_value =
last_value + 1``, which locks the row until the caller's transaction ends, so
two counters never get the same number (as patients/uhid.py does for UHIDs).
The (hospital, invoice_number) unique constraint is the backstop. A
rolled-back bill leaves a gap; the gap is visible in the series and harmless.
Invoices created before this series keep their old numbers.
"""

from django.db import IntegrityError, transaction
from django.db.models import F

from config.hospital_time import hospital_today

from .models import InvoiceSequence

NUMBER_WIDTH = 6
FINANCIAL_YEAR_START_MONTH = 4


def financial_year(day):
    """The starting calendar year of the April-to-March year containing ``day``."""
    return day.year if day.month >= FINANCIAL_YEAR_START_MONTH else day.year - 1


def format_invoice_number(year, number):
    return f"INV/{year % 100:02d}-{(year + 1) % 100:02d}/{number:0{NUMBER_WIDTH}d}"


def _bump(hospital_id, year):
    return InvoiceSequence.objects.filter(hospital_id=hospital_id, financial_year=year).update(
        last_value=F("last_value") + 1)


@transaction.atomic
def next_invoice_number(hospital):
    """The next invoice number of ``hospital`` (a Hospital or its id) in the current financial year."""
    hospital_id = getattr(hospital, "pk", hospital)
    year = financial_year(hospital_today())
    if not _bump(hospital_id, year):
        try:
            with transaction.atomic():
                InvoiceSequence.objects.create(hospital_id=hospital_id, financial_year=year, last_value=1)
            return format_invoice_number(year, 1)
        except IntegrityError:
            # Another bill created this year's row first; continue from it.
            _bump(hospital_id, year)
    number = InvoiceSequence.objects.values_list("last_value", flat=True).get(
        hospital_id=hospital_id, financial_year=year)
    return format_invoice_number(year, number)
