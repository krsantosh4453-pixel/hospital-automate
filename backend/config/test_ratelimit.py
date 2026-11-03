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

    def test_staff_login_is_limited_per_ip(self):
        self.assertEqual(self.statuses("/api/auth/staff/login/", 5), [200] * 5)
        blocked = self.call("/api/auth/staff/login/")
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(json.loads(blocked.content)["error"]["code"], "RATE_LIMITED")
        self.assertEqual(self.call("/api/auth/staff/login/", ip="10.0.0.2").status_code, 200)

    def test_headers_report_the_remaining_budget(self):
        response = self.call("/api/auth/staff/login/")
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
        self.assertEqual(self.statuses("/api/auth/staff/login/", 10), [200] * 10)
