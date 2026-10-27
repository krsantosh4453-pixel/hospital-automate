"""
Doctor-only patient scope.

In a hospital where the user's role is Doctor, patient data is limited to the
patients in that doctor's care: anyone with an appointment, OPD visit, queue
token or admission under one of the user's doctor profiles there. Patients
with an open emergency visit stay visible to every doctor so that no
emergency is hidden. Other roles, and other hospitals where the same user
holds another role, are not affected.
"""

from collections import deque
from functools import lru_cache

from django.apps import apps
from django.db import models
from django.db.models import Q

from users.models import StaffRole
from users.permissions import get_user_active_hospital_memberships

PATIENT_LABEL = "patients.Patient"
# Relations that never lead to the patient a row is about.
_NOT_PATIENT_PATHS = {"hospital.Hospital", "auth.User", "users.StaffProfile", "doctors.Doctor"}
# (model, field naming the responsible doctor) that put a patient in a doctor's care.
CARE_LINKS = (
    ("appointments.Appointment", "doctor"),
    ("encounters.Visit", "doctor"),
    ("encounters.QueueToken", "doctor"),
    ("ipd.Admission", "admitting_doctor"),
    ("emergency.EmergencyVisit", "attending_doctor"),
)
CLOSED_EMERGENCY_STATUSES = ("Admitted", "Discharged", "Referred", "Left Against Advice", "Expired")
MAX_PATH_DEPTH = 3


def doctor_hospital_ids(user, hospital_ids):
    """The hospitals among ``hospital_ids`` where the user acts as a Doctor."""
    memberships = get_user_active_hospital_memberships(user).filter(
        hospital_id__in=list(hospital_ids), role=StaffRole.DOCTOR
    )
    return set(memberships.values_list("hospital_id", flat=True))


def patients_in_care(user, hospital_ids):
    """Subquery of the ids of patients in this doctor's care in those hospitals."""
    hospital_ids = list(hospital_ids)
    in_care = Q()
    for label, field in CARE_LINKS:
        rows = apps.get_model(label).objects.filter(
            **{f"{field}__user": user, "hospital_id__in": hospital_ids}
        )
        in_care |= Q(pk__in=rows.values("patient_id"))
    # Emergency care is team work: an open emergency visit is visible to
    # every doctor of the hospital, whoever is attending.
    open_emergencies = (
        apps.get_model("emergency.EmergencyVisit").objects
        .filter(hospital_id__in=hospital_ids)
        .exclude(status__in=CLOSED_EMERGENCY_STATUSES)
    )
    in_care |= Q(pk__in=open_emergencies.values("patient_id"))
    return apps.get_model(PATIENT_LABEL).objects.filter(in_care).values("pk")


@lru_cache(maxsize=None)
def resolve_patient_lookup(model):
    """
    ORM path from ``model`` to the patient a row is about, e.g. ``"pk"``,
    ``"patient_id"`` or ``"visit__patient_id"``. None when rows are not about
    one patient (schedules, beds, stock), which the doctor scope leaves alone.
    """
    if model._meta.label == PATIENT_LABEL:
        return "pk"
    queue = deque([(model, "")])
    seen = {model}
    while queue:
        current, prefix = queue.popleft()
        if prefix.count("__") >= MAX_PATH_DEPTH:
            continue
        relations = [
            f for f in current._meta.concrete_fields
            if isinstance(f, (models.ForeignKey, models.OneToOneField))
        ]
        for field in relations:
            if field.related_model._meta.label == PATIENT_LABEL:
                return f"{prefix}{field.name}_id"
        for field in relations:
            target = field.related_model
            if target in seen or target._meta.label in _NOT_PATIENT_PATHS:
                continue
            seen.add(target)
            queue.append((target, f"{prefix}{field.name}__"))
    return None


def limit_to_patients_in_care(queryset, user, hospital_ids, in_hospitals):
    """
    Narrow ``queryset`` (already limited to ``hospital_ids``) so that rows of
    hospitals where the user is a Doctor are only those of patients in their
    care. ``in_hospitals(ids)`` returns the Q that places a row in those
    hospitals.
    """
    doctor_ids = doctor_hospital_ids(user, hospital_ids)
    if not doctor_ids:
        return queryset
    patient_lookup = resolve_patient_lookup(queryset.model)
    if patient_lookup is None:
        return queryset
    other_ids = [h for h in hospital_ids if h not in doctor_ids]
    in_care = in_hospitals(doctor_ids) & Q(
        **{f"{patient_lookup}__in": patients_in_care(user, doctor_ids)}
    )
    visible = in_care | in_hospitals(other_ids) if other_ids else in_care
    return queryset.filter(visible)


def doctor_view_of(queryset, user, hospital_id):
    """
    For a Doctor in ``hospital_id``, the rows of their own work: appointments,
    visits, queue tokens and admissions under their own profile, and other
    patient rows (lab, emergency, billing) of patients in their care. Rows
    not about a patient (beds, doctors) and other roles are left unchanged.
    """
    if not doctor_hospital_ids(user, [hospital_id]):
        return queryset
    label = queryset.model._meta.label
    for care_label, field in CARE_LINKS:
        if label == care_label and label != "emergency.EmergencyVisit":
            return queryset.filter(**{f"{field}__user": user})
    lookup = resolve_patient_lookup(queryset.model)
    if lookup is None:
        return queryset
    return queryset.filter(**{f"{lookup}__in": patients_in_care(user, [hospital_id])})


def _patient_id_of(obj):
    """The id of the patient ``obj`` is about, or None."""
    lookup = resolve_patient_lookup(type(obj))
    if lookup is None:
        return None
    if lookup == "pk":
        return obj.pk
    current = obj
    for part in lookup.split("__")[:-1]:
        current = getattr(current, part, None)
        if current is None:
            return None
    return getattr(current, lookup.split("__")[-1], None)


def may_use_patient(user, patient_id, hospital_ids):
    """
    Whether the user may write a row about this patient in ``hospital_ids``:
    always outside Doctor hospitals, otherwise only for a patient in care.
    """
    doctor_ids = doctor_hospital_ids(user, hospital_ids)
    if not doctor_ids:
        return True
    other_ids = [h for h in hospital_ids if h not in doctor_ids]
    patients = apps.get_model(PATIENT_LABEL).objects.filter(pk=patient_id)
    if other_ids and patients.filter(
        Q(hospital_id__in=other_ids)
        | Q(hospital_memberships__hospital_id__in=other_ids, hospital_memberships__is_active=True)
    ).exists():
        return True
    return patients_in_care(user, doctor_ids).filter(pk=patient_id).exists()


def may_write_for_patients(user, model, validated_data, hospital_ids):
    """
    Whether every patient a write refers to (directly, or through a visit,
    admission, prescription and so on) may be used by this user.
    """
    if assigns_self_as_doctor(user, model, validated_data):
        return True
    patient_ids = {
        _patient_id_of(value) for value in validated_data.values() if isinstance(value, models.Model)
    }
    patient_ids.discard(None)
    return all(may_use_patient(user, pid, hospital_ids) for pid in patient_ids)


def assigns_self_as_doctor(user, model, validated_data):
    """
    True when the row being written puts the patient in this user's own care.
    Registering an emergency visit is always allowed: an emergency is never
    turned away, and an open emergency visit is visible to every doctor.
    """
    if model._meta.label == "emergency.EmergencyVisit":
        return True
    for label, field in CARE_LINKS:
        if model._meta.label == label:
            doctor = validated_data.get(field)
            return doctor is not None and doctor.user_id == user.pk
    return False
