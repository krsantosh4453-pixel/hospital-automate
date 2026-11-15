"""
Start Consultation and Call Next take the same doctor lock (Prompt 04.3, synthetic data only).

Before: Start Consultation read and saved the token with no transaction and no
lock, and never checked for another open consultation. It could slip in
between Call Next's busy check and its save (a patient called while the
doctor had just started someone else), and two Start Consultations for one
doctor both succeeded (two open consultations).
"""

import threading
import time
import unittest
from datetime import date
from unittest import mock

from django.db import OperationalError, connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from doctors.models import Doctor
from encounters.models import QueueToken, Visit
from encounters.views import QueueTokenViewSet
from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

CALLED = QueueToken.Status.CALLED
SERVING = QueueToken.Status.IN_CONSULTATION
WAITING = QueueToken.Status.WAITING
# How long a held lock is kept open in the race tests; long enough for the
# other request to arrive and wait, short enough to keep the suite quick.
HOLD_SECONDS = 1.0
SECOND_REQUEST_DELAY = 0.3
# A request that waited for the held lock was held at least this long.
MIN_WAIT_SECONDS = (HOLD_SECONDS - SECOND_REQUEST_DELAY) * 0.8


def start_url(token, hospital):
    return f"/api/encounters/queue-tokens/{token.pk}/start-consultation/?hospital={hospital.pk}"


def call_next_url(hospital):
    return f"/api/encounters/queue-tokens/call-next/?hospital={hospital.pk}"


def post(user, url):
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(user)
    return client.post(url)


