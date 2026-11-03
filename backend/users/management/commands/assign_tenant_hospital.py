"""
Find and assign the owning hospital of rows the tenancy backfill
(clinical/0005_backfill_tenant_hospital) left empty. Until a row has a
hospital, scoping fails closed and hospital staff cannot see it.

    python manage.py assign_tenant_hospital                 # report only
    python manage.py assign_tenant_hospital --apply         # assign unambiguous rows
    python manage.py assign_tenant_hospital --model clinical.Allergy --ids 4 9 --hospital 2

--apply uses, in order: the hospital of the row's visit or invoice, the
patient's registering hospital, or the patient's one active hospital
registration. Rows with no candidate, or several, are listed for a manual
decision. Every assignment is written to the audit log.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from audit.services import record_audit
from hospital.models import Hospital

# (model, relation whose hospital owns the row) for the backfilled models.
BACKFILLED_MODELS = (
    ("clinical.MedicalRecord", "visit"),
    ("billing.InsuranceClaim", "invoice"),
    ("clinical.Allergy", None),
    ("notifications.Consent", None),
    ("audit.AIInteraction", None),
    ("patients.PatientDocument", None),
)
AUDIT_ACTION = "tenancy.assign_hospital"
# Unassigned row ids printed per model before the list is cut short.
MAX_LISTED_IDS = 50


def candidate_hospital(row, parent_field):
    """(hospital id, rule) when exactly one hospital owns ``row``, else (None, reason)."""
    parent = getattr(row, parent_field, None) if parent_field else None
    if parent is not None and parent.hospital_id:
        return parent.hospital_id, f"{parent_field} hospital"
    patient = row.patient
    if patient is None:
        return None, "no patient"
    if patient.hospital_id:
        return patient.hospital_id, "patient registering hospital"
    registrations = list(
        patient.hospital_memberships.filter(is_active=True).values_list("hospital_id", flat=True).distinct()
    )
    if len(registrations) == 1:
        return registrations[0], "patient's only hospital registration"
    if registrations:
        return None, "patient registered at several hospitals"
    return None, "patient has no hospital"


def patient_registered_at(patient, hospital_id):
    return patient.hospital_id == hospital_id or patient.hospital_memberships.filter(
        hospital_id=hospital_id, is_active=True,
    ).exists()


class Command(BaseCommand):
    help = "Report or assign the owning hospital of rows the tenancy backfill left empty."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Assign rows that have exactly one candidate.")
        parser.add_argument("--model", help="app_label.Model for a manual assignment.")
        parser.add_argument("--ids", nargs="+", type=int, help="Row ids for a manual assignment.")
        parser.add_argument("--hospital", type=int, help="Hospital id for a manual assignment.")

    def handle(self, *args, **options):
        if options["model"] or options["ids"] or options["hospital"]:
            self.assign_manually(options["model"], options["ids"], options["hospital"])
            return
        self.resolve_all(apply=options["apply"])

    def resolve_all(self, apply):
        total_assigned = total_left = 0
        for label, parent_field in BACKFILLED_MODELS:
            assigned, left = self.resolve_model(label, parent_field, apply)
            total_assigned += assigned
            total_left += len(left)
            self.stdout.write(f"{label}: {assigned} {'assigned' if apply else 'can be assigned'}, "
                              f"{len(left)} need a manual decision")
            for row_id, reason in left[:MAX_LISTED_IDS]:
                self.stdout.write(f"  id {row_id}: {reason}")
            if len(left) > MAX_LISTED_IDS:
                self.stdout.write(f"  ... and {len(left) - MAX_LISTED_IDS} more")
        verb = "Assigned" if apply else "Would assign"
        self.stdout.write(self.style.SUCCESS(f"{verb} {total_assigned} rows; {total_left} left for manual assignment."))

    @transaction.atomic
    def resolve_model(self, label, parent_field, apply):
        model = apps.get_model(label)
        related = ["patient"] + ([parent_field] if parent_field else [])
        assigned, left = 0, []
        for row in model.objects.filter(hospital__isnull=True).select_related(*related).order_by("pk"):
            hospital_id, rule = candidate_hospital(row, parent_field)
            if hospital_id is None:
                left.append((row.pk, rule))
                continue
            assigned += 1
            if apply:
                self.assign(row, hospital_id, rule)
        return assigned, left

    @transaction.atomic
    def assign_manually(self, label, row_ids, hospital_id):
        if not (label and row_ids and hospital_id):
            raise CommandError("A manual assignment needs --model, --ids and --hospital together.")
        known = {name for name, _ in BACKFILLED_MODELS}
        if label not in known:
            raise CommandError(f"--model must be one of: {', '.join(sorted(known))}")
        if not Hospital.objects.filter(pk=hospital_id).exists():
            raise CommandError(f"Hospital {hospital_id} does not exist.")

        rows = {row.pk: row for row in apps.get_model(label).objects.select_related("patient").filter(pk__in=row_ids)}
        problems = []
        for row_id in row_ids:
            row = rows.get(row_id)
            if row is None:
                problems.append(f"id {row_id}: not found")
            elif row.hospital_id is not None:
                problems.append(f"id {row_id}: already belongs to hospital {row.hospital_id}")
            elif row.patient is not None and not patient_registered_at(row.patient, hospital_id):
                problems.append(f"id {row_id}: patient {row.patient_id} is not registered at hospital {hospital_id}")
        if problems:
            raise CommandError("Nothing assigned:\n" + "\n".join(problems))

        for row in rows.values():
            self.assign(row, hospital_id, "manual")
        self.stdout.write(self.style.SUCCESS(f"Assigned {len(rows)} {label} rows to hospital {hospital_id}."))

    @staticmethod
    def assign(row, hospital_id, rule):
        row.hospital_id = hospital_id
        row.save(update_fields=["hospital"])
        record_audit(None, AUDIT_ACTION, row, hospital=hospital_id, details={"rule": rule})
