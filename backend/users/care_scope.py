"""
Care scope: the patients a Doctor or a Nurse may see.

In a hospital where the user's role is Doctor, patient data is limited to the
patients in that doctor's care: anyone with an appointment, OPD visit, queue
token or admission under one of the user's doctor profiles there.

Where the role is Nurse, it is limited to today's duty: patients admitted to a
bed in a ward the nurse is on duty in, patients assigned to the nurse for
today's shift, and today's OPD queue. Yesterday's Night shift still counts,
as it runs past midnight. Admitted patients still waiting for a bed are
visible to every nurse, so that one can be allocated.

Both roles see patients with an open emergency visit, so that no emergency is
hidden. Other roles, and other hospitals where the same user holds another
role, are not affected.
"""

from collections import deque
from datetime import timedelta
from functools import lru_cache

from django.apps import apps
from django.db import models
from django.db.models import Q

from config.hospital_time import hospital_today
from users.models import StaffRole
from users.permissions import get_user_active_hospital_memberships

PATIENT_LABEL = "patients.Patient"
SCOPED_ROLES = (StaffRole.DOCTOR, StaffRole.NURSE)
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
NIGHT_SHIFT = "Night"
MAX_PATH_DEPTH = 3


def _scoped_roles(user, hospital_ids):
    """{hospital_id: role} for the hospitals where the user is a Doctor or a Nurse."""
    memberships = get_user_active_hospital_memberships(user).filter(
        hospital_id__in=list(hospital_ids), role__in=SCOPED_ROLES
    )
    return dict(memberships.values_list("hospital_id", "role"))


def doctor_hospital_ids(user, hospital_ids):
    """The hospitals among ``hospital_ids`` where the user acts as a Doctor."""
    return {h for h, role in _scoped_roles(user, hospital_ids).items() if role == StaffRole.DOCTOR}


def _doctor_care(user, hospital_ids):
    in_care = Q(pk__in=[])
    for label, field in CARE_LINKS:
        rows = apps.get_model(label).objects.filter(
            **{f"{field}__user": user, "hospital_id__in": hospital_ids}
        )
        in_care |= Q(pk__in=rows.values("patient_id"))
    return in_care


def _nurse_care(user, hospital_ids):
    today = hospital_today()
    on_duty = Q(shift_date=today) | Q(shift_date=today - timedelta(days=1), shift=NIGHT_SHIFT)
    mine = {"is_active": True, "nurse__user": user, "hospital_id__in": hospital_ids}
    wards = apps.get_model("nurses.NurseWardAssignment").objects.filter(on_duty, **mine).values("ward_id")
    in_ward = apps.get_model("ipd.BedAllocation").objects.filter(
        is_active=True,
        admission__status="Admitted",
        admission__hospital_id__in=hospital_ids,
        bed__room__ward_id__in=wards,
    )
    # Admitted but no bed yet: any nurse may need to allocate one.
    awaiting_bed = apps.get_model("ipd.Admission").objects.filter(
        hospital_id__in=hospital_ids, status="Admitted"
    ).exclude(bed_allocations__is_active=True)
    direct = apps.get_model("nurses.PatientAssignment").objects.filter(on_duty, **mine)
    opd = apps.get_model("encounters.QueueToken").objects.filter(hospital_id__in=hospital_ids, token_date=today)
    return (
        Q(pk__in=in_ward.values("admission__patient_id"))
        | Q(pk__in=awaiting_bed.values("patient_id"))
        | Q(pk__in=direct.values("patient_id"))
        | Q(pk__in=opd.values("patient_id"))
    )


def patients_in_care(user, hospital_ids):
    """Subquery of the ids of patients in this user's care in those hospitals."""
    roles = _scoped_roles(user, hospital_ids)
    doctor_ids = [h for h, role in roles.items() if role == StaffRole.DOCTOR]
    nurse_ids = [h for h, role in roles.items() if role == StaffRole.NURSE]
    in_care = Q(pk__in=[])
    if doctor_ids:
        in_care |= _doctor_care(user, doctor_ids)
    if nurse_ids:
        in_care |= _nurse_care(user, nurse_ids)
    if roles:
        # Emergency care is team work: an open emergency visit is visible to
        # every doctor and nurse of the hospital, whoever is attending.
        open_emergencies = (
            apps.get_model("emergency.EmergencyVisit").objects
            .filter(hospital_id__in=list(roles))
            .exclude(status__in=CLOSED_EMERGENCY_STATUSES)
        )
        in_care |= Q(pk__in=open_emergencies.values("patient_id"))
    return apps.get_model(PATIENT_LABEL).objects.filter(in_care).values("pk")


@lru_cache(maxsize=None)
def resolve_patient_lookup(model):
    """
    ORM path from ``model`` to the patient a row is about, e.g. ``"pk"``,
    ``"patient_id"`` or ``"visit__patient_id"``. None when rows are not about
    one patient (schedules, beds, stock), which the care scope leaves alone.
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
    hospitals where the user is a Doctor or a Nurse are only those of patients
    in their care. ``in_hospitals(ids)`` returns the Q that places a row in
    those hospitals.
    """
    scoped_ids = set(_scoped_roles(user, hospital_ids))
    if not scoped_ids:
        return queryset
    patient_lookup = resolve_patient_lookup(queryset.model)
    if patient_lookup is None:
        return queryset
    other_ids = [h for h in hospital_ids if h not in scoped_ids]
    in_care = in_hospitals(scoped_ids) & Q(
        **{f"{patient_lookup}__in": patients_in_care(user, scoped_ids)}
    )
    visible = in_care | in_hospitals(other_ids) if other_ids else in_care
    return queryset.filter(visible)


def care_view_of(queryset, user, hospital_id):
    """
    The rows of this user's own work in ``hospital_id``, for home counts. A
    Doctor gets appointments, visits, queue tokens and admissions under their
    own profile, and other patient rows (lab, emergency, billing) of patients
    in their care; a Nurse gets every patient row of patients in their care.
    Rows not about a patient (beds, doctors) and other roles are unchanged.
    """
    role = _scoped_roles(user, [hospital_id]).get(hospital_id)
    if role is None:
        return queryset
    label = queryset.model._meta.label
    if role == StaffRole.DOCTOR:
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
    always outside Doctor/Nurse hospitals, otherwise only for a patient in care.
    """
    scoped_ids = set(_scoped_roles(user, hospital_ids))
    if not scoped_ids:
        return True
    other_ids = [h for h in hospital_ids if h not in scoped_ids]
    patients = apps.get_model(PATIENT_LABEL).objects.filter(pk=patient_id)
    if other_ids and patients.filter(
        Q(hospital_id__in=other_ids)
        | Q(hospital_memberships__hospital_id__in=other_ids, hospital_memberships__is_active=True)
    ).exists():
        return True
    return patients_in_care(user, scoped_ids).filter(pk=patient_id).exists()


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
    turned away, and an open emergency visit is visible to every clinician.
    """
    if model._meta.label == "emergency.EmergencyVisit":
        return True
    for label, field in CARE_LINKS:
        if model._meta.label == label:
            doctor = validated_data.get(field)
            return doctor is not None and doctor.user_id == user.pk
    return False
