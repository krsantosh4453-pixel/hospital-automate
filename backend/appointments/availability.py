"""
A doctor's working days, read from their own ``Doctor.availability`` text
(BUG-003, E2E audit 2026-11-24).

The field is free text written by the hospital ("Mon-Sat 09:00-17:00",
"Mon, Wed, Fri", "Weekdays", "Daily"). Only the days are read here; times are
left as they are (slots still follow the hospital's fixed day). When the text
names no day at all (blank, "On call", "09:00-17:00") there is no rule and
every day stays bookable, exactly as before, so nothing is invented.
"""
import re

from rest_framework.exceptions import ValidationError

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_DAYS = {
    "mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "weds": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5, "sun": 6, "sunday": 6,
}
_DAY = r"(mon(?:day)?|tue(?:s(?:day)?)?|wed(?:s|nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"
_RANGE = re.compile(rf"\b{_DAY}\b\s*(?:-|–|to|till|until|through|thru)\s*\b{_DAY}\b")
_SINGLE = re.compile(rf"\b{_DAY}\b")
EVERY_DAY = frozenset(range(7))


def _span(start, end):
    """Days from start to end inclusive, wrapping past Sunday ("Fri-Mon")."""
    days, day = {start}, start
    while day != end:
        day = (day + 1) % 7
        days.add(day)
    return days


def parse_working_days(text):
    """The weekdays (0 = Monday) the text names, or None when it names none."""
    value = str(text or "").lower()
    if not value.strip():
        return None
    if re.search(r"\b(daily|every\s*day|all\s*days|7\s*days|all\s*week)\b", value):
        return set(EVERY_DAY)
    days = set()
    if re.search(r"\bweekdays?\b", value):
        days |= set(range(5))
    if re.search(r"\bweekends?\b", value):
        days |= {5, 6}
    for match in _RANGE.finditer(value):
        days |= _span(_DAYS[match.group(1)], _DAYS[match.group(2)])
    for match in _SINGLE.finditer(_RANGE.sub(" ", value)):
        days.add(_DAYS[match.group(1)])
    return days or None


def working_days_of(doctor):
    """Sorted weekday numbers the doctor works, or None (no rule written)."""
    days = parse_working_days(getattr(doctor, "availability", ""))
    return sorted(days) if days is not None else None


def day_off_reason(doctor, day):
    """Why ``doctor`` cannot be booked on ``day``, or None when they work that day."""
    days = parse_working_days(getattr(doctor, "availability", ""))
    if days is None or day.weekday() in days:
        return None
    return (f"{doctor.name} does not see patients on {DAY_NAMES[day.weekday()]}s "
            f"({doctor.availability.strip()}). Choose another day.")


def refuse_day_off(doctor, day):
    """ValidationError on ``appointment_date`` when the doctor does not work that day."""
    reason = day_off_reason(doctor, day)
    if reason:
        raise ValidationError({"appointment_date": reason})
