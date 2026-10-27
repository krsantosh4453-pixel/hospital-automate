"""A client-supplied X-Forwarded-For must not choose the address used for limits and audit."""

from django.test import RequestFactory, SimpleTestCase, override_settings

from audit.services import _client_ip as audit_client_ip
from config.client_ip import client_ip
from config.middleware.ratelimit import RateLimitMiddleware

NGINX_SEEN = "203.0.113.7"


def request_with(forwarded=None, remote="10.0.0.2"):
    extra = {"REMOTE_ADDR": remote}
    if forwarded is not None:
        extra["HTTP_X_FORWARDED_FOR"] = forwarded
    return RequestFactory().post("/api/auth/staff/login/", **extra)


class ClientIpTests(SimpleTestCase):
    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_behind_one_proxy_the_entry_nginx_appended_wins(self):
        for spoofed in ("1.1.1.1", "2.2.2.2, 3.3.3.3"):
            self.assertEqual(client_ip(request_with(f"{spoofed}, {NGINX_SEEN}")), NGINX_SEEN)

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_without_a_trusted_proxy_the_header_is_ignored(self):
        self.assertEqual(client_ip(request_with("1.1.1.1")), "10.0.0.2")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_rate_limit_and_audit_use_the_same_address(self):
        request = request_with(f"9.9.9.9, {NGINX_SEEN}")
        middleware = RateLimitMiddleware(lambda r: None)
        self.assertEqual(middleware._get_client_ip(request), NGINX_SEEN)
        self.assertEqual(audit_client_ip(request), NGINX_SEEN)
