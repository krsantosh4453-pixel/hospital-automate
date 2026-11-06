"""One queue token per appointment, even when two desks issue it at the same moment (synthetic data only)."""

import unittest
from datetime import time

from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from appointments.models import Appointment
from config.hospital_time import hospital_today
from doctors.models import Doctor
from encounters.models import QueueToken
from encounters.services import issue_queue_token_for_appointment
from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_concurrency import run_together
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


def booked_appointment(hospital, name):
    doctor = Doctor.objects.create(hospital=hospital, name=f"Dr {name}", specialization="General",
                                   phone="9000009501")
    patient = Patient.objects.create(name=f"Synthetic {name}", age=30, gender="Male", phone="9000009502",
                                     hospital=hospital)
    return Appointment.objects.create(hospital=hospital, patient=patient, doctor=doctor,
                                      appointment_date=hospital_today(), appointment_time=time(10, 0))


class RepeatIssueTests(TestCase):
    def test_issuing_twice_returns_the_same_token(self):
        hospital = Hospital.objects.create(name="Synthetic Token Repeat", is_active=True)
        appointment = booked_appointment(hospital, "Repeat")
        desk, _ = make_staff("token_repeat_desk", hospital, role=StaffRole.RECEPTIONIST)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(desk)
        client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))

        first = client.post("/api/encounters/queue-tokens/issue/", {"appointment": appointment.id}, format="json")
        again = client.post("/api/encounters/queue-tokens/issue/", {"appointment": appointment.id}, format="json")

        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(first.json()["id"], again.json()["id"])
        self.assertEqual(QueueToken.objects.filter(appointment=appointment).count(), 1)


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ParallelIssueTests(TransactionTestCase):
    def test_parallel_issue_makes_one_token(self):
        hospital = Hospital.objects.create(name="Synthetic Token Race", is_active=True)
        appointment = booked_appointment(hospital, "Race")

        results = run_together(lambda i: issue_queue_token_for_appointment(
            Appointment.objects.get(pk=appointment.pk))[0].pk)

        self.assertFalse([r for r in results if isinstance(r, Exception)], results)
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(QueueToken.objects.filter(appointment=appointment).count(), 1)
