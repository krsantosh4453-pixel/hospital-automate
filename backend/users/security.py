"""Staff sign-in safeguards: failed-attempt lockout and signed OTP challenges."""

from django.conf import settings
from django.core import signing
from django.core.cache import cache

LOCKOUT_THRESHOLD = 5          # failed passwords before the account locks
LOCKOUT_SECONDS = 15 * 60      # how long the lock (and the failure count) lasts
CHALLENGE_SALT = "hms.staff-otp-challenge"
CHALLENGE_MAX_AGE = 10 * 60    # seconds a password-verified challenge stays valid


def _key(identifier):
    return f"staff-login-failures:{str(identifier or '').strip().lower()}"


def is_locked_out(identifier):
    return cache.get(_key(identifier), 0) >= LOCKOUT_THRESHOLD


def record_failure(identifier):
    key = _key(identifier)
    try:
        cache.add(key, 0, LOCKOUT_SECONDS)
        cache.incr(key)
    except ValueError:  # key expired between add and incr
        cache.set(key, 1, LOCKOUT_SECONDS)


def clear_failures(identifier):
    cache.delete(_key(identifier))


def issue_otp_challenge(user):
    """A signed, expiring proof that this user passed the password step."""
    return signing.dumps({"uid": user.pk}, salt=CHALLENGE_SALT)


def read_otp_challenge(token):
    """Return the user id from a valid challenge, else None."""
    try:
        data = signing.loads(str(token or ""), salt=CHALLENGE_SALT, max_age=CHALLENGE_MAX_AGE)
    except signing.BadSignature:
        return None
    return data.get("uid") if isinstance(data, dict) else None


def otp_required_for_staff():
    return bool(getattr(settings, "STAFF_LOGIN_REQUIRE_OTP", False))
