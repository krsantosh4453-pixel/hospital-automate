"""Voice-call fallback when SMS/WhatsApp delivery fails (K8)."""

from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from notifications.models import Consent, NotificationDelivery, VoiceCallFallback
from notifications.services import NotificationChannel, NotificationEvent, send_notification
from notifications.services.engine import NotificationEngine
from notifications.services.providers import NotificationPayload
from notifications.services.voice import (
    NoopVoiceCallProvider, TwilioVoiceCallProvider, VoiceCallProvider, VoiceCallResult,
    get_voice_call_provider, to_e164, twiml_for,
)
from notifications.services.voice_fallback import MAX_ATTEMPTS, place_queued_call
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole


class FakeVoice(VoiceCallProvider):
    name = "fake"

    def __init__(self, results):
        self.results, self.calls = list(results), []

    def place_call(self, to_number, message):
        self.calls.append((to_number, message))
        return self.results.pop(0)


def consent(patient, hospital, purpose, granted=True):
    Consent.objects.create(patient=patient, hospital=hospital, purpose=purpose, granted=granted)


class VoiceFallbackQueueTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Voice Hospital", is_active=True)
        self.patient = Patient.objects.create(name="Synthetic Caller", age=50, gender="Female",
                                              phone="9000000101", hospital=self.hospital)
        consent(self.patient, self.hospital, "notifications_sms")
        consent(self.patient, self.hospital, "notifications_voice")

    def notify(self, channels=(NotificationChannel.SMS,)):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            send_notification(NotificationEvent.PATIENT_CALLED, self.patient.id, self.hospital.id,
                              "Your token is being called", "Room 4, Dr Synthetic (cardiology review)",
                              channels=list(channels))
        return callbacks

    def test_failed_sms_queues_a_voice_call_without_clinical_details(self):
        callbacks = self.notify()  # SMS provider is not configured in tests, so SMS fails
        row = VoiceCallFallback.objects.get()
        self.assertEqual(row.status, VoiceCallFallback.Status.QUEUED)
        self.assertIn("Your token is being called", row.message)
        self.assertIn("Synthetic Voice Hospital", row.message)
        self.assertNotIn("cardiology", row.message)
        self.assertIn("sms:", row.reason)
        self.assertEqual(len(callbacks), 1)

    def test_no_call_when_patient_opted_out_of_sms_or_voice(self):
        consent(self.patient, self.hospital, "notifications_sms", granted=False)
        self.notify()
        self.assertFalse(VoiceCallFallback.objects.exists())

        consent(self.patient, self.hospital, "notifications_sms", granted=True)
        consent(self.patient, self.hospital, "notifications_voice", granted=False)
        self.notify()
        row = VoiceCallFallback.objects.get()
        self.assertEqual((row.status, row.error), (VoiceCallFallback.Status.SKIPPED, "No consent for voice calls"))

    def test_no_call_when_sms_succeeded_or_voice_already_tried(self):
        engine = NotificationEngine()
        payload = NotificationPayload(NotificationEvent.PATIENT_CALLED, self.patient.id, self.hospital.id, "T", "M",
                                      channels=[NotificationChannel.SMS])
        from notifications.services.providers import NotificationResult
        from notifications.services.voice_fallback import queue_voice_fallback

        ok = [NotificationResult(channel=NotificationChannel.SMS, success=True)]
        self.assertIsNone(queue_voice_fallback(engine, payload, ok))
        self.notify(channels=(NotificationChannel.SMS, NotificationChannel.VOICE))
        self.assertFalse(VoiceCallFallback.objects.exists())

    def test_in_app_only_notifications_never_call(self):
        self.notify(channels=(NotificationChannel.IN_APP,))
        self.assertFalse(VoiceCallFallback.objects.exists())


class PlaceVoiceCallTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Dial Hospital", is_active=True)
        self.patient = Patient.objects.create(name="Synthetic Dialled", age=40, gender="Male",
                                              phone="9000000102", hospital=self.hospital)
        self.row = VoiceCallFallback.objects.create(hospital=self.hospital, patient=self.patient,
                                                    event="patient_called", message="Hello")

    def test_noop_provider_skips_and_records(self):
        self.assertFalse(place_queued_call(self.row.pk, provider=NoopVoiceCallProvider()))
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.provider), (VoiceCallFallback.Status.SKIPPED, "noop"))
        self.assertEqual(NotificationDelivery.objects.get().status, NotificationDelivery.Status.SKIPPED)

    def test_success_marks_placed(self):
        provider = FakeVoice([VoiceCallResult(success=True, call_id="CA123")])
        self.assertFalse(place_queued_call(self.row.pk, provider=provider))
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.provider_call_id), (VoiceCallFallback.Status.PLACED, "CA123"))
        self.assertEqual(provider.calls, [("+919000000102", "Hello")])
        delivery = NotificationDelivery.objects.get()
        self.assertEqual((delivery.channel, delivery.status), ("voice", NotificationDelivery.Status.SENT))
        # A placed call is not dialled again.
        self.assertFalse(place_queued_call(self.row.pk, provider=provider))

    def test_retries_then_fails(self):
        provider = FakeVoice([VoiceCallResult(success=False, error="busy")] * MAX_ATTEMPTS)
        retries = [place_queued_call(self.row.pk, provider=provider) for _ in range(MAX_ATTEMPTS)]
        self.assertEqual(retries, [True] * (MAX_ATTEMPTS - 1) + [False])
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.attempts), (VoiceCallFallback.Status.FAILED, MAX_ATTEMPTS))

    def test_celery_task_uses_configured_provider(self):
        from notifications.tasks import place_voice_call

        with mock.patch("notifications.services.voice_fallback.get_voice_call_provider",
                        return_value=FakeVoice([VoiceCallResult(success=True, call_id="CA9")])):
            place_voice_call(self.row.pk)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, VoiceCallFallback.Status.PLACED)


