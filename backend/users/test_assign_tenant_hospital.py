"""The assign_tenant_hospital command for rows the tenancy backfill left empty (synthetic data)."""

from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from audit.models import AuditLog
from clinical.models import Allergy
from hospital.models import Hospital
from patients.models import Patient, PatientHospital


class AssignTenantHospitalTests(TestCase):
    def setUp(self):
        self.a = Hospital.objects.create(name="Synthetic Tenancy A", is_active=True)
        self.b = Hospital.objects.create(name="Synthetic Tenancy B", is_active=True)
        self.single = self.patient("Synthetic Single", "9000000901", self.a)
        self.double = self.patient("Synthetic Double", "9000000902", self.a, self.b)
        self.single_allergy = Allergy.objects.create(patient=self.single, name="Latex")
        self.double_allergy = Allergy.objects.create(patient=self.double, name="Dust")
        Allergy.objects.filter(pk__in=[self.single_allergy.pk, self.double_allergy.pk]).update(hospital=None)

    @staticmethod
    def patient(name, phone, *hospitals):
        patient = Patient.objects.create(name=name, age=30, gender="Female", phone=phone)
        for hospital in hospitals:
            PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=f"T-{phone}-{hospital.pk}")
        return patient

    def run_command(self, *args):
        out = StringIO()
        call_command("assign_tenant_hospital", *args, stdout=out)
        return out.getvalue()

    def hospital_of(self, allergy):
        allergy.refresh_from_db()
        return allergy.hospital_id

    def test_report_changes_nothing(self):
        output = self.run_command()
        self.assertIn("clinical.Allergy: 1 can be assigned, 1 need a manual decision", output)
        self.assertIn(f"id {self.double_allergy.pk}: patient registered at several hospitals", output)
        self.assertIsNone(self.hospital_of(self.single_allergy))

    def test_apply_assigns_only_unambiguous_rows_and_audits_them(self):
        self.run_command("--apply")
        self.assertEqual(self.hospital_of(self.single_allergy), self.a.pk)
        self.assertIsNone(self.hospital_of(self.double_allergy))
        log = AuditLog.objects.get(action="tenancy.assign_hospital")
        self.assertEqual((log.object_id, log.hospital_id), (str(self.single_allergy.pk), self.a.pk))

    def test_manual_assignment_to_a_registered_hospital(self):
        self.run_command("--model", "clinical.Allergy", "--ids", str(self.double_allergy.pk),
                         "--hospital", str(self.b.pk))
        self.assertEqual(self.hospital_of(self.double_allergy), self.b.pk)

    def test_manual_assignment_refuses_a_hospital_the_patient_never_visited(self):
        other = Hospital.objects.create(name="Synthetic Tenancy C", is_active=True)
        with self.assertRaisesMessage(CommandError, "is not registered at hospital"):
            self.run_command("--model", "clinical.Allergy", "--ids", str(self.single_allergy.pk),
                             "--hospital", str(other.pk))
        self.assertIsNone(self.hospital_of(self.single_allergy))

    def test_manual_assignment_needs_all_three_options(self):
        with self.assertRaisesMessage(CommandError, "needs --model, --ids and --hospital"):
            self.run_command("--model", "clinical.Allergy")
