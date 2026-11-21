"""
H-14: flag a laboratory result against the hospital's reference ranges.

The server decides the flags; the client's own flags are kept only for
parameters the hospital has no range for. A value that is not a plain number
(e.g. "<0.1", "positive") is recorded as *not checked*, never as normal.

Flags: "L" below the range, "H" above it, "LL" / "HH" at or beyond a critical
limit, "" inside the range.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

FLAG_LOW = "L"
FLAG_HIGH = "H"
FLAG_CRITICAL_LOW = "LL"
FLAG_CRITICAL_HIGH = "HH"
CRITICAL_FLAGS = (FLAG_CRITICAL_LOW, FLAG_CRITICAL_HIGH)


@dataclass(frozen=True)
class Evaluation:
    details: list = field(default_factory=list)
    reference_ranges: dict = field(default_factory=dict)
    abnormal_flags: list = field(default_factory=list)
    has_critical: bool = False


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _text(number):
    return None if number is None else format(number.normalize(), "f")


def flag_for(value, rng):
    """The flag for one numeric value against one range row."""
    if rng.critical_low is not None and value <= rng.critical_low:
        return FLAG_CRITICAL_LOW
    if rng.critical_high is not None and value >= rng.critical_high:
        return FLAG_CRITICAL_HIGH
    if rng.low is not None and value < rng.low:
        return FLAG_LOW
    if rng.high is not None and value > rng.high:
        return FLAG_HIGH
    return ""


def range_label(rng):
    """The range as the web and mobile reports already show it, e.g. "12-16 g/dL"."""
    if rng.low is not None and rng.high is not None:
        text = f"{_text(rng.low)}-{_text(rng.high)}"
    elif rng.low is not None:
        text = f">= {_text(rng.low)}"
    elif rng.high is not None:
        text = f"<= {_text(rng.high)}"
    else:
        text = ""
    return f"{text} {rng.unit}".strip()


def ranges_for(hospital_id, test_name, sex):
    """Active ranges for a test, keyed by lower-case parameter; a sex-specific row wins over "Any"."""
    from .models import LabReferenceRange

    if not hospital_id or not test_name:
        return {}
    rows = LabReferenceRange.objects.filter(hospital_id=hospital_id, test_name__iexact=test_name.strip(),
                                            is_active=True)
    chosen = {}
    for rng in rows:
        if rng.sex and rng.sex != sex:
            continue
        key = rng.parameter.strip().lower()
        if key not in chosen or (rng.sex and not chosen[key].sex):
            chosen[key] = rng
    return chosen


def _client_flag_names(client_flags):
    if isinstance(client_flags, dict):
        return [str(k) for k, v in client_flags.items() if v]
    if isinstance(client_flags, list):
        return [str(v) for v in client_flags if isinstance(v, (str, int)) and str(v).strip()]
    return []


def evaluate(hospital_id, test_name, sex, result_data, client_ranges=None, client_flags=None):
    """Flag ``result_data`` ({parameter: value}) against the hospital's ranges."""
    ranges = ranges_for(hospital_id, test_name, sex)
    details = []
    snapshot = {}
    flagged = []
    checked_keys = set()
    for parameter, raw in (result_data or {}).items():
        rng = ranges.get(str(parameter).strip().lower())
        if rng is None:
            continue
        checked_keys.add(str(parameter).strip().lower())
        snapshot[parameter] = range_label(rng)
        number = _number(raw)
        flag = flag_for(number, rng) if number is not None else ""
        if flag:
            flagged.append(parameter)
        details.append({
            "parameter": parameter,
            "value": str(raw),
            "unit": rng.unit,
            "low": _text(rng.low),
            "high": _text(rng.high),
            "critical_low": _text(rng.critical_low),
            "critical_high": _text(rng.critical_high),
            "flag": flag,
            "checked": number is not None,
        })

    # Parameters the hospital has no range for keep what the laboratory typed.
    if isinstance(client_ranges, dict):
        for parameter, value in client_ranges.items():
            if str(parameter).strip().lower() not in checked_keys:
                snapshot[parameter] = value
    for name in _client_flag_names(client_flags):
        if name.strip().lower() not in checked_keys and name not in flagged:
            flagged.append(name)

    return Evaluation(
        details=details,
        reference_ranges=snapshot,
        abnormal_flags=flagged,
        has_critical=any(d["flag"] in CRITICAL_FLAGS for d in details),
    )
