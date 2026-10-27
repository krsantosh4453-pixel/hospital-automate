"""
Session tokens in httpOnly cookies for the browser client.

The React app sends ``X-Auth-Mode: cookie``. For those requests, sign-in and
refresh responses put the access and refresh tokens in httpOnly cookies and
leave them out of the JSON body, so page scripts (and any XSS) never see
them. Requests authenticated by cookie must carry a CSRF token on writes.
API clients that send ``Authorization: Bearer`` work as before.
"""

from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

# DRF imports this module while loading its settings, so nothing here may
# import DRF views; the refresh and CSRF views live in auth_cookie_views.py.

ACCESS_COOKIE = "hms_access"
REFRESH_COOKIE = "hms_refresh"
# The refresh cookie is only needed by the token endpoints.
REFRESH_COOKIE_PATH = "/api/auth/"


def wants_cookies(request):
    return request.headers.get("X-Auth-Mode") == "cookie"


def _cookie_options():
    return {
        "httponly": True,
        "secure": getattr(settings, "AUTH_COOKIE_SECURE", not settings.DEBUG),
        "samesite": getattr(settings, "AUTH_COOKIE_SAMESITE", "Lax"),
    }


def set_auth_cookies(response, access, refresh=None):
    lifetimes = settings.SIMPLE_JWT
    response.set_cookie(
        ACCESS_COOKIE, access, path="/",
        max_age=int(lifetimes["ACCESS_TOKEN_LIFETIME"].total_seconds()), **_cookie_options(),
    )
    if refresh:
        response.set_cookie(
            REFRESH_COOKIE, refresh, path=REFRESH_COOKIE_PATH,
            max_age=int(lifetimes["REFRESH_TOKEN_LIFETIME"].total_seconds()), **_cookie_options(),
        )


def clear_auth_cookies(response):
    samesite = getattr(settings, "AUTH_COOKIE_SAMESITE", "Lax")
    response.delete_cookie(ACCESS_COOKIE, path="/", samesite=samesite)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, samesite=samesite)


def _enforce_csrf(request):
    # Same check as DRF's SessionAuthentication: a cookie is sent by the
    # browser automatically, so a write must also prove it came from our page.
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f"CSRF Failed: {reason}")


class CookieJWTAuthentication(JWTAuthentication):
    """Bearer header first; otherwise the httpOnly access cookie (with CSRF)."""

    def authenticate(self, request):
        if self.get_header(request) is not None:
            return super().authenticate(request)
        raw = request.COOKIES.get(ACCESS_COOKIE)
        if not raw:
            return None
        try:
            validated = self.get_validated_token(raw)
        except InvalidToken:
            # An expired cookie is "not signed in": protected views answer 401
            # (the client then refreshes) and sign-in pages still work.
            return None
        user = self.get_user(validated)
        _enforce_csrf(request)
        return user, validated


class AuthCookieMiddleware:
    """Moves tokens from sign-in/refresh JSON bodies into httpOnly cookies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not (wants_cookies(request) and request.path.startswith("/api/auth/")):
            return response
        data = getattr(response, "data", None)
        if not (isinstance(data, dict) and isinstance(data.get("access"), str)):
            return response
        from rest_framework.renderers import JSONRenderer

        body = {key: value for key, value in data.items() if key not in ("access", "refresh")}
        body["session"] = "cookie"
        response.data = body
        response.content = JSONRenderer().render(body)
        set_auth_cookies(response, data["access"], data.get("refresh"))
        return response
