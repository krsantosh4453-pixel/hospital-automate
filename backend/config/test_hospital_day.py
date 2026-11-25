"""
P1-3 (final validation 2026-11-25): settings run in UTC but the hospital's
day is India's. Between 00:00 and 05:30 IST the two dates differ, and filters
on `<field>__date` used the UTC date: a token made a second visit instead of
reusing the waiting one, and "today" figures read yesterday. These tests
replay existing checks with the clock frozen inside that window.
"""
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.test import SimpleTestCase

from config.hospital_time import day_bounds, hospital_today, on_hospital_day
from encounters import test_visit_lifecycle as lifecycle
from security_tests import test_home_stats as home_stats

EARLY_MORNING = datetime(2026, 11, 24, 21, 0, tzinfo=dt_timezone.utc)   # 02:30 IST on 25 Nov
LATE_EVENING = datetime(2026, 11, 25, 18, 0, tzinfo=dt_timezone.utc)    # 23:30 IST on 25 Nov


class FrozenClock:
    frozen = EARLY_MORNING

    def setUp(self):
        patcher = mock.patch("django.utils.timezone.now", return_value=self.frozen)
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()


class EarlyMorningTokenVisitTests(FrozenClock, lifecycle.TokenIssueVisitTests):
    """A token at 02:30 IST reuses the patient's waiting visit (no second visit)."""


class EarlyMorningBillingStatsTests(FrozenClock, home_stats.BillingStatsTests):
    """Money received at 02:30 IST counts as today's."""


class LateEveningBillingStatsTests(FrozenClock, home_stats.BillingStatsTests):
    frozen = LATE_EVENING


class HospitalDayTests(SimpleTestCase):
    def test_the_hospital_day_runs_from_ist_midnight_to_ist_midnight(self):
        start, end = day_bounds(date(2026, 11, 25))
        self.assertEqual(start, datetime(2026, 11, 24, 18, 30, tzinfo=dt_timezone.utc))
        self.assertEqual(end - start, timedelta(days=1))

    def test_today_is_india_today_in_the_early_morning(self):
        with mock.patch("django.utils.timezone.now", return_value=EARLY_MORNING):
            self.assertEqual(hospital_today(), date(2026, 11, 25))

    def test_on_hospital_day_is_a_half_open_range(self):
        condition = dict(on_hospital_day("paid_at", date(2026, 11, 25)).children)
        self.assertEqual(condition["paid_at__gte"], datetime(2026, 11, 24, 18, 30, tzinfo=dt_timezone.utc))
        self.assertEqual(condition["paid_at__lt"], datetime(2026, 11, 25, 18, 30, tzinfo=dt_timezone.utc))
