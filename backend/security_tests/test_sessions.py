"""Phase 3 sessions: one DeviceSession per sign-in, revocable at once, refresh reuse treated as theft.

Twilio Verify is replaced by the fake from test_auth; no SMS is sent and no real
Twilio credentials are used (they have never been exercised, see KNOWN_LIMITATIONS L2).
"""

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from hospital.models import Hospital
from users.models import DeviceSession, StaffHospitalMembership, StaffProfile, StaffRole

from .test_auth import PASSWORD, VALID_CODE, FakeVerify

User = get_user_model()
ME = "/api/auth/staff/me/"


@override_settings(STAFF_LOGIN_REQUIRE_OTP=False)
class SessionLifecycleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.hospital = Hospital.objects.create(name="Synthetic Session Hospital", is_active=True)
        self.user = User.objects.create_user(username="session_doc", password=PASSWORD)
        self.profile = StaffProfile.objects.create(user=self.user, role=StaffRole.DOCTOR, employee_id="EMP-SESS",
                                                   phone="9000000020", is_active_staff=True)
        self.membership = StaffHospitalMembership.objects.create(staff=self.profile, hospital=self.hospital,
                                                                 role=StaffRole.DOCTOR)

    def sign_in(self, **device):
        response = APIClient().post("/api/v1/auth/staff/login/",
                                    {"username": "session_doc", "password": PASSWORD, **device}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def client_with(self, access):
        client = APIClient(raise_request_exception=False)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client

    def refresh(self, token):
        return APIClient(raise_request_exception=False).post("/api/v1/auth/token/refresh/", {"refresh": token},
                                                             format="json")

    # Tokens ----------------------------------------------------------------

    def test_tokens_name_their_session_and_carry_no_role_claims(self):
        tokens = self.sign_in(device_id="phone-1", platform="android", app_version="1.0.0")

        access = AccessToken(tokens["access"])
        session = DeviceSession.objects.get(pk=access["sid"])
        self.assertEqual((session.user, session.platform, session.device_id), (self.user, "android", "phone-1"))
        for claim in ("roles", "hospitals", "staff_role"):
            self.assertNotIn(claim, access.payload)

    def test_a_refreshed_access_token_keeps_its_session(self):
        tokens = self.sign_in()
        refreshed = self.refresh(tokens["refresh"])

        self.assertEqual(refreshed.status_code, 200, refreshed.content)
        self.assertEqual(AccessToken(refreshed.json()["access"])["sid"], AccessToken(tokens["access"])["sid"])

    # Revocation ------------------------------------------------------------

    def test_revoking_a_session_stops_its_access_token_at_once(self):
        phone, laptop = self.sign_in(device_id="phone"), self.sign_in(device_id="laptop")
        phone_sid = AccessToken(phone["access"])["sid"]

        revoked = self.client_with(laptop["access"]).post(f"/api/v1/auth/sessions/{phone_sid}/revoke/")

        self.assertEqual(revoked.status_code, 200, revoked.content)
        self.assertEqual(self.client_with(phone["access"]).get(ME).status_code, 401)
        self.assertEqual(self.refresh(phone["refresh"]).status_code, 401)
        self.assertEqual(self.client_with(laptop["access"]).get(ME).status_code, 200)

    def test_sessions_list_shows_own_active_sessions_and_marks_the_current_one(self):
        self.sign_in(device_id="phone")
        second = self.sign_in(device_id="laptop")

        rows = self.client_with(second["access"]).get("/api/v1/auth/sessions/").json()["sessions"]

        self.assertEqual({row["device_id"] for row in rows}, {"phone", "laptop"})
        self.assertEqual([row["device_id"] for row in rows if row["current"]], ["laptop"])
        self.assertNotIn("current_jti", rows[0])

    def test_logout_all_signs_out_every_device(self):
        phone, laptop = self.sign_in(), self.sign_in()

        self.assertEqual(self.client_with(phone["access"]).post("/api/v1/auth/logout-all/").status_code, 200)

        for tokens in (phone, laptop):
            self.assertEqual(self.client_with(tokens["access"]).get(ME).status_code, 401)
            self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)
        self.assertEqual(self.client_with(self.sign_in()["access"]).get(ME).status_code, 200)

    def test_logout_revokes_its_session(self):
        tokens = self.sign_in()
        APIClient().post("/api/v1/auth/staff/logout/", {"refresh": tokens["refresh"]}, format="json")

        self.assertEqual(self.client_with(tokens["access"]).get(ME).status_code, 401)

    def test_nobody_can_revoke_or_see_another_users_session(self):
        mine = self.sign_in()
        other = User.objects.create_user(username="session_other", password=PASSWORD)
        other_session = DeviceSession.objects.create(user=other, account_type="staff")

        client = self.client_with(mine["access"])
        self.assertEqual(client.post(f"/api/v1/auth/sessions/{other_session.pk}/revoke/").status_code, 404)
        listed = {row["id"] for row in client.get("/api/v1/auth/sessions/").json()["sessions"]}
        self.assertNotIn(str(other_session.pk), listed)
        other_session.refresh_from_db()
        self.assertIsNone(other_session.revoked_at)

    def test_deactivated_staff_cannot_refresh(self):
        tokens = self.sign_in()
        StaffProfile.objects.filter(pk=self.profile.pk).update(is_active_staff=False)

        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

    def test_removing_the_last_membership_revokes_sessions(self):
        tokens = self.sign_in()
        admin = User.objects.create_user(username="session_admin", password=PASSWORD)
        admin_profile = StaffProfile.objects.create(user=admin, role=StaffRole.ADMIN, employee_id="EMP-SADM",
                                                    is_active_staff=True)
        StaffHospitalMembership.objects.create(staff=admin_profile, hospital=self.hospital, role=StaffRole.ADMIN)
        client = APIClient()
        client.force_authenticate(admin)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

        response = client.patch(f"/api/users/{self.user.id}/membership/", {"is_active": False}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)
        self.assertTrue(DeviceSession.objects.filter(user=self.user, revoked_at__isnull=False).exists())

    # Refresh-token reuse ---------------------------------------------------

    def test_reusing_a_rotated_refresh_token_revokes_the_session(self):
        tokens = self.sign_in()
        newer = self.refresh(tokens["refresh"]).json()
        # Old enough that it cannot be two tabs refreshing at the same moment.
        BlacklistedToken.objects.update(blacklisted_at=timezone.now() - timedelta(minutes=5))

        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

        self.assertEqual(self.refresh(newer["refresh"]).status_code, 401)
        self.assertEqual(self.client_with(newer["access"]).get(ME).status_code, 401)
        session = DeviceSession.objects.get(pk=AccessToken(tokens["access"])["sid"])
        self.assertTrue(session.revoked_reason.startswith("refresh token reused"))

    def test_two_tabs_refreshing_at_once_do_not_sign_the_user_out(self):
        tokens = self.sign_in()
        newer = self.refresh(tokens["refresh"]).json()

        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)  # the slower tab

        self.assertEqual(self.refresh(newer["refresh"]).status_code, 200)

    def test_a_second_refresh_chain_from_one_token_is_refused_without_signing_out(self):
        # Two refreshes with the same token that both slipped past the blacklist
        # (parallel requests): the session follows the first one only.
        tokens = self.sign_in()
        newer = self.refresh(tokens["refresh"]).json()
        BlacklistedToken.objects.all().delete()

        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

        self.assertEqual(self.refresh(newer["refresh"]).status_code, 200)

    def test_logout_with_an_already_rotated_token_still_signs_the_device_out(self):
        tokens = self.sign_in()
        newer = self.refresh(tokens["refresh"]).json()

        APIClient().post("/api/v1/auth/staff/logout/", {"refresh": tokens["refresh"]}, format="json")

        self.assertEqual(self.client_with(newer["access"]).get(ME).status_code, 401)
        self.assertEqual(self.refresh(newer["refresh"]).status_code, 401)

    def test_refreshing_a_signed_out_browser_session_clears_its_cookies(self):
        tokens = self.sign_in()
        sid = AccessToken(tokens["access"])["sid"]
        DeviceSession.objects.filter(pk=sid).update(revoked_at=timezone.now())
        cache.clear()
        client = APIClient(raise_request_exception=False)
        client.cookies["hms_refresh"] = tokens["refresh"]

        response = client.post("/api/v1/auth/token/refresh/", {}, format="json", HTTP_X_AUTH_MODE="cookie")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.cookies["hms_refresh"].value, "")

    def test_a_slower_tab_refreshing_does_not_clear_the_cookies_another_tab_just_set(self):
        tokens = self.sign_in()
        self.refresh(tokens["refresh"])  # the faster tab rotated the token
        client = APIClient(raise_request_exception=False)
        client.cookies["hms_refresh"] = tokens["refresh"]

        response = client.post("/api/v1/auth/token/refresh/", {}, format="json", HTTP_X_AUTH_MODE="cookie")

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("hms_refresh", response.cookies)

    def test_a_revoked_family_access_grant_cannot_refresh(self):
        from patients.models import Patient, ProxyAccess
        from users.proxy_access import issue_proxy_tokens, proxy_user_for

        patient = Patient.objects.create(name="Synthetic Grant Patient", age=60, gender="Male", phone="9000000050",
                                         hospital=self.hospital)
        proxy_user = proxy_user_for("9000000051")
        grant = ProxyAccess.objects.create(patient=patient, name="Synthetic Son", relationship="Son",
                                           phone="9000000051", proxy_user=proxy_user)
        tokens = issue_proxy_tokens(proxy_user, grant)
        ProxyAccess.objects.filter(pk=grant.pk).update(revoked_at=timezone.now())

        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)
        self.assertIsNotNone(DeviceSession.objects.get(pk=AccessToken(tokens["access"])["sid"]).revoked_at)

    # Before this deploy ----------------------------------------------------

    def test_tokens_issued_before_sessions_existed_keep_working(self):
        legacy = RefreshToken.for_user(self.user)

        self.assertEqual(self.client_with(str(legacy.access_token)).get(ME).status_code, 200)
        self.assertEqual(self.refresh(str(legacy)).status_code, 200)


