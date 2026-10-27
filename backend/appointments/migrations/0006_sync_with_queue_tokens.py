from django.db import migrations

# Same mapping as encounters/services/appointment_status.py (copied: data
# migrations must not import app code that may change later).
TOKEN_TO_APPOINTMENT = {
    "Waiting": "Checked In",
    "Called": "Checked In",
    "Acknowledged": "Checked In",
    "Ready": "Checked In",
    "In Consultation": "In Consultation",
    "Completed": "Completed",
    "No Show": "No Show",
    "Cancelled": "Cancelled",
}


def sync_from_tokens(apps, schema_editor):
    """Appointments booked before the server kept them in step with their token."""
    Appointment = apps.get_model("appointments", "Appointment")
    QueueToken = apps.get_model("encounters", "QueueToken")
    tokens = QueueToken.objects.exclude(appointment=None).order_by("created_at")
    for token in tokens.iterator():
        target = TOKEN_TO_APPOINTMENT.get(token.status)
        if target:
            Appointment.objects.filter(pk=token.appointment_id).exclude(status="Cancelled").update(status=target)


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0005_fixed_status_list"),
        ("encounters", "0004_alter_queuetoken_created_at_alter_queuetoken_status_and_more"),
    ]

    operations = [migrations.RunPython(sync_from_tokens, migrations.RunPython.noop)]
