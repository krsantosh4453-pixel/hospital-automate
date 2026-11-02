"""
Longitudinal record of one patient (requirements B9, D12): every clinical
event at the given hospitals, newest first, as plain rows for a timeline.

``for_patient=True`` is the patient's own read-only view: only released lab
results and signed imaging reports, and no doctor or nursing notes.
"""

from datetime import datetime, time

from django.utils import timezone

MAX_EVENTS = 300


def _when(value):
    """Datetimes as-is, dates at midnight local time, so all events sort together."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return timezone.make_aware(datetime.combine(value, time.min))


def _event(when, kind, title, detail="", hospital=None, ref=None):
    return {"when": _when(when), "kind": kind, "title": title, "detail": detail or "",
            "hospital": getattr(hospital, "name", ""), "ref": ref}


def _visits(patient, hospital_ids, **_):
    from encounters.models import Visit

    for v in Visit.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("doctor", "hospital"):
        doctor = f" with {v.doctor.name}" if v.doctor else ""
        yield _event(v.visit_date, "Visit", f"{v.visit_type} visit{doctor}", v.chief_complaint, v.hospital, v.pk)


def _diagnoses(patient, hospital_ids, **_):
    from clinical.models import Diagnosis

    rows = Diagnosis.objects.filter(visit__patient=patient, visit__hospital_id__in=hospital_ids).select_related("visit__hospital")
    for d in rows:
        code = f" ({d.icd10_code})" if d.icd10_code else ""
        yield _event(d.created_at, "Diagnosis", f"{d.diagnosis_type}: {d.name}{code}", d.remarks, d.visit.hospital, d.pk)


def _notes(patient, hospital_ids, for_patient=False, **_):
    if for_patient:
        return
    from clinical.models import ClinicalNote

    rows = ClinicalNote.objects.filter(visit__patient=patient, visit__hospital_id__in=hospital_ids).select_related("doctor", "visit__hospital")
    for n in rows:
        yield _event(n.created_at, "Doctor note", n.doctor.name if n.doctor else "Doctor note", n.as_text(), n.visit.hospital, n.pk)


def _vitals(patient, hospital_ids, **_):
    from clinical.models import VitalSign

    rows = VitalSign.objects.filter(visit__patient=patient, visit__hospital_id__in=hospital_ids).select_related("visit__hospital")
    for v in rows:
        parts = [
            f"BP {v.systolic_bp}/{v.diastolic_bp}" if v.systolic_bp and v.diastolic_bp else "",
            f"Pulse {v.heart_rate}" if v.heart_rate else "",
            f"SpO₂ {v.spo2}%" if v.spo2 else "",
            f"Temp {v.temperature}°C" if v.temperature else "",
        ]
        yield _event(v.recorded_at, "Vitals", "Vital signs", " · ".join(p for p in parts if p), v.visit.hospital, v.pk)


def _prescriptions(patient, hospital_ids, **_):
    from clinical.models import Prescription

    rows = Prescription.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital").prefetch_related("items")
    for p in rows:
        medicines = ", ".join(f"{i.name} {i.dosage}".strip() for i in p.items.all())
        yield _event(p.created_at, "Prescription", f"Prescription ({p.status})", medicines, p.hospital, p.pk)


def _lab(patient, hospital_ids, for_patient=False, **_):
    from laboratory.models import LabTest

    rows = LabTest.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital")
    if for_patient:
        rows = rows.filter(status="Released")
    for t in rows:
        released = t.status == "Released"
        detail = t.result if released else f"Status: {t.status}"
        yield _event((t.released_at if released else None) or t.test_date, "Lab", t.name, detail, t.hospital, t.pk)


def _imaging(patient, hospital_ids, for_patient=False, **_):
    from laboratory.models import ImagingStudy

    rows = ImagingStudy.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital")
    if for_patient:
        rows = rows.filter(status=ImagingStudy.Status.REPORTED)
    for s in rows:
        reported = s.status == ImagingStudy.Status.REPORTED
        detail = s.impression if reported else f"Status: {s.status}"
        yield _event((s.reported_at if reported else None) or s.ordered_at, "Imaging", f"{s.modality} {s.body_part}", detail, s.hospital, s.pk)


def _admissions(patient, hospital_ids, **_):
    from ipd.models import Admission

    for a in Admission.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital"):
        yield _event(a.admission_date, "Admission", "Admitted", a.reason, a.hospital, a.pk)
        if a.discharge_date:
            yield _event(a.discharge_date, "Discharge", "Discharged", "", a.hospital, a.pk)


def _emergency(patient, hospital_ids, **_):
    from emergency.models import EmergencyVisit

    for e in EmergencyVisit.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital"):
        detail = e.discharge_diagnosis or f"Triage {e.triage_level} · {e.status}"
        yield _event(e.arrival_time, "Emergency", f"ER visit {e.visit_number}", detail, e.hospital, e.pk)


def _nursing(patient, hospital_ids, for_patient=False, **_):
    if for_patient:
        return
    from nurses.models import NursingNote

    rows = NursingNote.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital")
    for n in rows:
        yield _event(n.created_at, "Nursing note", n.get_note_type_display(), n.note, n.hospital, n.pk)


def _immunizations(patient, hospital_ids, **_):
    from clinical.models import Immunization

    for i in Immunization.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital"):
        yield _event(i.administered_on, "Vaccination", f"{i.vaccine} (dose {i.dose_number})", i.notes, i.hospital, i.pk)


def _documents(patient, hospital_ids, **_):
    from clinical.models import MedicalCertificate, Referral

    for c in MedicalCertificate.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital"):
        yield _event(c.issued_at, "Certificate", f"Medical certificate ({c.kind})", c.diagnosis, c.hospital, c.pk)
    for r in Referral.objects.filter(patient=patient, hospital_id__in=hospital_ids).select_related("hospital", "referred_to_doctor"):
        target = r.referred_to_doctor.name if r.referred_to_doctor else r.referred_to_external
        yield _event(r.created_at, "Referral", f"Referred to {target}", r.reason, r.hospital, r.pk)


SOURCES = [
    _visits, _diagnoses, _notes, _vitals, _prescriptions, _lab, _imaging,
    _admissions, _emergency, _nursing, _immunizations, _documents,
]


def build_timeline(patient, hospital_ids, for_patient=False):
    hospital_ids = list(hospital_ids)
    events = [
        event
        for source in SOURCES
        for event in (source(patient, hospital_ids, for_patient=for_patient) or [])
        if event["when"] is not None
    ]
    events.sort(key=lambda event: event["when"], reverse=True)
    return events[:MAX_EVENTS]
