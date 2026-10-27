"""Cross-hospital isolation probes (release-blocking if any fail).

Hospital B owns one synthetic record of every hospital-owned model. A staff
admin who belongs only to Hospital A then calls every list and detail route.
Any Hospital B record that comes back is a tenant-isolation defect.

The shared patient is a member of both hospitals, which is the case the
documentation calls out: one verified identity across hospitals, but
"Hospital A must not automatically see Hospital B's clinical records".
"""

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import get_resolver
from rest_framework.test import APIClient

from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffHospitalMembership, StaffProfile, StaffRole

from .factory import SyntheticFactory

User = get_user_model()

# Apps whose rows belong to a hospital (directly or through a parent row).
TENANT_APPS = {
    "appointments", "billing", "bloodbank", "clinical", "compounder", "doctors",
    "emergency", "encounters", "ipd", "laboratory", "notifications", "nurses",
    "pharmacy", "procurement", "ai_scribe", "audit", "hospital", "reports",
    "documents", "consent", "patients",
}
# Platform-wide reference data, not owned by a hospital.
GLOBAL_MODELS = {
    "hospital.Hospital",           # listing is filtered by membership separately
    "ai_scribe.ClinicalExtractionSchema",
    "ai_scribe.AIPromptTemplate",
    "reports.ReportTemplate",
    "patients.Patient",            # shared identity; covered by its own test
    "patients.PatientHospital",
    "notifications.OTPVerification",
}


def _walk(patterns, prefix=""):
    for p in patterns:
        if hasattr(p, "url_patterns"):
            yield from _walk(p.url_patterns, prefix + str(p.pattern))
        else:
            yield prefix + str(p.pattern), p.callback


def _route_model(callback):
    cls = getattr(callback, "cls", None)
    if cls is None:
        return None
    qs = getattr(cls, "queryset", None)
    if qs is not None:
        return qs.model
    serializer = getattr(cls, "serializer_class", None)
    meta = getattr(serializer, "Meta", None)
    return getattr(meta, "model", None)


def _list_routes():
    routes = {}
    for route, callback in _walk(get_resolver().url_patterns):
        actions = getattr(callback, "actions", None) or {}
        if "<" in route or "format" in route or actions.get("get") != "list":
            continue
        model = _route_model(callback)
        if model is None:
            continue
        url = "/" + route.replace("^", "").replace("$", "")
        routes.setdefault(model._meta.label, url)
    return routes


def _ids(payload):
    if isinstance(payload, dict):
        payload = payload.get("results", payload.get("data", []))
    if not isinstance(payload, list):
        return set()
    return {row.get("id") for row in payload if isinstance(row, dict)}


def make_staff(username, hospital, role=StaffRole.ADMIN):
    user = User.objects.create_user(username=username, password="synthetic-Pass-123")
    profile = StaffProfile.objects.create(
        user=user, role=role, employee_id=f"EMP-{username}", is_active_staff=True
    )
    StaffHospitalMembership.objects.create(staff=profile, hospital=hospital, role=role, is_active=True)
    return user, profile


def put_in_care(user, hospital, *patients):
    """
    Give a Doctor login its Doctor profile in ``hospital`` and an OPD visit
    with each patient, so those patients are in that doctor's care.
    """
    from doctors.models import Doctor
    from encounters.models import Visit

    doctor, _ = Doctor.objects.get_or_create(
        user=user, hospital=hospital,
        defaults={"name": f"Dr {user.username}", "specialization": "General", "phone": "9000000999"},
    )
    for patient in patients:
        Visit.objects.create(patient=patient, hospital=hospital, doctor=doctor)
    return doctor


def put_on_duty(user, hospital, ward):
    """Give a Nurse login its Nurse profile and today's Morning duty in ``ward``."""
    from config.hospital_time import hospital_today
    from nurses.models import Nurse, NurseWardAssignment

    nurse, _ = Nurse.objects.get_or_create(
        user=user, hospital=hospital, defaults={"name": f"Nurse {user.username}", "phone": "9000000998"},
    )
    NurseWardAssignment.objects.create(
        nurse=nurse, ward=ward, hospital=hospital, shift="Morning", shift_date=hospital_today(),
    )
    return nurse


class TenantIsolationProbe(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital_a = Hospital.objects.create(name="Synthetic Hospital A", is_active=True)
        cls.hospital_b = Hospital.objects.create(name="Synthetic Hospital B", is_active=True)
        cls.user_a, _ = make_staff("admin_a", cls.hospital_a)
        cls.user_b, cls.profile_b = make_staff("admin_b", cls.hospital_b)

        cls.shared_patient = Patient.objects.create(
            name="Synthetic Shared", age=40, gender="Female", phone="9000000001",
            hospital=cls.hospital_b,
        )
        PatientHospital.objects.create(patient=cls.shared_patient, hospital=cls.hospital_a, uhid="A-1")
        PatientHospital.objects.create(patient=cls.shared_patient, hospital=cls.hospital_b, uhid="B-1")

        factory = SyntheticFactory(fixed={
            "hospital.Hospital": cls.hospital_b,
            "patients.Patient": cls.shared_patient,
            User._meta.label: cls.user_b,
            "users.StaffProfile": cls.profile_b,
        })
        cls.b_records = {}
        cls.unbuildable = {}
        for model in apps.get_models():
            label = model._meta.label
            if model._meta.app_label not in TENANT_APPS or label in GLOBAL_MODELS:
                continue
            try:
                cls.b_records[label] = factory.get(model)
            except Exception as exc:  # recorded, reported below
                cls.unbuildable[label] = f"{type(exc).__name__}: {exc}"[:160]

    def setUp(self):
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user_a)

    def test_hospital_a_cannot_list_or_read_hospital_b_records(self):
        routes = _list_routes()
        leaks, errors, checked = [], [], []
        for label, obj in sorted(self.b_records.items()):
            url = routes.get(label)
            if not url:
                continue
            checked.append(label)
            for query in ("", f"?hospital={self.hospital_a.id}"):
                resp = self.client.get(url + query)
                if resp.status_code >= 500:
                    errors.append(f"{label} LIST {url}{query} -> {resp.status_code}")
                elif resp.status_code == 200 and obj.pk in _ids(resp.json()):
                    leaks.append(f"{label} LIST {url}{query}")
            detail = f"{url}{obj.pk}/"
            resp = self.client.get(detail)
            if resp.status_code == 200:
                leaks.append(f"{label} DETAIL {detail}")
            elif resp.status_code >= 500:
                errors.append(f"{label} DETAIL {detail} -> {resp.status_code}")
        report = (
            f"\nchecked={len(checked)} unbuildable={self.unbuildable}\nunrouted={sorted(set(self.b_records)-set(checked))}\n"
            + "LEAKS:\n  " + "\n  ".join(leaks or ["none"])
            + "\nSERVER ERRORS:\n  " + "\n  ".join(errors or ["none"])
        )
        print(report)
        self.assertEqual(leaks, [], report)
        self.assertEqual(errors, [], report)

    def test_hospital_a_cannot_query_hospital_b_by_parameter(self):
        """Passing another hospital's id must be rejected, not honoured."""
        for url in ("/api/patients/", "/api/encounters/visits/", "/api/billing/invoices/"):
            resp = self.client.get(f"{url}?hospital={self.hospital_b.id}")
            self.assertIn(resp.status_code, (403, 404), url)

    def test_malformed_hospital_parameter_is_client_error(self):
        resp = self.client.get("/api/patients/?hospital=not-a-number")
        self.assertLess(resp.status_code, 500)
