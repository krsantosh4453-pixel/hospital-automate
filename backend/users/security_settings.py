"""
Read-only view of the effective security configuration (requirement A14).

These values come from environment variables at deploy time. They are not
editable here on purpose: letting the web application change its own OTP,
cookie or rate-limit rules would let one compromised admin session weaken
security for everyone. No secret (keys, tokens, passwords) is ever returned.
"""

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .permissions import IsAdmin

ONE_YEAR_SECONDS = 31536000
MIN_PASSWORD_VALIDATORS = 4


def _item(key, label, value, secure, note=""):
    # secure: True = recommended, False = weak for production, None = informational.
    return {"key": key, "label": label, "value": value, "secure": secure, "note": note}


def _setting(name, default=None):
    return getattr(settings, name, default)


def _lifetime(name):
    value = _setting("SIMPLE_JWT", {}).get(name)
    return str(value) if value is not None else "default"


def collect_security_settings():
    rates = _setting("REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES", {})
    hsts = _setting("SECURE_HSTS_SECONDS", 0)
    validators = len(_setting("AUTH_PASSWORD_VALIDATORS", []))
    otp = _setting("STAFF_LOGIN_REQUIRE_OTP", False)
    dev_login = _setting("DEV_LOGIN_ENABLED", False)
    cookie_secure = _setting("AUTH_COOKIE_SECURE", False)
    samesite = _setting("AUTH_COOKIE_SAMESITE", "")
    ssl_redirect = _setting("SECURE_SSL_REDIRECT", False)
    rate_limit = _setting("RATE_LIMIT_ENABLED", False)
    return [
        _item("DEBUG", "Debug mode", settings.DEBUG, not settings.DEBUG, "Must be off in production."),
        _item("STAFF_LOGIN_REQUIRE_OTP", "Staff sign-in needs a one-time code", otp, otp),
        _item("DEV_LOGIN_ENABLED", "Shared development sign-in", dev_login, not dev_login,
              "Development only; always off in production."),
        _item("ACCESS_TOKEN_LIFETIME", "Access token lifetime", _lifetime("ACCESS_TOKEN_LIFETIME"), None),
        _item("REFRESH_TOKEN_LIFETIME", "Refresh token lifetime", _lifetime("REFRESH_TOKEN_LIFETIME"), None),
        _item("AUTH_COOKIE_SECURE", "Sign-in cookies sent over HTTPS only", cookie_secure, cookie_secure),
        _item("AUTH_COOKIE_SAMESITE", "Sign-in cookie SameSite", samesite, samesite == "Strict"),
        _item("SECURE_SSL_REDIRECT", "Redirect HTTP to HTTPS", ssl_redirect, ssl_redirect),
        _item("SECURE_HSTS_SECONDS", "HSTS duration (seconds)", hsts, hsts >= ONE_YEAR_SECONDS),
        _item("PASSWORD_VALIDATORS", "Password rules applied", validators, validators >= MIN_PASSWORD_VALIDATORS),
        _item("RATE_LIMIT_ENABLED", "Rate limiting", rate_limit, rate_limit),
        _item("THROTTLE_LOGIN", "Sign-in attempts allowed", rates.get("login", "not set"), "login" in rates),
        _item("THROTTLE_OTP", "One-time codes allowed", rates.get("otp", "not set"), "otp" in rates),
        _item("TRUSTED_PROXY_COUNT", "Trusted proxies in front of the app", _setting("TRUSTED_PROXY_COUNT", 0), None,
              "Number of reverse proxies (e.g. 1 for nginx), so client IP addresses are read correctly."),
    ]


@api_view(["GET"])
@permission_classes([IsAdmin])
def security_settings(request):
    return Response({
        "editable": False,
        "how_to_change": "Set the environment variables on the server and restart the application.",
        "settings": collect_security_settings(),
    })
