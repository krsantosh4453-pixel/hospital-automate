"""
H-10: limits on an as-needed (PRN) medication order.

The doctor may set a minimum time between doses and a maximum number of
doses in any 24 hours. Blank means no limit. A dose that would break either
limit is refused, not warned about: the doctor changes the order if more is
needed. Only doses recorded as given count.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 7 * 24 * 60
MAX_DOSES_PER_24H = 48
WINDOW = timedelta(hours=24)


def _clock(moment):
    zone = ZoneInfo(getattr(settings, "HOSPITAL_TIME_ZONE", "Asia/Kolkata"))
    return moment.astimezone(zone).strftime("%d %b %H:%M")


def prn_limit_refusal(mar, now):
    """None when a PRN dose may be given at ``now``, else the 409 response body."""
    from .models import MARAdministration

    interval = mar.prn_min_interval_minutes
    max_doses = mar.prn_max_doses_per_24h
    if interval is None and max_doses is None:
        return None
    given = MARAdministration.objects.filter(mar=mar, is_prn=True, status=MARAdministration.ADMINISTERED)

    if interval is not None:
        last = given.order_by("-administered_time").values_list("administered_time", flat=True).first()
        if last is not None:
            next_allowed = last + timedelta(minutes=interval)
            if now < next_allowed:
                return {
                    "detail": (f"Too soon: the last dose was given at {_clock(last)}. The order allows one every "
                               f"{interval} minutes, so the next may be given from {_clock(next_allowed)}. "
                               "Ask the doctor if the patient needs it sooner."),
                    "code": "prn_min_interval",
                    # Boolean twins of "code" for clients that read flags (Android ApiException.flags).
                    "prn_min_interval": True,
                    "prn_limit": True,
                    "next_allowed_at": next_allowed.isoformat(),
                }

    if max_doses is not None:
        recent = given.filter(administered_time__gt=now - WINDOW).count()
        if recent >= max_doses:
            return {
                "detail": (f"Daily limit reached: {recent} doses in the last 24 hours, and the order allows "
                           f"{max_doses}. Ask the doctor before giving more."),
                "code": "prn_max_per_24h",
                "prn_max_per_24h": True,
                "prn_limit": True,
            }
    return None
