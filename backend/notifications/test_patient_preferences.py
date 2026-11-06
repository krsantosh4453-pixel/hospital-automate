"""K7: a patient sets how their hospital may contact them, and only for themselves (synthetic data)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Hospital
from notifications.models import Consent
from notifications.services import NotificationChannel, NotificationEvent
from notifications.services.engine import NotificationEngine
from patients.models import Patient, PatientHospital

URL = "/api/notifications/consents/"


class PatientPreferenceTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Prefs", is_active=True)
        self.login = get_user_model().objects.create_user(username="pref_patient", password="x")
        self.patient = Patient.objects.create(name="Synthetic Chooser", age=30, gender="Female", phone="9000002001",
                                              hospital=self.hospital, user=self.login)
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="PR-1")
        self.stranger = Patient.objects.create(name="Synthetic Stranger", age=31, gender="Male", phone="9000002002",
                                               hospital=self.hospital)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.login)

    def choose(self, verb, channel, **extra):
        return self.client.post(f"{URL}{verb}/", {"hospital": self.hospital.id, "purpose": f"notifications_{channel}",
                                                  **extra}, format="json")

    def test_newest_choice_is_what_the_engine_honours(self):
        self.assertEqual(self.choose("grant", "sms").status_code, 201)
        self.assertTrue(NotificationEngine().check_consent(self.patient.id, NotificationEvent.PATIENT_CALLED,
                                                           NotificationChannel.SMS, self.hospital.id))
        self.assertEqual(self.choose("revoke", "sms").status_code, 201)
        self.assertFalse(NotificationEngine().check_consent(self.patient.id, NotificationEvent.PATIENT_CALLED,
                                                            NotificationChannel.SMS, self.hospital.id))
        listed = self.client.get(f"{URL}?hospital={self.hospital.id}").json()
        self.assertEqual([r["granted"] for r in listed.get("results", listed)], [False, True])

    def test_a_patient_cannot_choose_for_someone_else(self):
        self.assertEqual(self.choose("grant", "whatsapp", patient=self.stranger.id).status_code, 201)
        self.assertFalse(Consent.objects.filter(patient=self.stranger).exists())
        self.assertTrue(Consent.objects.filter(patient=self.patient, purpose="notifications_whatsapp").exists())
