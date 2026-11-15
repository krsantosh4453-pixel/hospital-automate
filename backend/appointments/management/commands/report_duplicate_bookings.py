"""
List active bookings that repeat a patient, doctor and slot, appointments
with more than one queue token (P1-04), and slots holding more active
bookings than their doctor's capacity (Decision G: shared slots made before
2026-11-09 are kept, with numbered places). Read only: run it before the
migrations that add those unique constraints, and settle each group by hand.
Prints ids only, never patient names.

    python manage.py report_duplicate_bookings
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, F

from appointments.models import Appointment
from encounters.models import QueueToken


class Command(BaseCommand):
    help = "Report duplicate active bookings, duplicate queue tokens and over-capacity slots (read only)."

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

        crowded = (
            Appointment.objects.filter(status__in=Appointment.ACTIVE_STATUSES)
            .values("doctor_id", "doctor__slot_capacity", "appointment_date", "appointment_time")
            .annotate(rows=Count("id"))
            .filter(rows__gt=F("doctor__slot_capacity"))
            .order_by("appointment_date", "appointment_time")
        )
        for slot in crowded:
            self.stdout.write(f"doctor {slot['doctor_id']}, {slot['appointment_date']} {slot['appointment_time']}: "
                              f"{slot['rows']} active booking(s), capacity {slot['doctor__slot_capacity']}")

        self.stdout.write(f"{len(slots)} duplicate booking group(s), {len(tokens)} duplicate token group(s), "
                          f"{len(crowded)} slot(s) over capacity. Nothing was changed.")
