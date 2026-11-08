"""
Medication safety check for a prescription (KNOWN_LIMITATIONS F7, Phase A).

For each prescribed medicine the salts are taken from the hospital's
medicine catalogue (Medicine.generic_name) and from salt names written in the
text itself. They are then checked against the patient's recorded allergies,
each other (same salt twice) and the starter interaction list in
clinical/safety_rules.py. This is not a complete interaction database.
"""

import re

from . import safety_rules as rules

_SPLIT = re.compile(r"\s*(?:,|\+|/|;)\s*")


def _word(name):
    return re.compile(rf"\b{re.escape(name)}\b")


def _catalogue(hospital):
    """Catalogue names (lower-case) with their salts, longest name first."""
    from pharmacy.models import Medicine

    rows = (
        Medicine.objects.filter(hospital=hospital)
        .exclude(generic_name="")
        .values_list("name", "generic_name")
    )
    entries = {}
    for name, generic in rows:
        salts = {salt.lower() for salt in _SPLIT.split(generic.strip()) if salt}
        entries.setdefault(name.strip().lower(), set()).update(salts)
    return sorted(entries.items(), key=lambda entry: -len(entry[0]))


def salts_for(text, catalogue, known):
    """Salts of one prescribed medicine, from the catalogue and from the text."""
    lowered = (text or "").lower()
    salts = set()
    for name, catalogue_salts in catalogue:
        if name and _word(name).search(lowered):
            salts |= catalogue_salts
            break
    salts |= {salt for salt in known if _word(salt).search(lowered)}
    return salts


def _allergy_covers(allergen, prescribed_salts):
    """Salts an allergy recorded as ``allergen`` rules out."""
    allergen = allergen.lower()
    covered = set()
    for class_name, members in rules.ALLERGY_CLASSES.items():
        if re.search(rf"\b{re.escape(class_name)}s?\b", allergen):
            covered |= members
    covered |= {salt for salt in prescribed_salts if _word(salt).search(allergen)}
    return covered


def _alert(kind, severity, message, medicines, rule=None):
    return {"type": kind, "severity": severity, "message": message, "medicines": sorted(medicines), "rule": rule}


def check_items(hospital, patient, names):
    """Alerts for prescribing ``names`` (medicine text) to ``patient`` at ``hospital``."""
    from .models import Allergy

    catalogue = _catalogue(hospital)
    known = rules.known_salts()
    salts_by_item = {name: salts_for(name, catalogue, known) for name in names if name and name.strip()}
    alerts = []

    for name, salts in salts_by_item.items():
        if not salts:
            alerts.append(_alert(
                "unidentified", rules.INFO,
                "Salt not identified, so it was not checked. Add its generic name in Inventory.",
                [name],
            ))

    all_salts = set().union(*salts_by_item.values()) if salts_by_item else set()
    # P1-07 (owner's decision 2026-11-06): an allergy follows the patient to every
    # hospital in this system; one recorded elsewhere says where.
    allergies = Allergy.objects.filter(patient=patient).select_related("hospital") if patient else []
    for allergy in allergies:
        covered = _allergy_covers(allergy.name, all_salts)
        hits = [name for name, salts in salts_by_item.items() if salts & covered]
        if hits:
            reaction = f" ({allergy.reaction})" if allergy.reaction else ""
            elsewhere = ""
            if hospital is not None and allergy.hospital_id not in (None, hospital.pk):
                elsewhere = f" (recorded at {allergy.hospital.name})"
            alerts.append(_alert(
                "allergy", rules.HIGH,
                f"Recorded allergy: {allergy.name}{reaction}{elsewhere}.",
                hits, rule=f"allergy:{allergy.name.lower()}",
            ))

    for salt in sorted(all_salts):
        holders = [name for name, salts in salts_by_item.items() if salt in salts]
        if len(holders) > 1:
            alerts.append(_alert(
                "duplicate", rules.MODERATE,
                f"{salt.capitalize()} is prescribed more than once.",
                holders, rule=f"duplicate:{salt}",
            ))

    for rule in rules.INTERACTIONS:
        side_a = [name for name, salts in salts_by_item.items() if salts & rule["a"]]
        side_b = [name for name, salts in salts_by_item.items() if salts & rule["b"]]
        if side_a and side_b and set(side_a) | set(side_b) != set(side_a) & set(side_b):
            alerts.append(_alert("interaction", rule["severity"], rule["message"], set(side_a) | set(side_b), rule=rule["id"]))

    order = {rules.HIGH: 0, rules.MODERATE: 1, rules.INFO: 2}
    return sorted(alerts, key=lambda alert: order[alert["severity"]])


def blocking(alerts):
    return [alert for alert in alerts if alert["severity"] == rules.HIGH]