class VoiceProviderConfigTests(TestCase):
    def test_default_is_noop(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsInstance(get_voice_call_provider(), NoopVoiceCallProvider)

    def test_twilio_needs_credentials(self):
        with mock.patch.dict("os.environ", {"VOICE_CALL_PROVIDER": "twilio"}, clear=True):
            self.assertIsInstance(get_voice_call_provider(), NoopVoiceCallProvider)
        env = {"VOICE_CALL_PROVIDER": "twilio", "TWILIO_ACCOUNT_SID": "ACsynthetic",
               "TWILIO_AUTH_TOKEN": "synthetic", "TWILIO_VOICE_FROM_NUMBER": "+15005550006"}
        with mock.patch.dict("os.environ", env, clear=True):
            self.assertIsInstance(get_voice_call_provider(), TwilioVoiceCallProvider)

    def test_twilio_places_call_with_escaped_twiml(self):
        provider = TwilioVoiceCallProvider("ACsynthetic", "synthetic", "+15005550006")
        client = mock.Mock()
        client.calls.create.return_value = mock.Mock(sid="CAsynthetic")
        provider._client = client
        result = provider.place_call("+919000000103", "Dr A & B <ward>")
        self.assertEqual(result, VoiceCallResult(success=True, call_id="CAsynthetic"))
        kwargs = client.calls.create.call_args.kwargs
        self.assertEqual((kwargs["to"], kwargs["from_"]), ("+919000000103", "+15005550006"))
        self.assertIn("Dr A &amp; B &lt;ward&gt;", kwargs["twiml"])
        client.calls.create.side_effect = RuntimeError("auth")
        self.assertFalse(provider.place_call("+919000000103", "x").success)

    def test_phone_normalisation_and_twiml(self):
        self.assertEqual(to_e164("90000 00104"), "+919000000104")
        self.assertEqual(to_e164("+1 415 555 0100"), "+14155550100")
        self.assertEqual(to_e164("123"), "")
        self.assertTrue(twiml_for("Hi").startswith("<Response><Say"))


class VoiceCallApiTests(TestCase):
    def test_staff_list_is_hospital_scoped(self):
        a = Hospital.objects.create(name="Synthetic Voice A", is_active=True)
        b = Hospital.objects.create(name="Synthetic Voice B", is_active=True)
        patient = Patient.objects.create(name="Synthetic", age=30, gender="Male", phone="9000000105", hospital=a)
        VoiceCallFallback.objects.create(hospital=a, patient=patient, event="patient_called", message="Hello")
        VoiceCallFallback.objects.create(hospital=b, patient=patient, event="patient_called", message="Hello")
        reception, _ = make_staff("voice_rec", a, role=StaffRole.RECEPTIONIST)
        client = APIClient()
        client.force_authenticate(reception)
        resp = client.get("/api/notifications/voice-calls/", HTTP_X_HOSPITAL_ID=str(a.id))
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        rows = body["results"] if isinstance(body, dict) else body
        self.assertEqual([r["hospital"] for r in rows], [a.id])
        doctor, _ = make_staff("voice_doc", a, role=StaffRole.DOCTOR)
        client.force_authenticate(doctor)
        self.assertEqual(client.get("/api/notifications/voice-calls/", HTTP_X_HOSPITAL_ID=str(a.id)).status_code, 403)


class QueuedTextFailureTests(TestCase):
    """SMS/WhatsApp go through Celery with retries; the call follows the final failure only."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Retry Hospital", is_active=True)
        self.patient = Patient.objects.create(name="Synthetic Retried", age=60, gender="Male",
                                              phone="9000000103", hospital=self.hospital)
        consent(self.patient, self.hospital, "notifications_voice")
        self.payload = NotificationPayload(NotificationEvent.PATIENT_CALLED, self.patient.id, self.hospital.id,
                                           "Your token is being called", "Room 4", channels=[NotificationChannel.SMS])

    def run_task(self, result, retries=0):
        from notifications.tasks import send_notification_channel

        engine = mock.Mock(send_channel=mock.Mock(return_value=result), check_consent=mock.Mock(return_value=True))
        with mock.patch("notifications.services.get_notification_engine", return_value=engine):
            task = send_notification_channel
            task.push_request(retries=retries)
            try:
                return task.run(self.payload.to_dict(), "sms")
            finally:
                task.pop_request()

    def test_a_retryable_failure_with_retries_left_does_not_call_yet(self):
        from celery.exceptions import Retry
        from notifications.services.providers import NotificationResult

        with self.assertRaises(Retry):
            self.run_task(NotificationResult(channel=NotificationChannel.SMS, success=False, error="timeout",
                                             retryable=True))
        self.assertFalse(VoiceCallFallback.objects.exists())

    def test_final_failure_queues_one_call_even_if_whatsapp_fails_too(self):
        from notifications.services.providers import NotificationResult
        from notifications.tasks import NOTIFICATION_MAX_RETRIES

        failed = NotificationResult(channel=NotificationChannel.SMS, success=False, error="timeout", retryable=True)
        self.assertFalse(self.run_task(failed, retries=NOTIFICATION_MAX_RETRIES))
        self.run_task(NotificationResult(channel=NotificationChannel.WHATSAPP, success=False, error="rejected"))
        row = VoiceCallFallback.objects.get()
        self.assertEqual(row.status, VoiceCallFallback.Status.QUEUED)
        self.assertIn("sms: timeout", row.reason)

    def test_call_is_skipped_if_the_patient_was_reached_meanwhile(self):
        row = VoiceCallFallback.objects.create(hospital=self.hospital, patient=self.patient,
                                               event="patient_called", message="Hello")
        NotificationDelivery.objects.create(hospital=self.hospital, patient=self.patient, event="patient_called",
                                            channel="whatsapp", status=NotificationDelivery.Status.SENT)
        provider = FakeVoice([VoiceCallResult(success=True, call_id="CA1")])
        self.assertFalse(place_queued_call(row.pk, provider=provider))
        row.refresh_from_db()
        self.assertEqual(row.status, VoiceCallFallback.Status.SKIPPED)
        self.assertEqual(provider.calls, [])

    def test_retryable_attempt_through_the_real_engine_does_not_call(self):
        from notifications.services.providers import NotificationResult

        engine = NotificationEngine()
        flaky = mock.Mock(is_configured=mock.Mock(return_value=True),
                          send=mock.Mock(return_value=NotificationResult(channel=NotificationChannel.SMS, success=False,
                                                                         error="timeout", retryable=True)))
        engine._providers[NotificationChannel.SMS] = flaky
        consent(self.patient, self.hospital, "notifications_sms")
        engine.send_channel(self.payload, NotificationChannel.SMS)
        self.assertFalse(VoiceCallFallback.objects.exists())
