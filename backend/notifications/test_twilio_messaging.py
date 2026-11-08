"""P1-09: SMS and WhatsApp through Twilio Messaging, and signed delivery receipts (Twilio mocked)."""

from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator

from hospital.models import Hospital
from notifications.models import NotificationDelivery
from notifications.services.providers import (
    NotificationChannel,
    NotificationEvent,
    NotificationPayload,
    SMSProvider,
    WhatsAppProvider,
)
from patients.models import Patient

TWILIO = dict(
    TWILIO_ACCOUNT_SID="ACsynthetic", TWILIO_AUTH_TOKEN="synthetic-token", TWILIO_API_KEY="", TWILIO_API_SECRET="",
    TWILIO_MESSAGING_SERVICE_SID="MGsynthetic", TWILIO_PHONE_NUMBER="", TWILIO_WHATSAPP_FROM="+14155550100",
    TWILIO_WHATSAPP_CONTENT_SID="", TWILIO_STATUS_CALLBACK_URL="https://hms.example.test/api/notifications/twilio/status/",
)
STATUS_URL = "/api/notifications/twilio/status/"


@override_settings(**TWILIO)
class TwilioMessagingTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Messaging Hospital", is_active=True)
        self.patient = Patient.objects.create(name="Synthetic Messaged", age=30, gender="Female",
                                              phone="9876500090", hospital=self.hospital)
        self.client_patch = mock.patch("notifications.services.providers._twilio_client")
        self.twilio = self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.twilio.return_value.messages.create.return_value = mock.Mock(sid="SMsynthetic01")

    def payload(self, patient=None):
        return NotificationPayload(event=NotificationEvent.QUEUE_TOKEN_CREATED, patient_id=(patient or self.patient).pk,
                                   hospital_id=self.hospital.pk, title="Token", message="Your token is 7.")

    def sent(self):
        return self.twilio.return_value.messages.create.call_args.kwargs

    # --- SMS -----------------------------------------------------------------

    def test_sms_goes_to_the_patient_through_the_messaging_service(self):
        result = SMSProvider().send(self.payload())

        self.assertTrue(result.success, result.error)
        self.assertEqual(result.provider_message_id, "SMsynthetic01")
        self.assertEqual(self.sent()["to"], "+919876500090")
        self.assertEqual(self.sent()["messaging_service_sid"], "MGsynthetic")
        self.assertIn("Your token is 7.", self.sent()["body"])
        self.assertEqual(self.sent()["status_callback"], TWILIO["TWILIO_STATUS_CALLBACK_URL"])

    @override_settings(TWILIO_ACCOUNT_SID="")
    def test_sms_without_credentials_is_not_configured_and_sends_nothing(self):
        provider = SMSProvider()

        self.assertFalse(provider.is_configured())
        result = provider.send(self.payload())
        self.assertFalse(result.success)
        self.twilio.return_value.messages.create.assert_not_called()

    def test_patient_without_a_mobile_number_is_not_retried(self):
        patient = Patient.objects.create(name="Synthetic No Phone", age=30, gender="Male", phone="",
                                         hospital=self.hospital)

        result = SMSProvider().send(self.payload(patient))

        self.assertEqual((result.success, result.retryable), (False, False))

    def test_provider_outage_is_retried_but_a_bad_number_is_not(self):
        create = self.twilio.return_value.messages.create
        create.side_effect = TwilioRestException(503, "https://api.twilio.com", msg="Service unavailable")
        self.assertTrue(SMSProvider().send(self.payload()).retryable)

        create.side_effect = TwilioRestException(400, "https://api.twilio.com", msg="Invalid 'To'", code=21211)
        result = SMSProvider().send(self.payload())
        self.assertEqual((result.success, result.retryable), (False, False))
        self.assertNotIn("Your token", result.error or "")

    # --- WhatsApp ------------------------------------------------------------

    def test_whatsapp_uses_the_whatsapp_addresses(self):
        result = WhatsAppProvider().send(self.payload())

        self.assertTrue(result.success, result.error)
        self.assertEqual((self.sent()["to"], self.sent()["from_"]), ("whatsapp:+919876500090", "whatsapp:+14155550100"))

    @override_settings(TWILIO_WHATSAPP_CONTENT_SID="HXsynthetic")
    def test_whatsapp_uses_the_approved_template_when_set(self):
        WhatsAppProvider().send(self.payload())

        self.assertEqual(self.sent()["content_sid"], "HXsynthetic")
        self.assertNotIn("body", self.sent())

    # --- delivery receipts ---------------------------------------------------

    def receipt(self, params, signature=None):
        if signature is None:
            signature = RequestValidator("synthetic-token").compute_signature(TWILIO["TWILIO_STATUS_CALLBACK_URL"], params)
        return APIClient().post(STATUS_URL, params, HTTP_X_TWILIO_SIGNATURE=signature)

    def delivery(self):
        return NotificationDelivery.objects.create(
            hospital=self.hospital, patient=self.patient, event="queue_token_created", channel="sms",
            status=NotificationDelivery.Status.SENT, provider_message_id="SMsynthetic01")

    def test_signed_receipt_marks_the_message_delivered(self):
        delivery = self.delivery()

        response = self.receipt({"MessageSid": "SMsynthetic01", "MessageStatus": "delivered"})

        self.assertEqual(response.status_code, 204)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.DELIVERED)

    def test_failed_receipt_records_the_twilio_error_code(self):
        delivery = self.delivery()

        self.receipt({"MessageSid": "SMsynthetic01", "MessageStatus": "undelivered", "ErrorCode": "30008"})

        delivery.refresh_from_db()
        self.assertEqual((delivery.status, delivery.error), (NotificationDelivery.Status.FAILED, "Twilio error 30008"))

    def test_unsigned_receipt_is_refused_and_changes_nothing(self):
        delivery = self.delivery()

        response = self.receipt({"MessageSid": "SMsynthetic01", "MessageStatus": "delivered"}, signature="forged")

        self.assertEqual(response.status_code, 403)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)

    def test_channel_values_are_unchanged(self):
        self.assertEqual((SMSProvider().channel, WhatsAppProvider().channel),
                         (NotificationChannel.SMS, NotificationChannel.WHATSAPP))
