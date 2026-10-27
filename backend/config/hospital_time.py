"""The hospital's own clock. Settings use UTC; "today" follows the hospital."""

from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def hospital_now():
    return timezone.now().astimezone(ZoneInfo(getattr(settings, "HOSPITAL_TIME_ZONE", "Asia/Kolkata")))


def hospital_today():
    return hospital_now().date()
