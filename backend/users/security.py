"""Staff sign-in safeguards: failed-attempt lockout and signed OTP challenges."""

import hashlib

from django.conf import settings
from django.core import signing
from django.core.cache import cache

LOCKOUT_THRESHOLD = 5          # failed passwords before the account locks
LOCKOUT_SECONDS = 15 * 60      # how long the lock (and the failure count) lasts
CHALLENGE_SALT = "hms.staff-otp-challenge"
CHALLENGE_MAX_AGE = 10 * 60    # seconds a password-verified challenge stays valid


def _key(identifier):
    return f"staff-login-failures:{str(identifier or '').strip().lower()}"


def _account_key(user):
    # A separate namespace from typed identifiers, so no identifier a client
    # sends can collide with (and lock or clear) an account's counter. The
    # join time makes the key unique to this account even if an id is ever
    # reused (a database restored from backup, or test rollbacks).
    joined = int(user.date_joined.timestamp() * 1_000_000) if user.date_joined else 0
    return f"login-failures-account:{int(user.pk)}:{joined}"


def _locked(cache_key):
    return cache.get(cache_key, 0) >= LOCKOUT_THRESHOLD


def _incr(cache_key):
    try:
        cache.add(cache_key, 0, LOCKOUT_SECONDS)
        cache.incr(cache_key)
    except ValueError:  # key expired between add and incr
        cache.set(cache_key, 1, LOCKOUT_SECONDS)


def is_locked_out(identifier):
    return _locked(_key(identifier))


def record_failure(identifier):
    _incr(_key(identifier))


def clear_failures(identifier):
    cache.delete(_key(identifier))


# ---------------------------------------------------------------------------
# Per-account lockout (S-L1, S-L2)
#
# The counters above are keyed by what the client typed, so "dr.rao" and
# "rao@example.org" (the same account) had separate budgets. Password sign-in
# now also counts failures against every account the identifier resolves to.
# Staff and patient sign-in share the account counter, since both test the
# same password. The typed-identifier counter stays, so an identifier that
# matches no account locks exactly like one that does: the 429 does not reveal
# whether an account exists.
# ---------------------------------------------------------------------------

MAX_ACCOUNTS_PER_IDENTIFIER = 10   # bound the lookup; real identifiers match 1-3


def login_keys(identifier, users=()):
    """Cache keys for one password attempt: the typed identifier plus each account."""
    keys = [_key(identifier)]
    keys.extend(_account_key(user) for user in list(users)[:MAX_ACCOUNTS_PER_IDENTIFIER])
    return keys


def staff_login_keys(identifier):
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    ident = str(identifier or "").strip()
    if not ident:
        return login_keys(ident)
    users = (
        get_user_model().objects.filter(Q(username__iexact=ident) | Q(email__iexact=ident))
        .order_by("pk").only("pk", "date_joined")[:MAX_ACCOUNTS_PER_IDENTIFIER]
    )
    return login_keys(ident, users)


def any_locked_out(keys):
    return any(_locked(key) for key in keys)


def record_failures(keys):
    for key in keys:
        _incr(key)


def clear_login_failures(identifier, user):
    """After a correct password: clear the typed identifier and that account only."""
    cache.delete(_key(identifier))
    if user is not None:
        cache.delete(_account_key(user))



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


def _used_key(token):
    return "staff-otp-challenge-used:" + hashlib.sha256(str(token).encode()).hexdigest()


def otp_challenge_used(token):
    """Whether this challenge already signed someone in."""
    return cache.get(_used_key(token)) is not None


def consume_otp_challenge(token):
    """Mark the challenge used; False if another request used it first (single use)."""
    return cache.add(_used_key(token), 1, CHALLENGE_MAX_AGE)


def otp_required_for_staff():
    return bool(getattr(settings, "STAFF_LOGIN_REQUIRE_OTP", False))
