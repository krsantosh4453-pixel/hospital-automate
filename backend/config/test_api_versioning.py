"""/api/v1/ runs the same views as /api/, under the same rate limits and access rules."""

import json

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve, reverse

from config.api_paths import unversioned_path, versioned_paths_only
from config.middleware.ratelimit import RateLimitMiddleware

SAMPLE_PATHS = (
    "auth/patient/otp/request/",
    "auth/token/refresh/",
    "patients/",
    "appointments/book/",
    "laboratory/lab-results/",
    "billing/invoices/",
    "hospital/directory/",
    "ai/discharge/admissions/",
)


class VersionedRoutesTests(SimpleTestCase):
    def test_every_sample_route_resolves_to_the_same_view_under_both_prefixes(self):
        for path in SAMPLE_PATHS:
            legacy, versioned = resolve(f"/api/{path}"), resolve(f"/api/v1/{path}")
            self.assertEqual(legacy.func.__qualname__, versioned.func.__qualname__, path)
            self.assertEqual(getattr(legacy.func, "actions", None), getattr(versioned.func, "actions", None), path)

    def test_route_names_reverse_to_the_legacy_prefix_and_v1_names_to_v1(self):
        self.assertEqual(reverse("patient-otp-request"), "/api/auth/patient/otp/request/")
        self.assertEqual(reverse("v1:patient-otp-request"), "/api/v1/auth/patient/otp/request/")
        self.assertEqual(reverse("v1:abdm:status"), "/api/v1/abdm/status/")

    def test_unversioned_path_strips_only_the_version_prefix(self):
        self.assertEqual(unversioned_path("/api/v1/auth/staff/login/"), "/api/auth/staff/login/")
        self.assertEqual(unversioned_path("/api/auth/staff/login/"), "/api/auth/staff/login/")
        self.assertEqual(unversioned_path("/api/v10/x/"), "/api/v10/x/")
        self.assertEqual(unversioned_path("/health/"), "/health/")

    def test_schema_hook_keeps_only_versioned_endpoints(self):
        endpoints = [("/api/patients/", "", "GET", None), ("/api/v1/patients/", "", "GET", None)]
        self.assertEqual([e[0] for e in versioned_paths_only(endpoints)], ["/api/v1/patients/"])


@override_settings(RATE_LIMIT_ENABLED=True, TRUSTED_PROXY_COUNT=0)
class VersionedRateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.middleware = RateLimitMiddleware(lambda request: HttpResponse("ok"))

    def call(self, path):
        request = RequestFactory().post(
            path, data=json.dumps({"username": "dr.synthetic"}), content_type="application/json",
            REMOTE_ADDR="10.0.0.9",
        )
        request.user = AnonymousUser()
        return self.middleware(request).status_code

    def test_versioned_sign_in_is_rate_limited(self):
        statuses = [self.call("/api/v1/auth/staff/login/") for _ in range(6)]
        self.assertEqual(statuses, [200] * 5 + [429])

    def test_both_prefixes_share_one_budget(self):
        for _ in range(3):
            self.call("/api/auth/staff/login/")
        for _ in range(2):
            self.call("/api/v1/auth/staff/login/")
        self.assertEqual(self.call("/api/auth/staff/login/"), 429)
        self.assertEqual(self.call("/api/v1/auth/staff/login/"), 429)
