"""Phase 3 guard: every /api/ view is hospital-scoped or listed with a reason in config/tenancy_exemptions.py."""

from django.test import SimpleTestCase
from django.urls import get_resolver

from config.tenancy_exemptions import OWN_CHECKS, TENANCY_EXEMPTIONS
from users.viewsets import HospitalScopedViewSet, ReadOnlyHospitalScopedViewSet

SCOPED_BASES = (HospitalScopedViewSet, ReadOnlyHospitalScopedViewSet)


def _walk(patterns, prefix=""):
    for pattern in patterns:
        if hasattr(pattern, "url_patterns"):
            yield from _walk(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            yield prefix + str(pattern.pattern), pattern.callback


def view_key(callback):
    """``module.Class`` for class-based views, ``module.function`` for @api_view functions."""
    cls = getattr(callback, "cls", None)
    if cls is None or cls.__name__ == "WrappedAPIView":
        return f"{callback.__module__}.{callback.__name__}"
    return f"{cls.__module__}.{cls.__name__}"


def api_views():
    """``{view_key: (route, view class or None)}`` for every view under /api/ (both prefixes)."""
    views = {}
    for route, callback in _walk(get_resolver().url_patterns):
        if route.startswith("api/"):
            views.setdefault(view_key(callback), (route, getattr(callback, "cls", None)))
    return views


class TenancyGuardTests(SimpleTestCase):
    def test_every_api_view_is_scoped_or_has_a_written_reason(self):
        unclassified = sorted(
            f"{key} ({route})" for key, (route, cls) in api_views().items()
            if not (cls is not None and issubclass(cls, SCOPED_BASES)) and key not in TENANCY_EXEMPTIONS
        )
        self.assertEqual(unclassified, [], "Scope these views on HospitalScopedViewSet or list them, with a "
                                             "reason, in config/tenancy_exemptions.py")

    def test_the_exemption_list_names_only_views_that_exist_and_are_not_scoped(self):
        views = api_views()
        stale = sorted(key for key in TENANCY_EXEMPTIONS if key not in views)
        scoped = sorted(key for key, (_, cls) in views.items()
                        if key in TENANCY_EXEMPTIONS and cls is not None and issubclass(cls, SCOPED_BASES))
        self.assertEqual((stale, scoped), ([], []))

    def test_every_exemption_has_a_category_and_a_reason(self):
        for key, (category, reason) in TENANCY_EXEMPTIONS.items():
            self.assertIn(category, {"auth", "public", "platform", OWN_CHECKS, "webhook"}, key)
            self.assertTrue(reason.strip(), key)
