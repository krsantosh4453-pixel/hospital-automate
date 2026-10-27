"""
Backfill the owning hospital on rows that previously had none.

Rules (best available evidence, never deletes rows):
- MedicalRecord: its visit's hospital, else the patient's registering hospital.
- InsuranceClaim: its invoice's hospital, else the patient's registering hospital.
- Allergy, notification Consent, AIInteraction, PatientDocument: the patient's
  registering hospital (Patient.hospital).
- AuditLog: left empty; historic rows had no hospital context and stay
  visible only to platform administrators.

Rows whose patient has no registering hospital stay NULL and are hidden from
hospital staff until a hospital is assigned (see docs/DATABASE.md).
Reversing this migration is a no-op; the schema migrations drop the columns.
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery


def backfill(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    patient_hospital = Subquery(Patient.objects.filter(pk=OuterRef("patient_id")).values("hospital_id")[:1])

    MedicalRecord = apps.get_model("clinical", "MedicalRecord")
    MedicalRecord.objects.filter(hospital__isnull=True, visit__isnull=False).update(
        hospital_id=Subquery(apps.get_model("encounters", "Visit").objects.filter(
            pk=OuterRef("visit_id")).values("hospital_id")[:1])
    )
    MedicalRecord.objects.filter(hospital__isnull=True).update(hospital_id=patient_hospital)

    InsuranceClaim = apps.get_model("billing", "InsuranceClaim")
    InsuranceClaim.objects.filter(hospital__isnull=True, invoice__isnull=False).update(
        hospital_id=Subquery(apps.get_model("billing", "Invoice").objects.filter(
            pk=OuterRef("invoice_id")).values("hospital_id")[:1])
    )
    InsuranceClaim.objects.filter(hospital__isnull=True).update(hospital_id=patient_hospital)

    for app_label, model_name in (
        ("clinical", "Allergy"),
        ("notifications", "Consent"),
        ("audit", "AIInteraction"),
        ("patients", "PatientDocument"),
    ):
        model = apps.get_model(app_label, model_name)
        model.objects.filter(hospital__isnull=True, patient__isnull=False).update(hospital_id=patient_hospital)


class Migration(migrations.Migration):
    dependencies = [
        ("clinical", "0004_allergy_hospital_medicalrecord_hospital"),
        ("billing", "0005_insuranceclaim_hospital"),
        ("notifications", "0005_consent_hospital"),
        ("audit", "0003_alter_aiinteraction_options_alter_auditlog_options_and_more"),
        ("patients", "0007_patientdocument_hospital"),
        ("encounters", "0004_alter_queuetoken_created_at_alter_queuetoken_status_and_more"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
