"""
Prescription.idempotency_key: a retried POST returns the prescription its key
already wrote instead of writing a second one.

Additive only. Existing rows get "" and the unique constraint ignores blank
keys, so no existing prescription can conflict.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clinical", "0014_signed_records_and_prescription_revisions"),
    ]

    operations = [
        migrations.AddField(
            model_name="prescription",
            name="idempotency_key",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddConstraint(
            model_name="prescription",
            constraint=models.UniqueConstraint(
                condition=models.Q(("idempotency_key", ""), _negated=True),
                fields=("hospital", "idempotency_key"),
                name="prescription_unique_idempotency_key",
            ),
        ),
    ]
