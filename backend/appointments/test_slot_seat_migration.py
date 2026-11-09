"""Migration appointments/0009: existing shared slots keep every booking, numbered by age (synthetic data)."""

from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("appointments", "0008_appointment_idempotency_key"), ("doctors", "0008_doctor_registration_number")]
AFTER = [("appointments", "0009_appointment_slot_seat"), ("doctors", "0009_doctor_slot_capacity")]


class SlotSeatMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        self.migrate(executor_leaf_nodes())

    def test_shared_slots_keep_every_booking_with_numbered_seats(self):
        old = self.migrate(BEFORE)
        hospital = old.get_model("hospital", "Hospital").objects.create(name="Synthetic Legacy")
        doctor = old.get_model("doctors", "Doctor").objects.create(
            hospital=hospital, name="Dr Legacy", specialization="General", phone="9000072001")
        Patient = old.get_model("patients", "Patient")
        Appointment = old.get_model("appointments", "Appointment")
        slot = {"hospital": hospital, "doctor": doctor, "appointment_date": "2030-01-02", "appointment_time": "10:00"}
        ids = [
            Appointment.objects.create(
                patient=Patient.objects.create(name=f"Synthetic Legacy {i}", age=40, gender="Male",
                                               phone=f"900007300{i}"),
                status=status, **slot).id
            for i, status in enumerate(["Scheduled", "Checked In", "Cancelled", "Scheduled"])
        ]

        new = self.migrate(AFTER)

        Appointment = new.get_model("appointments", "Appointment")
        seats = dict(Appointment.objects.filter(id__in=ids).values_list("id", "slot_seat"))
        # Active bookings are numbered oldest first; the cancelled one holds no place.
        self.assertEqual([seats[ids[0]], seats[ids[1]], seats[ids[3]]], [1, 2, 3])
        self.assertEqual(new.get_model("doctors", "Doctor").objects.get(pk=doctor.pk).slot_capacity, 1)

        report = StringIO()
        call_command("report_duplicate_bookings", stdout=report)
        self.assertIn(f"doctor {doctor.pk}, 2030-01-02 10:00:00: 3 active booking(s), capacity 1", report.getvalue())


def executor_leaf_nodes():
    executor = MigrationExecutor(connection)
    return executor.loader.graph.leaf_nodes()
