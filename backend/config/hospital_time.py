"""
The hospital's own clock. Settings use UTC; "today" follows the hospital.

Never filter a timestamp with ``<field>__date=day``: with settings in UTC
that takes the UTC date, which differs from the hospital's between 00:00 and
05:30 IST. Use ``on_hospital_day`` (or ``day_bounds``) instead, and group by
``TruncDate(field, tzinfo=hospital_tz())``.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q
from django.utils import timezone


def hospital_tz():
    return ZoneInfo(getattr(settings, "HOSPITAL_TIME_ZONE", "Asia/Kolkata"))


def hospital_now():
    return timezone.now().astimezone(hospital_tz())


def hospital_today():
    return hospital_now().date()


def day_bounds(day):
    """(start, end) of the hospital's calendar ``day`` as aware datetimes; end is exclusive."""
    start = datetime.combine(day, time.min, tzinfo=hospital_tz())
    return start, start + timedelta(days=1)


def on_hospital_day(field, day):
    """Q: ``field`` (a timestamp) falls on the hospital's calendar ``day``."""
    start, end = day_bounds(day)
    return Q(**{f"{field}__gte": start, f"{field}__lt": end})


def hospital_date_range(field, first=None, last=None):
    """Q: ``field`` falls between the hospital days ``first`` and ``last`` (both inclusive, either optional)."""
    condition = Q()
    if first is not None:
        condition &= Q(**{f"{field}__gte": day_bounds(first)[0]})
    if last is not None:
        condition &= Q(**{f"{field}__lt": day_bounds(last)[1]})
    return condition
