"""Queued delivery of external notification channels and the Celery retry task."""

from unittest import mock

from celery.exceptions import Retry
from django.test import TestCase, override_settings

from hospital.models import Hospital
from notifications.models import Consent, NotificationDelivery
from notifications.services import (
    NotificationChannel,
    NotificationEvent,
    NotificationPayload,
    NotificationResult,
    get_notification_engine,
)
from notifications.tasks import NOTIFICATION_MAX_RETRIES, send_notification_channel
from patients.models import Patient

EMAIL_SETTINGS = {
    "EMAIL_HOST": "smtp.example.test",
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
}


@override_settings(**EMAIL_SETTINGS)
class AsyncNotificationDeliveryTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.hospital = Hospital.objects.create(name="Synthetic Async", is_active=True)
        login = get_user_model().objects.create_user(
            username="async_patient", email="async.patient@example.test", password="Synthetic-Pass-123",
        )
        self.patient = Patient.objects.create(name="Synthetic Async", age=40, gender="Female",
                                              phone="9000000090", hospital=self.hospital, user=login)
        Consent.objects.create(patient=self.patient, hospital=self.hospital,
                               purpose="notifications_email", granted=True)
        self.engine = get_notification_engine()

    def payload(self, channels):
        return NotificationPayload(
            event=NotificationEvent.PATIENT_CALLED, patient_id=self.patient.id, hospital_id=self.hospital.id,
            title="Your turn", message="Please come to room 4.", channels=channels,
        )

    def run_task(self):
        """Run attempts the way a worker does, returning each retry delay."""
        data = self.payload([NotificationChannel.EMAIL]).to_dict()
        delays = []
        with mock.patch.object(send_notification_channel, "retry",
                               side_effect=lambda countdown: delays.append(countdown) or Retry()):
            for attempt in range(NOTIFICATION_MAX_RETRIES + 2):
                send_notification_channel.push_request(retries=attempt)
                try:
                    send_notification_channel.run(data, "email")
                    return delays
                except Retry:
                    continue
                finally:
                    send_notification_channel.pop_request()
        self.fail("task kept retrying past its limit")

    def statuses(self, channel):
        return list(NotificationDelivery.objects.filter(channel=channel).order_by("id")
                    .values_list("status", flat=True))

    def test_payload_round_trips_through_json_form(self):
        original = self.payload([NotificationChannel.IN_APP, NotificationChannel.EMAIL])
        self.assertEqual(NotificationPayload.from_dict(original.to_dict()), original)

    def test_in_app_is_immediate_and_email_is_queued_until_commit(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            results = self.engine.send_async(self.payload([NotificationChannel.IN_APP, NotificationChannel.EMAIL]))

        self.assertEqual([r.channel for r in results], [NotificationChannel.IN_APP])
        self.assertEqual(self.statuses("in_app"), ["sent"])
        self.assertEqual(self.statuses("email"), [])
        self.assertEqual(len(callbacks), 1)

        for callback in callbacks:
            callback()
        self.assertEqual(self.statuses("email"), ["sent"])

    def test_channel_without_consent_is_skipped_now_and_never_queued(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            results = self.engine.send_async(self.payload([NotificationChannel.SMS]))
        self.assertEqual(results[0].error, "Consent not granted")
        self.assertEqual(self.statuses("sms"), ["skipped"])
        self.assertEqual(callbacks, [])

    def test_transient_failure_is_retried_until_it_succeeds(self):
        with mock.patch("django.core.mail.send_mail", side_effect=[OSError("smtp down"), OSError("smtp down"), 1]):
            delays = self.run_task()
        self.assertEqual(delays, [60, 120])
        self.assertEqual(self.statuses("email"), ["failed", "failed", "sent"])

    def test_retries_stop_after_the_limit(self):
        with mock.patch("django.core.mail.send_mail", side_effect=OSError("smtp down")):
            delays = self.run_task()
        self.assertEqual(len(delays), NOTIFICATION_MAX_RETRIES)
        self.assertEqual(self.statuses("email"), ["failed"] * (NOTIFICATION_MAX_RETRIES + 1))

    def test_permanent_failure_is_not_retried(self):
        failure = NotificationResult(channel=NotificationChannel.EMAIL, success=False, error="bad address")
        with mock.patch.object(self.engine._providers[NotificationChannel.EMAIL], "send", return_value=failure):
            self.assertEqual(self.run_task(), [])
        self.assertEqual(self.statuses("email"), ["failed"])

    def test_broker_outage_falls_back_to_sending_now(self):
        with mock.patch.object(send_notification_channel, "apply_async", side_effect=ConnectionError("no broker")):
            with self.captureOnCommitCallbacks(execute=True):
                self.engine.send_async(self.payload([NotificationChannel.EMAIL]))
        self.assertEqual(self.statuses("email"), ["sent"])
