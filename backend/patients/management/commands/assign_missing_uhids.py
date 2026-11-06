"""
F1: give a UHID to every patient registered at a hospital who has none
there: patients linked directly (Patient.hospital) with no membership row,
and membership rows whose UHID is blank. Existing UHIDs are never changed
and inactive memberships stay inactive.

Dry run by default; prints counts and ids only, never patient names.

    python manage.py assign_missing_uhids                # report
    python manage.py assign_missing_uhids --apply        # assign
    python manage.py assign_missing_uhids --apply --hospital 3
"""

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef, Q

from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from patients.uhid import ensure_uhid


def patients_missing_uhid(hospital):
    has_uhid = PatientHospital.objects.filter(patient=OuterRef("pk"), hospital=hospital).exclude(uhid="")
    return (
        Patient.objects.filter(
            Q(hospital=hospital) | Q(hospital_memberships__hospital=hospital, hospital_memberships__uhid="")
        )
        .filter(~Exists(has_uhid))
        .distinct()
        .order_by("created_at", "pk")
    )


class Command(BaseCommand):
    help = "Assign UHIDs to patients registered at a hospital without one (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Assign the UHIDs (otherwise only report).")
        parser.add_argument("--hospital", type=int, help="Only this hospital id.")

    def handle(self, *args, **options):
        hospitals = Hospital.objects.order_by("pk")
        if options["hospital"]:
            hospitals = hospitals.filter(pk=options["hospital"])
        total = 0
        for hospital in hospitals:
            missing = list(patients_missing_uhid(hospital))
            if not missing:
                continue
            total += len(missing)
            if not options["apply"]:
                self.stdout.write(f"hospital {hospital.pk}: {len(missing)} patient(s) without a UHID")
                continue
            for patient in missing:
                membership, _ = ensure_uhid(patient, hospital)
                self.stdout.write(f"hospital {hospital.pk}: patient {patient.pk} -> {membership.uhid}")
        if not total:
            self.stdout.write("Every registered patient has a UHID.")
        elif options["apply"]:
            self.stdout.write(f"Assigned {total} UHID(s).")
        else:
            self.stdout.write(f"{total} patient(s) without a UHID. Nothing was changed; run with --apply to assign.")
