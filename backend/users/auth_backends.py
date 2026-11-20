"""Password sign-in by username or email, as typed on any keyboard.

The sign-in forms ask for "Username or email". Django's ModelBackend only
matches the username exactly, so "Dr.Test" (a phone keyboard capitalising
the first letter), "dr.test " (a trailing space after a suggestion) or the
account's email address were all refused as wrong credentials.

Lookup order, so an exact username always wins:
1. the username exactly as typed (after trimming spaces);
2. the username in any letter case, when exactly one account matches;
3. the email address in any letter case, when exactly one account matches.
An ambiguous identifier matches nobody: the user types the exact username.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


def _single(queryset):
    """The only row of [queryset], or None when there are none or several."""
    rows = list(queryset[:2])
    return rows[0] if len(rows) == 1 else None


def find_user_by_identifier(identifier):
    """The account a typed username or email refers to, or None."""
    ident = str(identifier or "").strip()
    if not ident:
        return None
    users = get_user_model()._default_manager
    return (
        users.filter(username=ident).first()
        or _single(users.filter(username__iexact=ident))
        or _single(users.filter(email__iexact=ident))
    )


class UsernameOrEmailBackend(ModelBackend):
    """ModelBackend that accepts the username or email in any letter case."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = username if username is not None else kwargs.get(user_model.USERNAME_FIELD)
        if not identifier or password is None:
            return None
        user = find_user_by_identifier(identifier)
        if user is None:
            # Hash anyway so an unknown identifier takes as long as a wrong
            # password (as ModelBackend does), revealing no accounts.
            user_model().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
