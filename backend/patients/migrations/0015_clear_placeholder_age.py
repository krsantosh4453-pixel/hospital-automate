"""
BUG-04: self-registration (and Google sign-up) stored age 1 for every patient,
because the form asked for no age. Those placeholder ages become "not
recorded" (NULL) so no screen shows an adult as a one-year-old.

Only rows with the placeholder's signature change: age 1, no date of birth, a
portal login, and no direct hospital (reception registration always sets the
hospital and asks for the age). Reversible: the same rows get 1 back.
"""

from django.db import migrations


def placeholder_rows(Patient):
    return Patient.objects.filter(age=1, date_of_birth__isnull=True, user__isnull=False, hospital__isnull=True)


def clear(apps, schema_editor):
    placeholder_rows(apps.get_model("patients", "Patient")).update(age=None)


def restore(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    Patient.objects.filter(
        age__isnull=True, date_of_birth__isnull=True, user__isnull=False, hospital__isnull=True,
    ).update(age=1)


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0014_alter_patient_age"),
    ]

    operations = [
        migrations.RunPython(clear, restore),
    ]
