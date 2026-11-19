"""
How often a medication order (MAR) is given, read from the doctor's text.

Clinical safety review 2026-11-19, hazard H-01: the scheduler used to look
for substrings and fall back to "once daily" for anything it did not know,
so BD, TDS, 1-0-1 and WEEKLY were all scheduled once a day, EOD matched "OD",
STAT was repeated daily and Q0H never finished. A frequency is now either
recognised exactly or refused, so the doctor corrects it before any dose is
scheduled.
"""

import re
from dataclasses import dataclass

INTERVAL = "interval"  # a dose every ``interval_hours``
PRN = "prn"            # as needed: recorded when given, never scheduled
ONCE = "once"          # a single dose (STAT)

MIN_INTERVAL_HOURS = 1
MAX_INTERVAL_HOURS = 168  # weekly

ACCEPTED = ("Use OD, BD, TDS, QDS, HS, Q<hours>H (e.g. Q8H), the 1-0-1 pattern, EOD, WEEKLY, "
            "STAT or PRN/SOS.")

# Whole-text names and the hours between doses.
_NAMED = {
    "OD": 24, "QD": 24, "DAILY": 24, "ONCE DAILY": 24, "ONCE A DAY": 24,
    "HS": 24, "QHS": 24, "NOCTE": 24, "AT BEDTIME": 24,
    "BD": 12, "BID": 12, "TWICE DAILY": 12, "TWICE A DAY": 12,
    "TDS": 8, "TID": 8, "THRICE DAILY": 8, "THREE TIMES A DAY": 8, "THREE TIMES DAILY": 8,
    "QDS": 6, "QID": 6, "FOUR TIMES A DAY": 6, "FOUR TIMES DAILY": 6,
    "EOD": 48, "QOD": 48, "ALTERNATE DAY": 48, "ALTERNATE DAYS": 48, "EVERY OTHER DAY": 48,
    "WEEKLY": 168, "ONCE WEEKLY": 168, "ONCE A WEEK": 168,
}
_ONCE = {"STAT", "ONCE", "SINGLE DOSE", "ONE DOSE", "ONCE ONLY"}
# As needed wins over anything else written with it ("PRN Q6H"): never auto-scheduled.
_PRN_WORD = re.compile(r"\b(PRN|SOS|AS NEEDED|AS REQUIRED)\b")
_EVERY = re.compile(r"^(?:Q\s*(\d+)\s*(?:H|HR|HRS|HRLY|HOURLY)|EVERY\s+(\d+)\s*(?:H|HR|HRS|HOURS?))$")
# Morning-afternoon-night (and optionally a fourth slot) dose pattern, e.g. 1-0-1 or ½-0-½.
_SLOT = r"(?:\d+(?:\.\d+)?|½|¼|¾)"
_SLOTS = re.compile(rf"^{_SLOT}(?:\s*-\s*{_SLOT}){{2,3}}$")
_HOURS_FOR_DOSES = {1: 24, 2: 12, 3: 8, 4: 6}


class FrequencyError(ValueError):
    """The frequency cannot be scheduled safely; the message says what to write."""


@dataclass(frozen=True)
class Frequency:
    kind: str
    interval_hours: int | None = None


def _normal(text):
    return " ".join(str(text or "").upper().replace(".", " ").split())


def _slot_doses(text):
    return sum(1 for part in text.split("-") if part.strip() not in ("0", "0.0"))


def parse_frequency(text):
    """The schedule ``text`` asks for, or FrequencyError."""
    value = _normal(text)
    if not value:
        raise FrequencyError(f"Frequency is required. {ACCEPTED}")
    if _PRN_WORD.search(value):
        return Frequency(PRN)
    if value in _ONCE:
        return Frequency(ONCE)
    if value in _NAMED:
        return Frequency(INTERVAL, _NAMED[value])
    every = _EVERY.match(value)
    if every:
        hours = int(every.group(1) or every.group(2))
        if not MIN_INTERVAL_HOURS <= hours <= MAX_INTERVAL_HOURS:
            raise FrequencyError(
                f"Every {hours} hours cannot be scheduled; use {MIN_INTERVAL_HOURS} to {MAX_INTERVAL_HOURS} hours.")
        return Frequency(INTERVAL, hours)
    if _SLOTS.match(value):
        doses = _slot_doses(value)
        if doses not in _HOURS_FOR_DOSES:
            raise FrequencyError(f"\"{text}\" gives no dose to schedule. {ACCEPTED}")
        return Frequency(INTERVAL, _HOURS_FOR_DOSES[doses])
    raise FrequencyError(f"\"{str(text).strip()}\" is not a frequency the schedule understands. {ACCEPTED}")
