"""
List active bookings that repeat a patient, doctor and slot, and appointments
with more than one queue token (P1-04). Read only: run it before the
migrations that add those unique constraints, and settle each group by hand.
Prints ids only, never patient names.

    python manage.py report_duplicate_bookings
"""

from django.core.management.base import BaseCommand
from django.db.models import Count

from appointments.models import Appointment
from encounters.models import QueueToken


class Command(BaseCommand):
    help = "Report duplicate active bookings and duplicate queue tokens (read only)."

    def handle(self, *args, **options):
        slots = (
            Appointment.objects.filter(status__in=Appointment.ACTIVE_STATUSES)
            .values("patient_id", "doctor_id", "appointment_date", "appointment_time")
            .annotate(rows=Count("id"))
            .filter(rows__gt=1)
            .order_by("appointment_date", "appointment_time")
        )
        for slot in slots:
            ids = list(Appointment.objects.filter(status__in=Appointment.ACTIVE_STATUSES, **{
                key: slot[key] for key in ("patient_id", "doctor_id", "appointment_date", "appointment_time")
            }).order_by("id").values_list("id", flat=True))
            self.stdout.write(f"patient {slot['patient_id']}, doctor {slot['doctor_id']}, "
                              f"{slot['appointment_date']} {slot['appointment_time']}: appointments {ids}")

        tokens = (
            QueueToken.objects.exclude(appointment__isnull=True)
            .values("appointment_id").annotate(rows=Count("id")).filter(rows__gt=1).order_by("appointment_id")
        )
        for group in tokens:
            ids = list(QueueToken.objects.filter(appointment_id=group["appointment_id"])
                       .order_by("id").values_list("id", flat=True))
            self.stdout.write(f"appointment {group['appointment_id']}: queue tokens {ids}")

        self.stdout.write(f"{len(slots)} duplicate booking group(s), {len(tokens)} duplicate token group(s). "
                          "Nothing was changed.")
