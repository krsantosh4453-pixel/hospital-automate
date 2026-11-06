"""
AI-assisted discharge summary drafts (K6).

The draft is built from what was recorded during the admission (diagnoses,
clinical and nursing notes, vitals, medications, released lab results,
discharge plan). With an LLM configured (ai_scribe's provider registry) the
model writes the narrative from that data only; otherwise the draft is
assembled from the records directly. Either way it is only a draft: nothing
is saved to the discharge summary until a clinician reviews and saves it.
The model is never sent the patient's name or contact details.
"""

import json
import logging
from dataclasses import dataclass, field

from django.utils import timezone

logger = logging.getLogger(__name__)

TO_COMPLETE = "[clinician to complete]"
MAX_NOTES = 20
MAX_NOTE_CHARS = 800
MAX_ROWS = 40
LLM_MAX_TOKENS = 2000

# Sections of the draft, in order, with their printed headings.
SECTIONS = [
    ("reason_for_admission", "Reason for admission"),
    ("diagnoses", "Diagnoses"),
    ("hospital_course", "Hospital course"),
    ("investigations", "Investigations"),
    ("medications", "Medications"),
    ("condition_at_discharge", "Condition at discharge"),
    ("discharge_instructions", "Discharge instructions"),
    ("follow_up", "Follow-up"),
]

SYSTEM_PROMPT = """You draft hospital discharge summaries for a doctor to review.
Rules:
1. Use ONLY the facts in the admission record you are given. Never invent findings, results, doses or diagnoses.
2. Where the record has no information for a section, write exactly "[clinician to complete]".
3. Write concise clinical prose; list medications with dose and frequency as recorded.
4. Do not give new treatment advice that is not in the record.
5. Reply with ONLY a JSON object whose keys are: %s. Every value is a string.
A licensed clinician will review and edit the draft before it becomes part of the record.""" % ", ".join(
    key for key, _ in SECTIONS
)


@dataclass(frozen=True)
class DischargeDraft:
    sections: dict
    text: str
    source: str  # "llm" or "records"
    provider: str = ""
    model: str = ""
    warnings: list = field(default_factory=list)


def _fmt(value):
    return timezone.localtime(value).strftime("%d %b %Y %H:%M") if value else ""


def _window(admission):
    return admission.admission_date, admission.discharge_date or timezone.now()


def _vitals(patient_id, hospital_id, start, end):
    from clinical.models import VitalSign

    fields = ("recorded_at", "systolic_bp", "diastolic_bp", "heart_rate", "respiratory_rate",
              "temperature", "spo2", "blood_sugar")
    rows = list(VitalSign.objects.filter(
        visit__patient_id=patient_id, visit__hospital_id=hospital_id, recorded_at__range=(start, end)
    ).order_by("recorded_at").values(*fields))
    if not rows:
        return {}
    def clean(row):
        return {k: (_fmt(v) if k == "recorded_at" else str(v)) for k, v in row.items() if v is not None}

    return {"count": len(rows), "first": clean(rows[0]), "latest": clean(rows[-1])}


def _medications(admission, start, end):
    from clinical.models import PrescriptionItem
    from nurses.models import MAR

    meds = [
        f"{m['medicine_name']} {m['dose']} {m['route']} {m['frequency']}".strip()
        + ("" if m["is_active"] else " (stopped)")
        for m in MAR.objects.filter(admission=admission).values("medicine_name", "dose", "route", "frequency", "is_active")
    ]
    meds += [
        " ".join(filter(None, [i["name"], i["dosage"], i["frequency"], i["duration"] and f"for {i['duration']}"]))
        for i in PrescriptionItem.objects.filter(
            prescription__patient_id=admission.patient_id, prescription__hospital_id=admission.hospital_id,
            prescription__created_at__range=(start, end),
        ).values("name", "dosage", "frequency", "duration")
    ]
    return list(dict.fromkeys(meds))[:MAX_ROWS]


def _notes(admission, start, end):
    from clinical.models import ClinicalNote
    from ipd.models import DischargeNote
    from nurses.models import NursingNote

    notes = [("Doctor", n["created_at"], n["note"]) for n in ClinicalNote.objects.filter(
        visit__patient_id=admission.patient_id, visit__hospital_id=admission.hospital_id,
        created_at__range=(start, end),
    ).values("created_at", "note")]
    notes += [(f"Nursing ({n['note_type']})", n["created_at"], n["note"])
              for n in NursingNote.objects.filter(admission=admission).values("note_type", "created_at", "note")]
    notes += [("Discharge note", n["created_at"], n["note"])
              for n in DischargeNote.objects.filter(admission=admission).values("created_at", "note")]
    notes.sort(key=lambda n: n[1])
    return [{"by": by, "at": _fmt(at), "note": text[:MAX_NOTE_CHARS]} for by, at, text in notes[-MAX_NOTES:]]


