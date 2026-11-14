"""
Call Next never completes a consultation (decision 2026-11-14, synthetic data only).

Before: Call Next marked every "In Consultation" token in the caller's scope
Completed, then called the next patient; with nobody waiting it still closed
the consultation and answered 404, and the front desk's Call Next closed
whichever doctor's patient was in the room.
"""

import unittest
from datetime import date, timedelta
from unittest import mock

from django.db import OperationalError, connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from doctors.models import Doctor
from encounters.models import QueueToken, Visit
from encounters.views import QueueTokenViewSet
from hospital.models import Hospital
from patients.models import Patient
from security_tests.test_concurrency import run_together
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

CALL_NEXT = "/api/encounters/queue-tokens/call-next/"
SERVING = QueueToken.Status.IN_CONSULTATION
WAITING = QueueToken.Status.WAITING


class CallNextSafetyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Call Next Hospital", is_active=True)
        cls.doctor_user, _ = make_staff("cn_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.colleague_user, _ = make_staff("cn_colleague", cls.hospital, role=StaffRole.DOCTOR)
        cls.desk_user, _ = make_staff("cn_desk", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.doctor = Doctor.objects.create(user=cls.doctor_user, hospital=cls.hospital, name="Dr Synthetic One",
                                           specialization="General", phone="9000000921")
        cls.colleague = Doctor.objects.create(user=cls.colleague_user, hospital=cls.hospital,
                                              name="Dr Synthetic Two", specialization="General", phone="9000000922")
        cls.patients = [
            Patient.objects.create(name=f"Synthetic Queue {n}", age=30 + n, gender="Female",
                                   phone=f"900000093{n}", hospital=cls.hospital)
            for n in range(3)
        ]

    def token(self, patient, doctor, number, state):
        visit = Visit.objects.create(hospital=self.hospital, patient=patient, doctor=doctor)
        return QueueToken.objects.create(hospital=self.hospital, visit=visit, patient=patient, doctor=doctor,
                                         token_date=date.today(), token_number=number, status=state)

    def call_next(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        return client.post(f"{CALL_NEXT}?hospital={self.hospital.id}")

    def assertStatus(self, token, expected):
        token.refresh_from_db()
        self.assertEqual(token.status, expected)

    def test_a_doctor_with_a_patient_still_in_consultation_is_refused(self):
        open_one = self.token(self.patients[0], self.doctor, 1, SERVING)
        waiting = self.token(self.patients[1], self.doctor, 2, WAITING)

        response = self.call_next(self.doctor_user)

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn("#1", response.json()["detail"])
        self.assertStatus(open_one, SERVING)
        self.assertStatus(waiting, WAITING)

    def test_with_nobody_waiting_the_open_consultation_is_left_alone(self):
        open_one = self.token(self.patients[0], self.doctor, 1, SERVING)

        response = self.call_next(self.doctor_user)

        self.assertEqual(response.status_code, 404, response.content)
        self.assertStatus(open_one, SERVING)
        open_one.visit.refresh_from_db()
        self.assertNotEqual(open_one.visit.status, "Completed")

    def test_the_desk_never_closes_another_doctors_consultation(self):
        theirs = self.token(self.patients[0], self.colleague, 1, SERVING)
        next_up = self.token(self.patients[1], self.doctor, 2, WAITING)

        response = self.call_next(self.desk_user)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["id"], next_up.id)
        self.assertStatus(next_up, QueueToken.Status.CALLED)
        self.assertStatus(theirs, SERVING)

    def test_the_desk_is_refused_when_the_next_patients_doctor_is_busy(self):
        busy = self.token(self.patients[0], self.doctor, 1, SERVING)
        next_up = self.token(self.patients[1], self.doctor, 2, WAITING)

        response = self.call_next(self.desk_user)

        self.assertEqual(response.status_code, 409, response.content)
        self.assertStatus(busy, SERVING)
        self.assertStatus(next_up, WAITING)

    def test_after_completing_the_consultation_the_next_patient_is_called(self):
        open_one = self.token(self.patients[0], self.doctor, 1, SERVING)
        waiting = self.token(self.patients[1], self.doctor, 2, WAITING)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.doctor_user)
        done = client.post(f"/api/encounters/queue-tokens/{open_one.id}/complete/?hospital={self.hospital.id}")
        self.assertEqual(done.status_code, 200, done.content)

        response = self.call_next(self.doctor_user)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["id"], waiting.id)
        self.assertStatus(open_one, QueueToken.Status.COMPLETED)
        self.assertStatus(waiting, QueueToken.Status.CALLED)

    # --- Prompt 04.2: ordering, repeats, isolation, rollback --------------------

    def test_a_normal_call_next_calls_the_first_waiting_patient(self):
        first = self.token(self.patients[0], self.doctor, 1, WAITING)
        second = self.token(self.patients[1], self.doctor, 2, WAITING)

        response = self.call_next(self.doctor_user)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["id"], first.id)
        self.assertStatus(first, QueueToken.Status.CALLED)
        self.assertStatus(second, WAITING)

    def test_queue_order_is_date_then_token_number(self):
        later = self.token(self.patients[0], self.doctor, 1, WAITING)
        earlier_day = self.token(self.patients[1], self.doctor, 9, WAITING)
        QueueToken.objects.filter(pk=earlier_day.pk).update(token_date=date.today() - timedelta(days=1))
        lower_number = self.token(self.patients[2], self.doctor, 0, WAITING)

        self.assertEqual(self.call_next(self.desk_user).json()["id"], earlier_day.id)
        self.assertStatus(later, WAITING)
        self.assertStatus(lower_number, WAITING)

    def test_another_doctors_queue_is_not_blocked(self):
        self.token(self.patients[0], self.doctor, 1, SERVING)
        theirs = self.token(self.patients[1], self.colleague, 2, WAITING)

        response = self.call_next(self.colleague_user)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["id"], theirs.id)

    def test_a_repeated_request_calls_the_same_patient_again_never_a_second_one(self):
        first = self.token(self.patients[0], self.doctor, 1, WAITING)
        second = self.token(self.patients[1], self.doctor, 2, WAITING)
        with mock.patch.object(QueueTokenViewSet, "_send_status_change_notification") as notify, \
                self.captureOnCommitCallbacks(execute=True):
            one = self.call_next(self.doctor_user)
        with mock.patch.object(QueueTokenViewSet, "_send_status_change_notification") as notify_again, \
                self.captureOnCommitCallbacks(execute=True):
            # A retry after a lost answer, with or without an Idempotency-Key header.
            client = APIClient(raise_request_exception=False)
            client.force_authenticate(self.doctor_user)
            two = client.post(f"{CALL_NEXT}?hospital={self.hospital.id}", HTTP_IDEMPOTENCY_KEY="retry-1")

        self.assertEqual((one.status_code, two.status_code), (200, 200))
        self.assertEqual(one.json()["id"], first.id)
        self.assertEqual(two.json()["id"], first.id)
        self.assertStatus(second, WAITING)
        # The first call moved Waiting -> Called; the repeat was a re-call, not a new assignment.
        self.assertEqual(notify.call_args.args[1:], (WAITING, QueueToken.Status.CALLED))
        self.assertEqual(notify_again.call_args.args[1:], (QueueToken.Status.CALLED, QueueToken.Status.CALLED))

    def test_a_new_idempotency_key_does_not_bypass_the_busy_doctor_rule(self):
        self.token(self.patients[0], self.doctor, 1, SERVING)
        waiting = self.token(self.patients[1], self.doctor, 2, WAITING)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.desk_user)

        for key in ("key-a", "key-b"):
            with self.subTest(key=key):
                response = client.post(f"{CALL_NEXT}?hospital={self.hospital.id}", HTTP_IDEMPOTENCY_KEY=key)
                self.assertEqual(response.status_code, 409, response.content)
        self.assertStatus(waiting, WAITING)

    def test_another_hospital_stays_isolated(self):
        other = Hospital.objects.create(name="Synthetic Call Next Other", is_active=True)
        outsider, _ = make_staff("cn_outsider", other, role=StaffRole.RECEPTIONIST)
        waiting = self.token(self.patients[0], self.doctor, 1, WAITING)

        self.assertEqual(self.call_next(outsider).status_code, 403)
        self.assertStatus(waiting, WAITING)

    def test_unauthenticated_and_unpermitted_users_are_refused(self):
        waiting = self.token(self.patients[0], self.doctor, 1, WAITING)
        lab_user, _ = make_staff("cn_lab", self.hospital, role=StaffRole.LAB_STAFF)

        anonymous = APIClient(raise_request_exception=False).post(f"{CALL_NEXT}?hospital={self.hospital.id}")
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(self.call_next(lab_user).status_code, 403)
        self.assertStatus(waiting, WAITING)

    def test_a_hospital_id_that_is_not_a_number_is_refused(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.desk_user)
        self.assertEqual(client.post(f"{CALL_NEXT}?hospital=abc").status_code, 400)

    def test_a_failure_part_way_rolls_back_and_messages_nobody(self):
        waiting = self.token(self.patients[0], self.doctor, 1, WAITING)
        with mock.patch.object(QueueTokenViewSet, "_recalculate_estimates", side_effect=RuntimeError("synthetic")), \
                mock.patch.object(QueueTokenViewSet, "_send_status_change_notification") as notify, \
                self.captureOnCommitCallbacks(execute=True):
            response = self.call_next(self.desk_user)

        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"synthetic", response.content)
        self.assertStatus(waiting, WAITING)
        notify.assert_not_called()

    def test_sqlite_refusing_a_simultaneous_writer_is_a_409_not_a_500(self):
        # Simulates what SQLite raises for the second of two writers at the same
        # moment; the real two-writer race is ParallelCallNextTests (PostgreSQL).
        waiting = self.token(self.patients[0], self.doctor, 1, WAITING)
        with mock.patch("encounters.views.lock_doctor", side_effect=OperationalError("database is locked")):
            response = self.call_next(self.desk_user)

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn("same moment", response.json()["detail"])
        self.assertStatus(waiting, WAITING)


