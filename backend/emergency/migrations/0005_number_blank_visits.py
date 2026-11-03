"""Give the (at most one) ER visit saved with a blank number its ER-<id> number."""

from django.db import migrations


def number_blank_visits(apps, schema_editor):
    EmergencyVisit = apps.get_model("emergency", "EmergencyVisit")
    for visit in EmergencyVisit.objects.filter(visit_number=""):
        EmergencyVisit.objects.filter(pk=visit.pk).update(visit_number=f"ER-{visit.pk}")


class Migration(migrations.Migration):
    dependencies = [
        ("emergency", "0004_emergencynote"),
    ]

    operations = [
        migrations.RunPython(number_blank_visits, migrations.RunPython.noop),
    ]