def collect_admission_context(admission):
    """Everything recorded for ``admission`` that a discharge summary draws on."""
    from clinical.models import Allergy, Diagnosis
    from ipd.models import DischargePlan
    from laboratory.models import LabTest

    start, end = _window(admission)
    patient, hospital_id = admission.patient, admission.hospital_id
    plan = DischargePlan.objects.filter(admission=admission).first()
    return {
        "patient": {"age": patient.age, "gender": patient.gender},
        "admitted_at": _fmt(admission.admission_date),
        "discharged_at": _fmt(admission.discharge_date),
        "reason_for_admission": admission.reason,
        "allergies": [f"{a['name']}" + (f" ({a['reaction']})" if a["reaction"] else "")
                      for a in Allergy.objects.filter(patient=patient, hospital_id=hospital_id).values("name", "reaction")],
        "diagnoses": [f"{d['name']}" + (f" [{d['icd10_code']}]" if d["icd10_code"] else "") + f" - {d['diagnosis_type']}"
                      for d in Diagnosis.objects.filter(
                          visit__patient=patient, visit__hospital_id=hospital_id, created_at__range=(start, end),
                      ).values("name", "icd10_code", "diagnosis_type")[:MAX_ROWS]],
        "notes": _notes(admission, start, end),
        "vitals": _vitals(patient.pk, hospital_id, start, end),
        "medications": _medications(admission, start, end),
        "lab_results": [f"{t['name']}: {t['result'] or 'no result text'}" for t in LabTest.objects.filter(
            patient=patient, hospital_id=hospital_id, status="Released", released_at__range=(start, end),
        ).values("name", "result")[:MAX_ROWS]],
        "discharge_plan": {"instructions": plan.instructions, "pending_tasks": plan.pending_tasks} if plan else {},
    }


def _bullets(items):
    return "\n".join(f"- {item}" for item in items) if items else TO_COMPLETE


def sections_from_records(context):
    """A draft assembled from the records alone (no model)."""
    vitals = context["vitals"]
    vitals_line = ""
    if vitals:
        vitals_line = f"\nVitals: {vitals['count']} readings; latest {json.dumps(vitals['latest'])}."
    notes = context["notes"][-3:]
    course = "\n".join(f"{n['at']} {n['by']}: {n['note']}" for n in notes)
    plan = context["discharge_plan"]
    return {
        "reason_for_admission": context["reason_for_admission"] or TO_COMPLETE,
        "diagnoses": _bullets(context["diagnoses"]),
        "hospital_course": (f"Admitted {context['admitted_at']}. Recent notes:\n{course}" if course else TO_COMPLETE)
        + vitals_line,
        "investigations": _bullets(context["lab_results"]),
        "medications": _bullets(context["medications"]),
        "condition_at_discharge": TO_COMPLETE,
        "discharge_instructions": plan.get("instructions") or TO_COMPLETE,
        "follow_up": TO_COMPLETE,
    }


def render_text(sections, context):
    lines = []
    if context["allergies"]:
        lines.append("Allergies: " + ", ".join(context["allergies"]))
        lines.append("")
    for key, heading in SECTIONS:
        lines.append(f"{heading}:")
        lines.append(str(sections.get(key) or TO_COMPLETE).strip())
        lines.append("")
    return "\n".join(lines).strip()


def _llm_provider():
    """The configured real LLM provider, or None (the dev mock does not count)."""
    from ai_scribe.services.llm import LLMClinicalService, LLMGenerationError

    try:
        provider = LLMClinicalService().get_provider()
    except LLMGenerationError:
        return None
    return None if provider.provider_name == "development" else provider


def _sections_from_llm(provider, context):
    model = getattr(provider, "default_model", "")
    result = provider.generate(
        system_prompt=SYSTEM_PROMPT,
        user_prompt="Admission record (JSON):\n" + json.dumps(context, ensure_ascii=False),
        model=model,
        temperature=0.1,
        max_tokens=LLM_MAX_TOKENS,
        prompt_version="discharge-v1",
    )
    data = result.structured_extraction or {}
    if not isinstance(data, dict) or not any(data.get(key) for key, _ in SECTIONS):
        raise ValueError("The model returned no discharge summary sections.")
    return {key: str(data.get(key) or TO_COMPLETE) for key, _ in SECTIONS}, result.provider, result.model


def draft_discharge_summary(admission, provider=None):
    """Build a DischargeDraft for ``admission``; never raises for model errors."""
    context = collect_admission_context(admission)
    provider = provider if provider is not None else _llm_provider()
    warnings = []
    if provider is not None:
        try:
            sections, name, model = _sections_from_llm(provider, context)
            return context, DischargeDraft(sections, render_text(sections, context), "llm", name, model)
        except Exception as exc:  # model/network/parse errors fall back to the records draft
            logger.warning("Discharge draft LLM call failed for admission %s: %s", admission.pk, type(exc).__name__)
            warnings.append("The AI model could not produce a draft; this one is assembled from the records.")
    else:
        warnings.append("No AI model is configured; this draft is assembled from the records.")
    sections = sections_from_records(context)
    return context, DischargeDraft(sections, render_text(sections, context), "records", warnings=warnings)
