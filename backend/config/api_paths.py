"""
The API is mounted at /api/v1/ and at /api/ (config/urls.py), running the same
views. Code that matches request paths (rate limits, cookie sign-in, family
access) compares the unversioned form, so a rule written for /api/auth/ also
covers /api/v1/auth/ and the two prefixes share one budget.
"""

API_PREFIX = "/api/"
API_VERSION_PREFIX = "/api/v1/"


def unversioned_path(path):
    """``/api/v1/auth/x/`` -> ``/api/auth/x/``; any other path is returned unchanged."""
    if path.startswith(API_VERSION_PREFIX):
        return API_PREFIX + path[len(API_VERSION_PREFIX):]
    return path


def versioned_paths_only(endpoints):
    """drf-spectacular preprocessing hook: document each endpoint once, under /api/v1/."""
    return [endpoint for endpoint in endpoints if endpoint[0].startswith(API_VERSION_PREFIX)]
