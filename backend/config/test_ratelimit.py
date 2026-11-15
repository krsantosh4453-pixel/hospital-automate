"""RateLimitMiddleware: per-rule budgets, most specific rule wins, keys that can't be dodged."""

import json

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from config.middleware.ratelimit import RateLimitMiddleware


@override_settings(RATE_LIMIT_ENABLED=True, TRUSTED_PROXY_COUNT=0)
class RateLimitMiddlewareTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.middleware = RateLimitMiddleware(lambda request: HttpResponse("ok"))

    def call(self, path, ip="10.0.0.1", method="post", data=None):
        if method == "get":
            request = self.factory.get(path, REMOTE_ADDR=ip)
        else:
            request = self.factory.post(
                path, data=json.dumps(data or {}), content_type="application/json", REMOTE_ADDR=ip
            )
        request.user = AnonymousUser()
        return self.middleware(request)

    def statuses(self, path, times, **kwargs):
        return [self.call(path, **kwargs).status_code for _ in range(times)]

    def test_staff_login_is_limited_per_account(self):
        login = {"username": "dr.synthetic", "password": "x"}
        self.assertEqual(self.statuses("/api/auth/staff/login/", 5, data=login), [200] * 5)
        blocked = self.call("/api/auth/staff/login/", data=login)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(json.loads(blocked.content)["error"]["code"], "RATE_LIMITED")
        # The same account from another address shares the budget.
        self.assertEqual(self.call("/api/auth/staff/login/", ip="10.0.0.2", data=login).status_code, 429)
        # Usernames differ only in case: one account.
        self.assertEqual(self.call("/api/auth/staff/login/", data={"username": "DR.Synthetic"}).status_code, 429)

    def test_a_shift_change_behind_one_address_is_not_blocked(self):
        # 40 staff sign in from one hospital NAT address, each with password then OTP.
        for n in range(40):
            user = {"username": f"staff{n}"}
            self.assertEqual(self.call("/api/auth/staff/login/otp/start/", data=user).status_code, 200, n)

    def test_patients_behind_one_mobile_carrier_address_can_all_ask_for_a_code(self):
        """P1-08: carrier-grade NAT puts many patients on one IP; the limit is per phone."""
        for n in range(30):
            phone = {"phone": f"98765{n:05d}"}
            self.assertEqual(self.call("/api/auth/patient/otp/request/", data=phone).status_code, 200, n)

    def test_one_phone_is_still_capped_across_addresses(self):
        phone = {"phone": "9876500001"}
        for n in range(5):
            self.call("/api/auth/patient/otp/request/", ip=f"10.0.1.{n}", data=phone)
        self.assertEqual(self.call("/api/auth/patient/otp/request/", ip="10.0.1.99", data=phone).status_code, 429)

    def test_one_address_spraying_many_phones_is_still_capped(self):
        for n in range(60):
            self.call("/api/auth/patient/otp/request/", data={"phone": f"91111{n:05d}"})
        self.assertEqual(self.call("/api/auth/patient/otp/request/", data={"phone": "9222200000"}).status_code, 429)

    def test_one_address_trying_many_accounts_is_still_capped(self):
        for n in range(60):
            self.call("/api/auth/staff/login/", data={"username": f"spray{n}"})
        self.assertEqual(self.call("/api/auth/staff/login/", data={"username": "spray99"}).status_code, 429)

    def test_otp_steps_are_limited_per_challenge(self):
        for _ in range(5):
            self.call("/api/auth/staff/login/otp/verify/", data={"challenge": "signed-a", "otp": "000000"})
        self.assertEqual(self.call("/api/auth/staff/login/otp/verify/",
                                   data={"challenge": "signed-a", "otp": "000000"}).status_code, 429)
        self.assertEqual(self.call("/api/auth/staff/login/otp/verify/",
                                   data={"challenge": "signed-b", "otp": "000000"}).status_code, 200)

    def test_headers_report_the_remaining_budget(self):
        response = self.call("/api/auth/staff/login/", data={"username": "dr.headers"})
        self.assertEqual(response["X-RateLimit-Limit"], "5")
        self.assertEqual(response["X-RateLimit-Remaining"], "4")

    def test_the_most_specific_rule_applies(self):
        # /api/ai/consultation/ allows 10 a minute; the broader /api/ai/ rule allows 30.
        self.assertEqual(self.statuses("/api/ai/consultation/", 10), [200] * 10)
        self.assertEqual(self.call("/api/ai/consultation/").status_code, 429)

    def test_paths_under_one_rule_share_its_budget(self):
        for i in range(20):
            self.call(f"/api/documents/{i}/")
        self.assertEqual(self.call("/api/documents/99/").status_code, 429)

    def test_otp_is_limited_per_phone_across_ips(self):
        for i in range(3):
            self.assertEqual(self.call("/api/notifications/otp/", ip=f"10.0.1.{i}",
                                       data={"phone": "9000000001"}).status_code, 200)
        self.assertEqual(self.call("/api/notifications/otp/", ip="10.0.1.9",
                                   data={"phone": "9000000001"}).status_code, 429)
        self.assertEqual(self.call("/api/notifications/otp/", data={"phone": "9000000002"}).status_code, 200)

    def test_unlisted_and_health_paths_are_not_limited(self):
        self.assertEqual(self.statuses("/api/patients/", 50, method="get"), [200] * 50)
        self.assertEqual(self.statuses("/health/ready/", 50, method="get"), [200] * 50)

    @override_settings(RATE_LIMIT_ENABLED=False)
    def test_disabled_setting_turns_limits_off(self):
        self.assertEqual(self.statuses("/api/auth/staff/login/", 10, data={"username": "u"}), [200] * 10)