class QueueFixture:
    """Two doctors of one hospital, a front desk, and synthetic patients."""

    def build(self, prefix):
        self.hospital = Hospital.objects.create(name=f"Synthetic {prefix} Hospital", is_active=True)
        self.doctor_user, _ = make_staff(f"{prefix}_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.colleague_user, _ = make_staff(f"{prefix}_colleague", self.hospital, role=StaffRole.DOCTOR)
        self.desk_user, _ = make_staff(f"{prefix}_desk", self.hospital, role=StaffRole.RECEPTIONIST)
        self.doctor = Doctor.objects.create(user=self.doctor_user, hospital=self.hospital, name=f"Dr {prefix} One",
                                            specialization="General", phone="9000000961")
        self.colleague = Doctor.objects.create(user=self.colleague_user, hospital=self.hospital,
                                               name=f"Dr {prefix} Two", specialization="General", phone="9000000962")
        self.patients = [
            Patient.objects.create(name=f"Synthetic {prefix} {n}", age=30 + n, gender="Female",
                                   phone=f"900000097{n}", hospital=self.hospital)
            for n in range(4)
        ]

    def token(self, patient, doctor, number, state):
        visit = Visit.objects.create(hospital=self.hospital, patient=patient, doctor=doctor)
        return QueueToken.objects.create(hospital=self.hospital, visit=visit, patient=patient, doctor=doctor,
                                         token_date=date.today(), token_number=number, status=state)

    def status_of(self, token):
        return QueueToken.objects.get(pk=token.pk).status


class StartConsultationRuleTests(QueueFixture, TestCase):
    def setUp(self):
        self.build("sc")

    def test_starting_a_called_patient_works_and_messages_after_commit(self):
        token = self.token(self.patients[0], self.doctor, 1, CALLED)
        with mock.patch.object(QueueTokenViewSet, "_send_status_change_notification") as notify, \
                self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = post(self.doctor_user, start_url(token, self.hospital))

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.status_of(token), SERVING)
        token.visit.refresh_from_db()
        self.assertEqual(token.visit.status, "In Consultation")
        self.assertEqual(len(callbacks), 1)
        notify.assert_called_once()

    def test_a_doctor_with_a_consultation_open_cannot_start_another(self):
        open_one = self.token(self.patients[0], self.doctor, 1, SERVING)
        next_one = self.token(self.patients[1], self.doctor, 2, CALLED)

        response = post(self.doctor_user, start_url(next_one, self.hospital))

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn("#1", response.json()["detail"])
        self.assertEqual((self.status_of(open_one), self.status_of(next_one)), (SERVING, CALLED))
        next_one.visit.refresh_from_db()
        self.assertNotEqual(next_one.visit.status, "In Consultation")

    def test_after_completing_the_next_consultation_can_start(self):
        open_one = self.token(self.patients[0], self.doctor, 1, SERVING)
        next_one = self.token(self.patients[1], self.doctor, 2, CALLED)
        self.assertEqual(post(self.doctor_user, f"/api/encounters/queue-tokens/{open_one.pk}/complete/"
                                                f"?hospital={self.hospital.pk}").status_code, 200)

        self.assertEqual(post(self.doctor_user, start_url(next_one, self.hospital)).status_code, 200)
        self.assertEqual(self.status_of(next_one), SERVING)

    def test_another_doctor_is_not_blocked(self):
        self.token(self.patients[0], self.doctor, 1, SERVING)
        theirs = self.token(self.patients[1], self.colleague, 2, CALLED)

        self.assertEqual(post(self.colleague_user, start_url(theirs, self.hospital)).status_code, 200)
        self.assertEqual(self.status_of(theirs), SERVING)

    def test_starting_the_same_consultation_twice_is_refused(self):
        token = self.token(self.patients[0], self.doctor, 1, CALLED)
        self.assertEqual(post(self.doctor_user, start_url(token, self.hospital)).status_code, 200)

        again = post(self.doctor_user, start_url(token, self.hospital))

        self.assertEqual(again.status_code, 400, again.content)
        self.assertEqual(self.status_of(token), SERVING)

    def test_a_waiting_token_cannot_skip_straight_into_consultation(self):
        token = self.token(self.patients[0], self.doctor, 1, WAITING)
        self.assertEqual(post(self.doctor_user, start_url(token, self.hospital)).status_code, 400)
        self.assertEqual(self.status_of(token), WAITING)

    def test_an_unknown_token_is_not_found(self):
        response = post(self.doctor_user, f"/api/encounters/queue-tokens/999999/start-consultation/"
                                          f"?hospital={self.hospital.pk}")
        self.assertEqual(response.status_code, 404)

    def test_another_doctor_cannot_start_this_doctors_patient(self):
        token = self.token(self.patients[0], self.doctor, 1, CALLED)

        response = post(self.colleague_user, start_url(token, self.hospital))

        self.assertIn(response.status_code, (403, 404), response.content)
        self.assertEqual(self.status_of(token), CALLED)

    def test_another_hospital_cannot_start_or_lock_this_hospitals_patient(self):
        token = self.token(self.patients[0], self.doctor, 1, CALLED)
        other = Hospital.objects.create(name="Synthetic sc Other", is_active=True)
        outsider, _ = make_staff("sc_outsider", other, role=StaffRole.DOCTOR)

        with mock.patch("encounters.views.lock_doctor") as lock:
            response = post(outsider, start_url(token, other))
        self.assertIn(response.status_code, (403, 404), response.content)
        lock.assert_not_called()
        self.assertEqual(self.status_of(token), CALLED)

    def test_unauthenticated_requests_are_refused(self):
        token = self.token(self.patients[0], self.doctor, 1, CALLED)
        response = APIClient(raise_request_exception=False).post(start_url(token, self.hospital))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.status_of(token), CALLED)

    def test_a_failure_part_way_rolls_back_and_messages_nobody(self):
        token = self.token(self.patients[0], self.doctor, 1, CALLED)
        with mock.patch.object(QueueTokenViewSet, "_recalculate_estimates", side_effect=RuntimeError("synthetic")), \
                mock.patch.object(QueueTokenViewSet, "_send_status_change_notification") as notify, \
                self.captureOnCommitCallbacks(execute=True):
            response = post(self.doctor_user, start_url(token, self.hospital))

        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"synthetic", response.content)
        self.assertEqual(self.status_of(token), CALLED)
        token.visit.refresh_from_db()
        self.assertNotEqual(token.visit.status, "In Consultation")
        notify.assert_not_called()

    def test_sqlite_refusing_a_simultaneous_writer_is_a_409_not_a_500(self):
        # Simulates SQLite's answer to a second writer at the same moment; the
        # real two-request races are StartConsultationRaceTests (PostgreSQL).
        token = self.token(self.patients[0], self.doctor, 1, CALLED)
        with mock.patch("encounters.views.lock_doctor", side_effect=OperationalError("database is locked")):
            response = post(self.doctor_user, start_url(token, self.hospital))

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn("same moment", response.json()["detail"])
        self.assertEqual(self.status_of(token), CALLED)


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class StartConsultationRaceTests(QueueFixture, TransactionTestCase):
    """
    Real concurrent requests on separate connections. The thread named ``holder``
    keeps the doctor lock for HOLD_SECONDS by pausing inside the busy check,
    which both requests run after taking the lock; the other request arrives
    meanwhile, so the order of the two is fixed rather than left to chance.
    """

    def setUp(self):
        self.build("race")

    def race(self, holder, other):
        """Run ``holder`` and, a moment later, ``other``; return their (status, seconds taken)."""
        real = QueueTokenViewSet._open_consultation

        def slow_for_holder(view, *args, **kwargs):
            found = real(view, *args, **kwargs)
            if threading.current_thread().name == "holder":
                time.sleep(HOLD_SECONDS)
            return found

        results = {}

        def run(name, job, delay):
            time.sleep(delay)
            began = time.monotonic()
            try:
                results[name] = (job().status_code, time.monotonic() - began)
            except Exception as exc:  # collected for the assertions
                results[name] = (exc, time.monotonic() - began)
            finally:
                connection.close()

        with mock.patch.object(QueueTokenViewSet, "_open_consultation", autospec=True, side_effect=slow_for_holder):
            threads = [threading.Thread(target=run, name="holder", args=("holder", holder, 0)),
                       threading.Thread(target=run, name="other", args=("other", other, SECOND_REQUEST_DELAY))]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        return results["holder"], results["other"]

    def test_a_start_consultation_first_then_call_next_calls_nobody(self):
        next_up = self.token(self.patients[0], self.doctor, 1, WAITING)
        starting = self.token(self.patients[1], self.doctor, 2, CALLED)

        (start, _), (call, call_took) = self.race(
            lambda: post(self.doctor_user, start_url(starting, self.hospital)),
            lambda: post(self.desk_user, call_next_url(self.hospital)),
        )

        self.assertEqual((start, call), (200, 409))
        self.assertGreaterEqual(call_took, MIN_WAIT_SECONDS, "Call Next must wait for the doctor lock")
        self.assertEqual((self.status_of(starting), self.status_of(next_up)), (SERVING, WAITING))

    def test_b_call_next_first_then_start_consultation_waits_and_rechecks(self):
        next_up = self.token(self.patients[0], self.doctor, 1, WAITING)
        starting = self.token(self.patients[1], self.doctor, 2, CALLED)

        (call, _), (start, start_took) = self.race(
            lambda: post(self.desk_user, call_next_url(self.hospital)),
            lambda: post(self.doctor_user, start_url(starting, self.hospital)),
        )

        # Call Next found the doctor free and called the next patient; Start
        # Consultation waited, re-read the token and found it still Called.
        self.assertEqual((call, start), (200, 200))
        self.assertGreaterEqual(start_took, MIN_WAIT_SECONDS, "Start Consultation must wait for the doctor lock")
        self.assertEqual((self.status_of(next_up), self.status_of(starting)), (CALLED, SERVING))
        self.assertEqual(QueueToken.objects.filter(doctor=self.doctor, status=SERVING).count(), 1)

    def test_c_two_start_consultations_for_one_doctor_open_one(self):
        first = self.token(self.patients[0], self.doctor, 1, CALLED)
        second = self.token(self.patients[1], self.doctor, 2, CALLED)

        (one, _), (two, _) = self.race(
            lambda: post(self.doctor_user, start_url(first, self.hospital)),
            lambda: post(self.doctor_user, start_url(second, self.hospital)),
        )

        self.assertEqual((one, two), (200, 409))
        self.assertEqual((self.status_of(first), self.status_of(second)), (SERVING, CALLED))
        self.assertEqual(QueueToken.objects.filter(doctor=self.doctor, status=SERVING).count(), 1)

    def test_d_another_doctor_is_not_held_up(self):
        mine = self.token(self.patients[0], self.doctor, 1, CALLED)
        theirs = self.token(self.patients[1], self.colleague, 2, CALLED)

        (one, _), (two, two_took) = self.race(
            lambda: post(self.doctor_user, start_url(mine, self.hospital)),
            lambda: post(self.colleague_user, start_url(theirs, self.hospital)),
        )

        self.assertEqual((one, two), (200, 200))
        self.assertLess(two_took, MIN_WAIT_SECONDS / 2, "the other doctor's request must not wait for this doctor's lock")
        self.assertEqual((self.status_of(mine), self.status_of(theirs)), (SERVING, SERVING))
