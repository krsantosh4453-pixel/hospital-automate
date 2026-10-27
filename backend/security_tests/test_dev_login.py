"""The temporary shared development sign-in (users/dev_login.py)."""

from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.dev_login import DEV_ACCOUNTS

URL = "/api/auth/dev/login/"
DEV_SETTINGS = {
    "DEBUG": True,
    "DEV_LOGIN_ENABLED": True,
    "DEV_LOGIN_MOBILE": "9000000000",
    "DEV_LOGIN_EMAIL": "dev@example.test",
    "DEV_LOGIN_PASSWORD": "dev-pass-1",
}


@override_settings(**DEV_SETTINGS)
class DevLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with override_settings(DEBUG=True):
            call_command("seed_demo", password="Demo-Check-2026", stdout=StringIO())

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def post(self, identifier="9000000000", password="dev-pass-1", role="Doctor"):
        return self.client.post(URL, {"identifier": identifier, "password": password, "role": role}, format="json")

    def test_lists_every_role_including_patient(self):
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["roles"], list(DEV_ACCOUNTS))
        self.assertIn("Patient", resp.json()["roles"])

    def test_mobile_with_country_code_opens_the_chosen_staff_role(self):
        resp = self.post(identifier="+91 90000 00000", role="Nurse")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["account_type"], "staff")
        self.assertEqual(resp.json()["roles"], ["Nurse"])

    def test_email_opens_every_role(self):
        for role, username in DEV_ACCOUNTS.items():
            resp = self.post(identifier="DEV@example.test", role=role)
            self.assertEqual(resp.status_code, 200, f"{role}: {resp.content}")
            self.assertEqual(resp.json()["user"]["username"], username)
            expected = "patient" if role == "Patient" else "staff"
            self.assertEqual(resp.json()["account_type"], expected, role)

    def test_wrong_password_or_identifier_is_refused(self):
        self.assertEqual(self.post(password="123456").status_code, 401)
        self.assertEqual(self.post(identifier="9111111111").status_code, 401)
        self.assertEqual(self.post(identifier="other@example.test").status_code, 401)

    def test_unknown_role_is_refused(self):
        self.assertEqual(self.post(role="Superuser").status_code, 400)

    def test_repeated_failures_lock_the_sign_in(self):
        for _ in range(10):
            self.post(password="wrong")
        self.assertEqual(self.post().status_code, 429)


class DevLoginDisabledTests(TestCase):
    def test_off_without_debug(self):
        with override_settings(**{**DEV_SETTINGS, "DEBUG": False}):
            self.assertEqual(APIClient().get(URL).status_code, 404)
            self.assertEqual(APIClient().post(URL, {}, format="json").status_code, 404)

    def test_off_when_not_enabled(self):
        with override_settings(**{**DEV_SETTINGS, "DEV_LOGIN_ENABLED": False}):
            self.assertEqual(APIClient().get(URL).status_code, 404)

    def test_off_without_a_password(self):
        with override_settings(**{**DEV_SETTINGS, "DEV_LOGIN_PASSWORD": ""}):
            self.assertEqual(APIClient().get(URL).status_code, 404)
