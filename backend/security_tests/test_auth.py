"""Staff authentication: OTP challenge binding, lockout, policy and password reset.

Twilio Verify is replaced by a fake; no SMS is sent.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from hospital.models import Hospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole
from users.twilio_verify import VerifyResult

User = get_user_model()
PASSWORD = "Synthetic-Pass-123"
VALID_CODE = "123456"


class FakeVerify:
    def __init__(self):
        self.sent = []

    def is_configured(self):
        return True

    def start_verification(self, phone, channel="sms"):
        self.sent.append(phone)
        return VerifyResult(ok=True, message="sent")

    def check_verification(self, phone, code):
        return VerifyResult(ok=code == VALID_CODE, message="ok" if code == VALID_CODE else "Invalid code")


class StaffAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient(raise_request_exception=False)
        hospital = Hospital.objects.create(name="Synthetic Auth Hospital", is_active=True)
        self.user = User.objects.create_user(username="auth_doc", password=PASSWORD, email="auth_doc@example.test")
        profile = StaffProfile.objects.create(
            user=self.user, role=StaffRole.DOCTOR, employee_id="EMP-AUTH", phone="9000000010", is_active_staff=True
        )
        StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=StaffRole.DOCTOR)
        self.fake = FakeVerify()
        patcher = mock.patch("users.views.get_twilio_verify_service", return_value=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def start(self):
        resp = self.client.post(
            "/api/auth/staff/login/otp/start/", {"username": "auth_doc", "password": PASSWORD}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()["challenge"]

    def test_otp_verify_requires_password_challenge(self):
        resp = self.client.post(
            "/api/auth/staff/login/otp/verify/", {"user_id": self.user.id, "otp": VALID_CODE}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("access", resp.json())

    def test_forged_challenge_rejected(self):
        resp = self.client.post(
            "/api/auth/staff/login/otp/verify/", {"challenge": "forged:token", "otp": VALID_CODE}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_resend_requires_challenge(self):
        resp = self.client.post("/api/auth/staff/login/otp/resend/", {"user_id": self.user.id}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.fake.sent, [])

    def test_full_otp_login(self):
        challenge = self.start()
        wrong = self.client.post(
            "/api/auth/staff/login/otp/verify/", {"challenge": challenge, "otp": "000000"}, format="json"
        )
        self.assertEqual(wrong.status_code, 401)
        ok = self.client.post(
            "/api/auth/staff/login/otp/verify/", {"challenge": challenge, "otp": VALID_CODE}, format="json"
        )
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertIn("access", ok.json())

    def test_lockout_after_repeated_failures(self):
        for _ in range(5):
            self.client.post("/api/auth/staff/login/", {"username": "auth_doc", "password": "wrong"}, format="json")
        resp = self.client.post("/api/auth/staff/login/", {"username": "auth_doc", "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 429)

    @override_settings(STAFF_LOGIN_REQUIRE_OTP=True)
    def test_password_only_login_refused_when_otp_required(self):
        resp = self.client.post("/api/auth/staff/login/", {"username": "auth_doc", "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("access", resp.json())

    def test_bare_token_obtain_endpoint_removed(self):
        resp = self.client.post("/api/auth/token/", {"username": "auth_doc", "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_password_reset_does_not_reveal_accounts(self):
        known = self.client.post("/api/auth/password/reset/", {"username": "auth_doc"}, format="json")
        unknown = self.client.post("/api/auth/password/reset/", {"username": "nobody"}, format="json")
        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(self.fake.sent, ["9000000010"])

    def test_password_reset_confirm(self):
        old_refresh = RefreshToken.for_user(self.user)
        bad = self.client.post(
            "/api/auth/password/reset/confirm/",
            {"username": "auth_doc", "code": "999999", "new_password": "Another-Strong-Pass-9"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        weak = self.client.post(
            "/api/auth/password/reset/confirm/",
            {"username": "auth_doc", "code": VALID_CODE, "new_password": "123"},
            format="json",
        )
        self.assertEqual(weak.status_code, 400)
        ok = self.client.post(
            "/api/auth/password/reset/confirm/",
            {"username": "auth_doc", "code": VALID_CODE, "new_password": "Another-Strong-Pass-9"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200, ok.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-Strong-Pass-9"))
        refresh = self.client.post("/api/auth/token/refresh/", {"refresh": str(old_refresh)}, format="json")
        self.assertEqual(refresh.status_code, 401)
