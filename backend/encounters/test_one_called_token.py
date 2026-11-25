"""
BUG-011 (web audit; remaining work 2026-11-25): a doctor has at most one
called patient at a time. Calling another while one is still Called,
Acknowledged or Ready is refused (409) until that one starts, is skipped or is
marked no-show. Re-calling the same patient stays allowed. Synthetic data only.
"""
from django.test import TestCase

from encounters.models import QueueToken
from encounters.test_visit_lifecycle import LifecycleFixture, Token, client_for


class OneCalledTokenPerDoctorTests(LifecycleFixture, TestCase):
    def setUp(self):
        self.build("oct")

    def call(self, token, user=None):
        return client_for(user or self.desk_user, self.hospital).post(f"/api/encounters/queue-tokens/{token.pk}/call/")

    def call_next(self, user=None):
        return client_for(user or self.desk_user, self.hospital).post(
            f"/api/encounters/queue-tokens/call-next/?hospital={self.hospital.pk}")

    def test_a_second_patient_is_not_called_while_one_is_called(self):
        first = self.booked("First", state=Token.CALLED)
        third = self.booked("Third", state=Token.WAITING)

        response = self.call(third)

        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn(f"#{first.token_number}", response.json()["detail"])
        self.assertEqual(QueueToken.objects.get(pk=third.pk).status, Token.WAITING)

    def test_acknowledged_and_ready_also_count_as_called(self):
        for state in (Token.ACKNOWLEDGED, Token.READY):
            with self.subTest(state=state):
                self.booked(f"Held {state}", state=state)
                waiting = self.booked(f"Next {state}", state=Token.WAITING)
                self.assertEqual(self.call(waiting).status_code, 409)
                QueueToken.objects.filter(status=state).update(status=Token.SKIPPED)

    def test_call_next_does_not_call_a_second_patient(self):
        # Token 2 was called out of order; token 1 still waits.
        early = self.booked("Early", state=Token.WAITING, number=1)
        self.booked("Called", state=Token.CALLED, number=2)

        response = self.call_next()

        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(QueueToken.objects.get(pk=early.pk).status, Token.WAITING)

    def test_calling_is_free_again_once_the_called_patient_moves_on(self):
        first = self.booked("Moves On", state=Token.CALLED)
        second = self.booked("After", state=Token.WAITING)
        QueueToken.objects.filter(pk=first.pk).update(status=Token.NO_SHOW)

        self.assertEqual(self.call(second).status_code, 200)

    def test_another_doctors_called_patient_does_not_block(self):
        self.booked("Colleague", state=Token.CALLED, doctor=self.colleague)
        mine = self.booked("Mine", state=Token.WAITING)

        self.assertEqual(self.call(mine).status_code, 200)

    def test_call_next_can_re_announce_the_called_patient(self):
        called = self.booked("Again", state=Token.CALLED, number=1)
        self.booked("Later", state=Token.WAITING, number=2)

        response = self.call_next()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["id"], called.pk)


class VisitShowsQueueStatusTests(LifecycleFixture, TestCase):
    """BUG-011: Consultation reads the queue status with the visit, so both screens agree."""

    def setUp(self):
        self.build("vqs")

    def test_the_visit_list_and_detail_carry_the_token_status(self):
        token = self.booked("Called Visit", state=Token.CALLED)
        client = client_for(self.doctor_user, self.hospital)

        rows = client.get(f"/api/encounters/visits/?hospital={self.hospital.pk}").json()
        rows = rows.get("results", rows) if isinstance(rows, dict) else rows
        detail = client.get(f"/api/encounters/visits/{token.visit_id}/").json()

        self.assertEqual([row["queue_status"] for row in rows if row["id"] == token.visit_id], ["Called"])
        self.assertEqual(detail["queue_status"], "Called")
