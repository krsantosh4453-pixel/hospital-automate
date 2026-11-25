"""
Final validation P1-2, policy decision 2026-11-25 ("Audit log se naam jodo"):
nursing assessments and notes saved without a nurse (nurses invited before a
Nurse profile was created for them) get their author from the audit log.

    python manage.py attribute_nursing_records                 # dry run: report only
    python manage.py attribute_nursing_records --apply         # attribute
    python manage.py attribute_nursing_records --apply --hospital 3

A record is attributed only when the audit log names the user who created it
and that user holds the Nurse role at the record's hospital. Their Nurse
profile is linked or created (users.staff_invite._ensure_nurse_profile). Every
change is audited; anything uncertain is reported and left alone.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from audit.models import AuditLog
from audit.services import record_audit
from nurses.models import NursingAssessment, NursingNote
from users.models import StaffHospitalMembership, StaffRole

MODELS = (("nurses.NursingAssessment", NursingAssessment), ("nurses.NursingNote", NursingNote))


def _creator(label, pk):
    entry = (AuditLog.objects.filter(model_name=label, object_id=str(pk), action__endswith=".create")
             .exclude(user__isnull=True).order_by("created_at").select_related("user").first())
    return entry.user if entry else None


def _nurse_membership(user, hospital_id):
    return (StaffHospitalMembership.objects.select_related("staff", "department")
            .filter(staff__user=user, hospital_id=hospital_id, role=StaffRole.NURSE, is_active=True).first())


class Command(BaseCommand):
    help = "Attribute nursing records saved without a nurse, from the audit log (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Attribute the records (otherwise only report).")
        parser.add_argument("--hospital", type=int, help="Only this hospital id.")

    def handle(self, *args, apply=False, hospital=None, **options):
        from users.staff_invite import _ensure_nurse_profile

        totals = {"attributed": 0, "no_audit_entry": 0, "not_a_nurse_there": 0}
        for label, model in MODELS:
            rows = model.objects.filter(nurse__isnull=True)
            if hospital:
                rows = rows.filter(hospital_id=hospital)
            for record in rows.order_by("pk"):
                user = _creator(label, record.pk)
                if user is None:
                    totals["no_audit_entry"] += 1
                    self.stdout.write(f"  {label} #{record.pk}: no audit entry names its author; left as is")
                    continue
                membership = _nurse_membership(user, record.hospital_id)
                if membership is None:
                    totals["not_a_nurse_there"] += 1
                    self.stdout.write(f"  {label} #{record.pk}: {user.username} is not a nurse at hospital "
                                      f"{record.hospital_id}; left as is")
                    continue
                totals["attributed"] += 1
                name = user.get_full_name().strip() or user.username
                self.stdout.write(f"  {label} #{record.pk}: {'attributing to' if apply else 'would attribute to'} {name}")
                if apply:
                    with transaction.atomic():
                        nurse = _ensure_nurse_profile(user, record.hospital_id, name, membership.staff.phone or "",
                                                      user.email or "", membership.department)
                        model.objects.filter(pk=record.pk, nurse__isnull=True).update(nurse=nurse)
                        record_audit(None, f"{label.lower()}.attributed", record, hospital=record.hospital_id,
                                     details={"nurse": nurse.pk, "user": user.pk, "source": "audit log"})
        verb = "Attributed" if apply else "Would attribute"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {totals['attributed']} record(s); left {totals['no_audit_entry']} without an audit entry and "
            f"{totals['not_a_nurse_there']} whose author is not a nurse there."
            + ("" if apply else " Dry run: nothing changed. Run with --apply to save.")))
