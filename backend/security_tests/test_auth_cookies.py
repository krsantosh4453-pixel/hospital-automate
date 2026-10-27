"""Browser sessions: tokens in httpOnly cookies, CSRF on cookie-authenticated writes."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from config.auth_cookies import ACCESS_COOKIE, REFRESH_COOKIE
from hospital.models import Hospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

User = get_user_model()
PASSWORD = "Synthetic-Pass-123"
COOKIE_MODE = {"HTTP_X_AUTH_MODE": "cookie"}


@override_settings(STAFF_LOGIN_REQUIRE_OTP=False)
class CookieSessionTests(TestCase):
    def setUp(self):
        cache.clear()
        hospital = Hospital.objects.create(name="Synthetic Cookie Hospital", is_active=True)
        self.user = User.objects.create_user(username="cookie_doc", password=PASSWORD)
        profile = StaffProfile.objects.create(
            user=self.user, role=StaffRole.DOCTOR, employee_id="EMP-COOKIE", phone="9000000020", is_active_staff=True,
        )
        StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=StaffRole.DOCTOR)

    def browser(self):
        return APIClient(enforce_csrf_checks=True, raise_request_exception=False)

    def sign_in(self, client):
        resp = client.post(
            "/api/auth/staff/login/", {"username": "cookie_doc", "password": PASSWORD}, format="json", **COOKIE_MODE,
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp

    def csrf(self, client):
        return client.get("/api/auth/csrf/").json()["csrfToken"]

    def test_sign_in_sets_httponly_cookies_and_keeps_tokens_out_of_the_body(self):
        resp = self.sign_in(self.browser())
        body = resp.json()
        self.assertNotIn("access", body)
        self.assertNotIn("refresh", body)
        self.assertEqual(body["session"], "cookie")
        for name in (ACCESS_COOKIE, REFRESH_COOKIE):
            self.assertTrue(resp.cookies[name].value)
            self.assertTrue(resp.cookies[name]["httponly"])

    def test_cookie_authenticates_reads(self):
        client = self.browser()
        self.sign_in(client)
        self.assertEqual(client.get("/api/auth/staff/me/").status_code, 200)

    def test_cookie_authenticated_write_needs_csrf_token(self):
        client = self.browser()
        self.sign_in(client)
        refused = client.post("/api/auth/staff/logout/", {}, format="json", **COOKIE_MODE)
        self.assertEqual(refused.status_code, 403, refused.content)
        self.assertIn("CSRF", refused.content.decode())

        token = self.csrf(client)
        accepted = client.post("/api/auth/staff/logout/", {}, format="json", HTTP_X_CSRFTOKEN=token, **COOKIE_MODE)
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertEqual(accepted.cookies[ACCESS_COOKIE].value, "")
        self.assertEqual(accepted.cookies[REFRESH_COOKIE].value, "")

    def test_logout_blacklists_the_cookie_refresh_token(self):
        client = self.browser()
        refresh = self.sign_in(client).cookies[REFRESH_COOKIE].value
        client.post("/api/auth/staff/logout/", {}, format="json", HTTP_X_CSRFTOKEN=self.csrf(client), **COOKIE_MODE)
        reuse = APIClient().post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(reuse.status_code, 401)

    def test_refresh_from_cookie_rotates_cookies_without_exposing_tokens(self):
        client = self.browser()
        old_refresh = self.sign_in(client).cookies[REFRESH_COOKIE].value
        resp = client.post("/api/auth/token/refresh/", {}, format="json", **COOKIE_MODE)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertNotIn("access", resp.json())
        self.assertTrue(resp.cookies[ACCESS_COOKIE].value)
        self.assertNotEqual(resp.cookies[REFRESH_COOKIE].value, old_refresh)

    def test_refresh_without_cookie_is_unauthorized(self):
        resp = self.browser().post("/api/auth/token/refresh/", {}, format="json", **COOKIE_MODE)
        self.assertEqual(resp.status_code, 401)

    def test_stale_access_cookie_does_not_block_sign_in(self):
        client = self.browser()
        client.cookies[ACCESS_COOKIE] = "not-a-valid-token"
        self.assertEqual(client.get("/api/auth/staff/me/").status_code, 401)
        self.sign_in(client)

    def test_bearer_clients_still_get_tokens_in_the_body(self):
        resp = APIClient().post("/api/auth/staff/login/", {"username": "cookie_doc", "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("access", resp.json())
        self.assertNotIn(ACCESS_COOKIE, resp.cookies)