@unittest.skipUnless(connection.vendor == "postgresql", "needs real row locks (set TEST_DATABASE_URL)")
class ParallelCallNextTests(TransactionTestCase):
    def test_simultaneous_call_next_calls_one_patient_once(self):
        hospital = Hospital.objects.create(name="Synthetic Call Next Race", is_active=True)
        desk_user, _ = make_staff("cn_race_desk", hospital, role=StaffRole.RECEPTIONIST)
        doctor_user, _ = make_staff("cn_race_doctor", hospital, role=StaffRole.DOCTOR)
        doctor = Doctor.objects.create(user=doctor_user, hospital=hospital, name="Dr Synthetic Race",
                                       specialization="General", phone="9000000941")
        tokens = []
        for number in (1, 2):
            patient = Patient.objects.create(name=f"Synthetic Race {number}", age=40, gender="Male",
                                             phone=f"900000095{number}", hospital=hospital)
            visit = Visit.objects.create(hospital=hospital, patient=patient, doctor=doctor)
            tokens.append(QueueToken.objects.create(hospital=hospital, visit=visit, patient=patient, doctor=doctor,
                                                    token_date=date.today(), token_number=number))
        first, second = tokens

        def call(_index):
            client = APIClient(raise_request_exception=False)
            client.force_authenticate(desk_user)
            response = client.post(f"{CALL_NEXT}?hospital={hospital.id}")
            return response.status_code, response.json().get("id")

        with mock.patch.object(QueueTokenViewSet, "_send_status_change_notification") as notify:
            results = run_together(call)

        self.assertFalse([r for r in results if isinstance(r, Exception)], results)
        self.assertTrue(all(code in (200, 409) for code, _ in results), results)
        self.assertTrue(any(code == 200 for code, _ in results), results)
        # Every success called the first patient; the second patient was never called.
        self.assertEqual({rx for code, rx in results if code == 200}, {first.id}, results)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.status, second.status), (QueueToken.Status.CALLED, WAITING))
        # Exactly one request moved the first patient from Waiting to Called.
        transitions = [c for c in notify.call_args_list if c.args[1] == WAITING]
        self.assertEqual(len(transitions), 1, notify.call_args_list)
