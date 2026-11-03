"""
List UHIDs used more than once within one hospital (ignoring case). Read
only: run it before adding a (hospital, uhid) unique constraint, and settle
each group by hand. Prints ids only, never patient names.

    python manage.py report_duplicate_uhids
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower

from patients.models import PatientHospital


class Command(BaseCommand):
    help = "Report UHIDs repeated within a hospital (read only)."

    def handle(self, *args, **options):
        groups = (
            PatientHospital.objects.annotate(uhid_key=Lower("uhid"))
            .values("hospital_id", "uhid_key")
            .annotate(rows=Count("id"))
            .filter(rows__gt=1)
            .order_by("hospital_id", "uhid_key")
        )
        if not groups:
            self.stdout.write("No duplicate UHIDs.")
            return
        for group in groups:
            rows = PatientHospital.objects.filter(
                hospital_id=group["hospital_id"], uhid__iexact=group["uhid_key"]
            ).order_by("id")
            listed = ", ".join(f"row {row.id} (patient {row.patient_id})" for row in rows)
            self.stdout.write(f"hospital {group['hospital_id']}: UHID {group['uhid_key']!r} x{group['rows']}: {listed}")
        self.stdout.write(f"{len(groups)} duplicate UHID group(s). Nothing was changed.")
