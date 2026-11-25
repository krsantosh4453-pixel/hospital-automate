"""attribute_nursing_records (P1-2 follow-up; policy decision 2026-11-25). Synthetic data only."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from audit.models import AuditLog
from hospital.models import Hospital
from nurses.models import Nurse, NursingAssessment, NursingNote
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class AttributeNursingRecordsTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Attribution", is_active=True)
        self.patient = Patient.objects.create(name="Synthetic Ward Patient", age=60, gender="Male",
                                              phone="9000091101", hospital=self.hospital)
        self.nurse_user, _ = make_staff("attr_nurse", self.hospital, role=StaffRole.NURSE)
        self.nurse_user.first_name, self.nurse_user.last_name = "Synthetic", "Asha"
        self.nurse_user.save()
        self.clerk, _ = make_staff("attr_clerk", self.hospital, role=StaffRole.RECEPTIONIST)

    def _record(self, model, author, **fields):
        record = model.objects.create(patient=self.patient, hospital=self.hospital, **fields)
        if author is not None:
            AuditLog.objects.create(user=author, hospital=self.hospital, action=f"{model._meta.label_lower}.create",
                                    model_name=model._meta.label, object_id=str(record.pk))
        return record

    def run_command(self, *args):
        out = StringIO()
        call_command("attribute_nursing_records", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_reports_and_changes_nothing(self):
        record = self._record(NursingAssessment, self.nurse_user, vitals={"temperature": "37.0"})

        output = self.run_command()

        self.assertIn("Would attribute 1 record(s)", output)
        record.refresh_from_db()
        self.assertIsNone(record.nurse_id)
        self.assertFalse(Nurse.objects.exists())

    def test_apply_attributes_records_to_the_nurse_who_created_them(self):
        assessment = self._record(NursingAssessment, self.nurse_user, vitals={"temperature": "37.0"})
        note = self._record(NursingNote, self.nurse_user, note="Synthetic note")

        output = self.run_command("--apply")

        nurse = Nurse.objects.get(user=self.nurse_user, hospital=self.hospital)
        self.assertEqual(nurse.name, "Synthetic Asha")
        assessment.refresh_from_db()
        note.refresh_from_db()
        self.assertEqual((assessment.nurse_id, note.nurse_id), (nurse.pk, nurse.pk))
        self.assertIn("Attributed 2 record(s)", output)
        self.assertTrue(AuditLog.objects.filter(action="nurses.nursingassessment.attributed").exists())

    def test_uncertain_records_are_left_alone(self):
        unknown = self._record(NursingAssessment, None, vitals={"pulse": "80"})
        by_clerk = self._record(NursingAssessment, self.clerk, vitals={"pulse": "82"})

        output = self.run_command("--apply")

        unknown.refresh_from_db()
        by_clerk.refresh_from_db()
        self.assertIsNone(unknown.nurse_id)
        self.assertIsNone(by_clerk.nurse_id)
        self.assertIn("left 1 without an audit entry and 1 whose author is not a nurse there", output)

    def test_an_existing_profile_is_reused_and_records_already_attributed_are_untouched(self):
        existing = Nurse.objects.create(user=self.nurse_user, hospital=self.hospital, name="Synthetic Asha", phone="9000091102")
        done = NursingAssessment.objects.create(patient=self.patient, hospital=self.hospital, nurse=existing, vitals={})
        open_record = self._record(NursingAssessment, self.nurse_user, vitals={"pulse": "70"})

        self.run_command("--apply")

        self.assertEqual(Nurse.objects.count(), 1)
        open_record.refresh_from_db()
        self.assertEqual(open_record.nurse_id, existing.pk)
        done.refresh_from_db()
        self.assertEqual(done.nurse_id, existing.pk)
