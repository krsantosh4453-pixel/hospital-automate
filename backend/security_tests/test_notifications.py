"""Communication consent, delivery records and notification failure isolation."""

import datetime
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from appointments.models import Appointment
from doctors.models import Doctor
from encounters.models import QueueToken
from hospital.models import Hospital
from notifications.models import NotificationDelivery
from notifications.services import NotificationChannel, NotificationEvent, NotificationPayload, get_notification_engine
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

User = get_user_model()


class CommunicationConsentTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Notify", is_active=True)
        self.reception, _ = make_staff("notify_reception", self.hospital, role=StaffRole.RECEPTIONIST)
        self.login = User.objects.create_user(username="notify_patient", password="Synthetic-Pass-123")
        self.patient = Patient.objects.create(name="Synthetic Notified", age=30, gender="Male",
                                              phone="9000000070", hospital=self.hospital, user=self.login)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="N-1")

    def patient_api(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.login)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def send_sms(self):
        return get_notification_engine().send(NotificationPayload(
            event=NotificationEvent.QUEUE_TOKEN_CREATED, patient_id=self.patient.id, hospital_id=self.hospital.id,
            title="Token", message="Your token is coming soon.", channels=[NotificationChannel.SMS],
        ))

    def test_opt_in_then_opt_out_is_honoured_and_logged(self):
        self.send_sms()
        self.assertEqual(NotificationDelivery.objects.latest("id").error, "Consent not granted")

        api = self.patient_api()
        self.assertEqual(api.post("/api/notifications/consents/grant/", {"purpose": "notifications_sms"}, format="json").status_code, 201)
        self.assertTrue(api.get("/api/notifications/consents/check/?purpose=notifications_sms").json()["granted"])
        self.assertTrue(get_notification_engine().check_consent(
            self.patient.id, NotificationEvent.QUEUE_TOKEN_CREATED, NotificationChannel.SMS, self.hospital.id))

        self.assertEqual(api.post("/api/notifications/consents/revoke/", {"purpose": "notifications_sms"}, format="json").status_code, 201)
        self.assertFalse(get_notification_engine().check_consent(
            self.patient.id, NotificationEvent.QUEUE_TOKEN_CREATED, NotificationChannel.SMS, self.hospital.id))
        self.send_sms()
        self.assertEqual(NotificationDelivery.objects.latest("id").status, "skipped")

    def test_queue_event_records_in_app_delivery(self):
        doctor = Doctor.objects.create(hospital=self.hospital, name="Dr Notify", specialization="GP", phone="9000000071")
        appt = Appointment.objects.create(patient=self.patient, doctor=doctor, hospital=self.hospital,
                                          appointment_date=datetime.date.today(), appointment_time=datetime.time(9, 0))
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.reception)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        resp = client.post("/api/encounters/queue-tokens/issue/", {"appointment": appt.id}, format="json")
        self.assertIn(resp.status_code, (200, 201), resp.content)
        self.assertTrue(QueueToken.objects.filter(patient=self.patient).exists())
        delivery = NotificationDelivery.objects.get(channel="in_app")
        self.assertEqual(delivery.status, "sent")
        # Other channels were attempted but skipped: the patient never opted in.
        others = NotificationDelivery.objects.exclude(pk=delivery.pk)
        self.assertTrue(others.exists())
        self.assertEqual(set(others.values_list("status", flat=True)), {"skipped"})
        listing = client.get("/api/notifications/deliveries/").json()
        rows = listing.get("results", listing)
        self.assertEqual(len(rows), NotificationDelivery.objects.count())

    def test_lab_sub_resources_are_routable(self):
        lab, _ = make_staff("notify_lab", self.hospital, role=StaffRole.LAB_STAFF)
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(lab)
        for url in ("/api/laboratory/", "/api/laboratory/sample-collections/", "/api/laboratory/lab-results/",
                    "/api/laboratory/sample-dispatches/", "/api/laboratory/result-verifications/"):
            self.assertEqual(client.get(url).status_code, 200, url)


class ProviderHonestyTests(TestCase):
    """A channel may only be recorded as sent when something was really sent."""

    def setUp(self):
        from notifications.models import Consent

        self.hospital = Hospital.objects.create(name="Synthetic Providers", is_active=True)
        self.login = User.objects.create_user(
            username="provider_patient", email="provider.patient@example.test", password="Synthetic-Pass-123",
        )
        self.patient = Patient.objects.create(name="Synthetic Provider", age=30, gender="Male",
                                              phone="9000000080", hospital=self.hospital, user=self.login)
        for channel in ("sms", "whatsapp", "voice", "email"):
            Consent.objects.create(patient=self.patient, hospital=self.hospital,
                                   purpose=f"notifications_{channel}", granted=True)

    def send(self, channel, message="Synthetic body 4471"):
        return get_notification_engine().send(NotificationPayload(
            event=NotificationEvent.PATIENT_CALLED, patient_id=self.patient.id, hospital_id=self.hospital.id,
            title="Your turn", message=message, channels=[channel],
        ))

    def test_unimplemented_channels_never_report_success_or_log_the_message(self):
        env = {
            "SMS_PROVIDER_ACCOUNT_SID": "AC-synthetic", "SMS_PROVIDER_AUTH_TOKEN": "synthetic",
            "WHATSAPP_PROVIDER_ACCOUNT_SID": "AC-synthetic", "WHATSAPP_PROVIDER_AUTH_TOKEN": "synthetic",
            "VOICE_PROVIDER_ACCOUNT_SID": "AC-synthetic", "VOICE_PROVIDER_AUTH_TOKEN": "synthetic",
        }
        with mock.patch.dict(os.environ, env):
            for channel in (NotificationChannel.SMS, NotificationChannel.WHATSAPP, NotificationChannel.VOICE):
                with self.assertLogs("notifications", level="DEBUG") as logs:
                    [result] = self.send(channel)
                self.assertFalse(result.success, channel)
                self.assertNotIn("Synthetic body 4471", "\n".join(logs.output))
        self.assertFalse(NotificationDelivery.objects.filter(status="sent").exists())

    @override_settings(EMAIL_HOST="smtp.example.test",
                       EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_is_really_sent_to_the_patient_address(self):
        [result] = self.send(NotificationChannel.EMAIL)
        self.assertTrue(result.success, result.error)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["provider.patient@example.test"])
        self.assertIn("Synthetic body 4471", mail.outbox[0].body)
        self.assertEqual(NotificationDelivery.objects.get(channel="email").status, "sent")

    @override_settings(EMAIL_HOST="smtp.example.test",
                       EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_without_an_address_fails(self):
        self.login.email = ""
        self.login.save(update_fields=["email"])
        [result] = self.send(NotificationChannel.EMAIL)
        self.assertFalse(result.success)
        self.assertEqual(mail.outbox, [])
