"""
Link existing Doctor profiles to staff logins where the match is unambiguous:
exactly one active user has the doctor's email, that user is Doctor staff with
an active membership in the doctor's hospital, and no other doctor at that
hospital is linked to them. Everything else stays unlinked for an admin to
resolve. Reversing is a no-op (the schema migration drops the column).
"""

from django.db import migrations


def link(apps, schema_editor):
    Doctor = apps.get_model("doctors", "Doctor")
    User = apps.get_model("auth", "User")
    Membership = apps.get_model("users", "StaffHospitalMembership")
    for doctor in Doctor.objects.filter(user__isnull=True).exclude(email="").exclude(hospital__isnull=True):
        users = list(User.objects.filter(email__iexact=doctor.email, is_active=True)[:2])
        if len(users) != 1:
            continue
        user = users[0]
        if not Membership.objects.filter(
            staff__user=user, hospital_id=doctor.hospital_id, role="Doctor", is_active=True
        ).exists():
            continue
        if Doctor.objects.filter(user=user, hospital_id=doctor.hospital_id).exists():
            continue
        doctor.user = user
        doctor.save(update_fields=["user"])


class Migration(migrations.Migration):
    dependencies = [
        ("doctors", "0006_doctor_user_doctor_doctor_unique_user_per_hospital"),
        ("users", "0004_compounder_role_and_staff_profile_details"),
    ]

    operations = [migrations.RunPython(link, migrations.RunPython.noop)]
