from django.db import migrations, models


STAFF_ROLE_CHOICES = [
    ("Admin", "Admin"),
    ("Doctor", "Doctor"),
    ("Nurse", "Nurse"),
    ("Compounder", "Compounder"),
    ("Receptionist", "Receptionist"),
    ("Pharmacist", "Pharmacist"),
    ("Lab Staff", "Lab Staff"),
    ("Blood Bank Staff", "Blood Bank Staff"),
    ("Billing Staff", "Billing Staff"),
    ("Inventory Staff", "Inventory Staff"),
    ("Hospital Manager", "Hospital Manager"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_add_blood_bank_staff_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffprofile",
            name="department_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="staffprofile",
            name="license_number",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="staffprofile",
            name="specialization",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="staffprofile",
            name="years_experience",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name="staffhospitalmembership",
            name="role",
            field=models.CharField(
                choices=STAFF_ROLE_CHOICES,
                default="Receptionist",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="staffprofile",
            name="role",
            field=models.CharField(
                choices=STAFF_ROLE_CHOICES,
                default="Receptionist",
                max_length=30,
            ),
        ),
    ]
