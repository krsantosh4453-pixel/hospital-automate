"""
Correct MAR rows the old schedule generator created as "Administered" before
any dose was given. A row marked Administered with no administered_time was
never recorded by a nurse, so it is set back to Scheduled. Rows with an
administration time are left exactly as they are. Reverse is a no-op.
"""

from django.db import migrations


def fix(apps, schema_editor):
    MARAdministration = apps.get_model("nurses", "MARAdministration")
    MARAdministration.objects.filter(status="Administered", administered_time__isnull=True).update(status="Scheduled")


class Migration(migrations.Migration):
    dependencies = [("nurses", "0005_maradministration_is_prn_and_more")]
    operations = [migrations.RunPython(fix, migrations.RunPython.noop)]
