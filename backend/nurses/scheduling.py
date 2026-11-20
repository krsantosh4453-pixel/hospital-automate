"""
When the doses of a ward medication order (MAR) fall.

Final E2E audit (20 Nov 2026): a once-daily order written at 07:32 got its
first dose at 00:00 that day and showed as Overdue at once. The first dose
is now one of:

* ``now``        - start now (a STAT dose, or the doctor wants it given now);
* ``at``         - a time the doctor chose, never in the past;
* ``next_round`` - the hospital's next configured medication round.

Rounds are configured per hospital (``MedicationRound``); none are assumed.
When the doctor chooses nothing, a once-daily-or-longer order takes the next
round, and a hospital without rounds gets a refusal asking the doctor to
choose. Later doses follow the frequency: whole days keep the local clock
time (so a daylight-saving change does not move an 08:00 dose to 07:00),
shorter intervals step in real hours.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone

from config.hospital_time import hospital_now

from .frequency import INTERVAL, ONCE, PRN, Frequency

NOW = "now"
AT = "at"
NEXT_ROUND = "next_round"
MODES = (NOW, AT, NEXT_ROUND)

# A chosen time this far behind the server clock still counts as "now"
# (the doctor's screen and the server disagree by a few seconds).
CLOCK_TOLERANCE = timedelta(minutes=5)
# Without an end date, doses are scheduled this many days ahead (as before).
DEFAULT_DAYS = 7
DEFAULT_OVERDUE_GRACE_MINUTES = 30


class ScheduleError(ValueError):
    """The first dose cannot be placed safely; ``needs_choice`` asks the doctor to pick."""

    def __init__(self, message, needs_choice=False):
        super().__init__(message)
        self.needs_choice = needs_choice


@dataclass(frozen=True)
class FirstDose:
    mode: str
    at: datetime


def overdue_grace():
    """How long after its time a due dose is shown as overdue."""
    return timedelta(minutes=getattr(settings, "MAR_OVERDUE_GRACE_MINUTES", DEFAULT_OVERDUE_GRACE_MINUTES))


def hospital_zone():
    return hospital_now().tzinfo


def at_local(day, clock, tz):
    """``day`` at wall-clock ``clock`` in ``tz``, moved forward past a DST gap."""
    naive = datetime.combine(day, clock)
    aware = naive.replace(tzinfo=tz)
    # A wall time inside a spring-forward gap does not exist; round-tripping
    # through UTC gives the real instant just after the gap.
    return aware.astimezone(dt_timezone.utc).astimezone(tz)


def next_round(rounds, after, tz, earliest_day=None):
    """The first active round strictly after ``after`` (and not before ``earliest_day``)."""
    times = sorted(rounds)
    if not times:
        return None
    local = after.astimezone(tz)
    day = max(local.date(), earliest_day or local.date())
    for offset in range(0, 3):
        for clock in times:
            candidate = at_local(day + timedelta(days=offset), clock, tz)
            if candidate > after:
                return candidate
    return None


def parse_when(value, tz):
    """An ISO date-time; a time without a zone is the hospital's clock."""
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ScheduleError("Give the first dose time as ISO date-time, e.g. 2026-11-20T14:00.") from exc
    if timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=tz)
        parsed = parsed.astimezone(dt_timezone.utc).astimezone(tz)
    return parsed


def resolve_first_dose(frequency: Frequency, mode, when, rounds, start_day, end_day, now=None, tz=None):
    """
    The first dose of an order, or ScheduleError.

    ``mode`` is None when the doctor chose nothing; ``when`` is the chosen
    time for ``at``; ``rounds`` are the hospital's round clock times.
    """
    tz = tz or hospital_zone()
    now = now or timezone.now()
    today = now.astimezone(tz).date()
    if frequency.kind == PRN:
        raise ScheduleError("As-needed (PRN) orders have no scheduled doses.")
    if mode is not None and mode not in MODES:
        raise ScheduleError(f"First dose must be one of: {', '.join(MODES)}.")
    if end_day is not None and end_day < max(today, start_day or today):
        raise ScheduleError("The order has already ended; no dose can be scheduled.")
    if mode is None:
        mode = _default_mode(frequency, rounds, start_day, today)

    if mode == NOW:
        if start_day and start_day > today:
            raise ScheduleError(f"The order starts on {start_day}; choose a time on or after that day.")
        first = now
    elif mode == AT:
        if not when:
            raise ScheduleError("Choose the time of the first dose.", needs_choice=True)
        first = parse_when(when, tz)
        if first < now - CLOCK_TOLERANCE:
            raise ScheduleError("The first dose cannot be in the past; choose a later time or start now.")
        if start_day and first.astimezone(tz).date() < start_day:
            raise ScheduleError(f"The order starts on {start_day}; the first dose cannot be earlier.")
    else:
        first = next_round(rounds, now, tz, earliest_day=start_day)
        if first is None:
            raise ScheduleError(
                "This hospital has no medication rounds configured. Choose Start now or a specific time.",
                needs_choice=True,
            )
    if end_day is not None and first.astimezone(tz).date() > end_day:
        raise ScheduleError(f"The first dose would fall after the order ends on {end_day}.")
    return FirstDose(mode, first.astimezone(tz))


def _default_mode(frequency, rounds, start_day, today):
    if frequency.kind == ONCE:
        return NOW  # STAT: given now
    if frequency.interval_hours and frequency.interval_hours >= 24:
        if not rounds:
            raise ScheduleError(
                "Once-daily (or less frequent) orders start at a medication round, and this hospital has "
                "none configured. Choose Start now or a specific time.",
                needs_choice=True,
            )
        return NEXT_ROUND
    if start_day and start_day > today:
        raise ScheduleError(f"The order starts on {start_day}; choose the time of the first dose.",
                            needs_choice=True)
    return NOW  # more than once a day: as before, the first dose is now


def dose_times(frequency: Frequency, first: datetime, end_day=None, tz=None):
    """Every scheduled dose from ``first`` up to ``end_day`` (default: 7 days on)."""
    tz = tz or hospital_zone()
    first = first.astimezone(tz)
    if frequency.kind == ONCE:
        return [first]
    if frequency.kind != INTERVAL or not frequency.interval_hours:
        return []
    last_day = end_day or first.date() + timedelta(days=DEFAULT_DAYS)
    hours = frequency.interval_hours
    times = []
    if hours % 24 == 0:
        step = hours // 24
        k = 0
        while True:
            when = at_local(first.date() + timedelta(days=step * k), first.time().replace(tzinfo=None), tz)
            if when.date() > last_day:
                break
            times.append(when)
            k += 1
    else:
        when = first
        while when.astimezone(tz).date() <= last_day:
            times.append(when.astimezone(tz))
            when = when + timedelta(hours=hours)
    return times


def round_times(hospital_id):
    """The hospital's active round clock times."""
    from .models import MedicationRound

    return list(MedicationRound.objects.filter(hospital_id=hospital_id, is_active=True)
                .values_list("time", flat=True))


def as_day(value):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