class OTPChallengeTests(TestCase):
    """Staff OTP sign-in with a mocked Twilio Verify (real credentials untested)."""

    def setUp(self):
        cache.clear()
        hospital = Hospital.objects.create(name="Synthetic OTP Hospital", is_active=True)
        user = User.objects.create_user(username="otp_doc", password=PASSWORD)
        profile = StaffProfile.objects.create(user=user, role=StaffRole.DOCTOR, employee_id="EMP-OTP",
                                              phone="9000000030", is_active_staff=True)
        StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=StaffRole.DOCTOR)
        patcher = mock.patch("users.views.get_twilio_verify_service", return_value=FakeVerify())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = APIClient(raise_request_exception=False)

    def challenge(self):
        response = self.client.post("/api/v1/auth/staff/login/otp/start/",
                                    {"username": "otp_doc", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["challenge"]

    def verify(self, challenge, code=VALID_CODE):
        return self.client.post("/api/v1/auth/staff/login/otp/verify/", {"challenge": challenge, "otp": code},
                                format="json")

    def test_otp_sign_in_creates_a_session(self):
        response = self.verify(self.challenge())

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(DeviceSession.objects.filter(pk=AccessToken(response.json()["access"])["sid"]).exists())

    def test_a_challenge_cannot_sign_in_twice(self):
        challenge = self.challenge()
        self.assertEqual(self.verify(challenge).status_code, 200)

        self.assertEqual(self.verify(challenge).status_code, 400)

    def test_too_many_wrong_codes_lock_the_challenge(self):
        challenge = self.challenge()
        for _ in range(5):
            self.assertEqual(self.verify(challenge, code="000000").status_code, 401)

        self.assertEqual(self.verify(challenge).status_code, 429)

    def test_a_wrong_code_leaves_the_challenge_usable(self):
        challenge = self.challenge()
        self.assertEqual(self.verify(challenge, code="000000").status_code, 401)

        self.assertEqual(self.verify(challenge).status_code, 200)
