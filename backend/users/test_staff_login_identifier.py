"""Staff sign in with the username or email as typed on any keyboard.

The sign-in forms (web and mobile) ask for "Username or email". Phone
keyboards capitalise the first letter or add a trailing space after a
suggestion, so the identifier must match regardless of letter case and
surrounding spaces, and an email address must work as well as the username.
"""

from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from hospital.models import Hospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
LOGIN_URL = "/api/auth/staff/login/"
PASSWORD = "doctorpass123"


@override_settings(STAFF_LOGIN_REQUIRE_OTP=False)
class StaffLoginIdentifierTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        hospital = Hospital.objects.create(name="City Hospital", is_active=True)
        self.user = User.objects.create_user(
            username="dr.test", email="Dr.Test@Example.com", password=PASSWORD
        )
        profile = StaffProfile.objects.create(
            user=self.user, role=StaffRole.DOCTOR, employee_id="EMP-1", is_active_staff=True
        )
        StaffHospitalMembership.objects.create(
            staff=profile, hospital=hospital, role=StaffRole.DOCTOR, is_active=True
        )

    def login(self, identifier, password=PASSWORD):
        return self.client.post(
            LOGIN_URL, {"username": identifier, "password": password}, format="json"
        )

    def test_exact_username_signs_in(self):
        self.assertEqual(self.login("dr.test").status_code, status.HTTP_200_OK)

    def test_username_in_other_letter_case_signs_in(self):
        for typed in ("Dr.test", "DR.TEST", "Dr.Test"):
            with self.subTest(typed=typed):
                self.assertEqual(self.login(typed).status_code, status.HTTP_200_OK)

    def test_username_with_surrounding_spaces_signs_in(self):
        self.assertEqual(self.login("  dr.test ").status_code, status.HTTP_200_OK)

    def test_email_in_any_case_signs_in(self):
        for typed in ("Dr.Test@Example.com", "dr.test@example.com ", "DR.TEST@EXAMPLE.COM"):
            with self.subTest(typed=typed):
                self.assertEqual(self.login(typed).status_code, status.HTTP_200_OK)

    def test_wrong_password_is_still_rejected(self):
        response = self.login("Dr.Test", password="wrong-password")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_identifier_is_rejected(self):
        response = self.login("nobody@example.com")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UsernameOrEmailBackendTests(TestCase):
    def test_exact_username_wins_over_a_case_variant(self):
        exact = User.objects.create_user(username="Sam", password="pass-one-123")
        User.objects.create_user(username="sam", password="pass-two-123")
        self.assertEqual(authenticate(username="Sam", password="pass-one-123"), exact)

    def test_ambiguous_case_variant_is_rejected(self):
        User.objects.create_user(username="Sam", password="same-pass-123")
        User.objects.create_user(username="sam", password="same-pass-123")
        self.assertIsNone(authenticate(username="SAM", password="same-pass-123"))

    def test_shared_email_is_rejected(self):
        User.objects.create_user(username="a1", email="shared@example.com", password="same-pass-123")
        User.objects.create_user(username="a2", email="shared@example.com", password="same-pass-123")
        self.assertIsNone(authenticate(username="shared@example.com", password="same-pass-123"))

    def test_inactive_user_is_rejected(self):
        User.objects.create_user(username="gone", password="gone-pass-123", is_active=False)
        self.assertIsNone(authenticate(username="Gone", password="gone-pass-123"))

    def test_missing_identifier_or_password_is_rejected(self):
        User.objects.create_user(username="someone", password="some-pass-123")
        self.assertIsNone(authenticate(username="   ", password="some-pass-123"))
        self.assertIsNone(authenticate(username="someone", password=None))


class StaffLoginOptionsTests(TestCase):
    """Final E2E finding 5: the app called otp/start on every login and got 400/503 first."""

    OPTIONS_URL = "/api/auth/staff/login/options/"
    setUp = StaffLoginIdentifierTests.setUp
    login = StaffLoginIdentifierTests.login

    @override_settings(STAFF_LOGIN_REQUIRE_OTP=False, OTP_PROVIDER="console")
    def test_otp_off_says_so_and_password_login_works(self):
        options = self.client.get(self.OPTIONS_URL)
        self.assertEqual(options.status_code, 200)
        self.assertEqual(options.json(), {"otp_required": False, "otp_available": False})
        self.assertEqual(self.login("dr.test").status_code, status.HTTP_200_OK)
        self.assertEqual(self.login("dr.test", "wrong-password").status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(STAFF_LOGIN_REQUIRE_OTP=True, OTP_PROVIDER="console")
    def test_otp_required_is_reported_and_still_enforced(self):
        self.assertTrue(self.client.get(self.OPTIONS_URL).json()["otp_required"])
        refused = self.login("dr.test")
        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("access", refused.json())

    def test_options_reveal_nothing_else(self):
        self.assertEqual(set(self.client.get(self.OPTIONS_URL).json()), {"otp_required", "otp_available"})
