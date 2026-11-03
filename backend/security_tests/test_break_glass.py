"""Break-glass emergency access and sensitive-read auditing (synthetic data only)."""

import json
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from audit.models import AuditLog, BreakGlassAccess
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff, put_in_care

PATIENTS = "/api/patients/"
BREAK_GLASS = "/api/audit/break-glass/"
REASON = "Unconscious patient brought in, treating doctor unavailable"


def ids(response):
    body = response.json()
    rows = body["results"] if isinstance(body, dict) and "results" in body else body
    return {row["id"] for row in rows}


class BreakGlassTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hospital = Hospital.objects.create(name="Synthetic Glass A", is_active=True)
        cls.other_hospital = Hospital.objects.create(name="Synthetic Glass B", is_active=True)
        cls.doctor, _ = make_staff("glass_doctor", cls.hospital, role=StaffRole.DOCTOR)
        cls.admin, _ = make_staff("glass_admin", cls.hospital, role=StaffRole.ADMIN)
        cls.reception, _ = make_staff("glass_reception", cls.hospital, role=StaffRole.RECEPTIONIST)
        cls.mine = cls.make_patient("Synthetic Glass Mine", "9000000801", cls.hospital)
        cls.stranger = cls.make_patient("Synthetic Glass Stranger", "9000000802", cls.hospital)
        cls.elsewhere = cls.make_patient("Synthetic Glass Elsewhere", "9000000803", cls.other_hospital)
        put_in_care(cls.doctor, cls.hospital, cls.mine)

    @staticmethod
    def make_patient(name, phone, hospital):
        patient = Patient.objects.create(name=name, age=50, gender="Male", phone=phone, hospital=hospital)
        PatientHospital.objects.create(patient=patient, hospital=hospital, uhid=f"G-{phone}")
        return patient

    def api(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def open_grant(self, patient=None, reason=REASON):
        return self.api(self.doctor).post(
            BREAK_GLASS, {"patient": (patient or self.stranger).id, "reason": reason}, format="json",
        )

    def test_grant_brings_patient_into_care_until_it_ends(self):
        doctor = self.api(self.doctor)
        self.assertEqual(doctor.get(f"{PATIENTS}{self.stranger.id}/").status_code, 404)

        response = self.open_grant()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn(self.stranger.id, ids(doctor.get(PATIENTS)))
        self.assertEqual(doctor.get(f"{PATIENTS}{self.stranger.id}/").status_code, 200)

        grant_id = response.json()["id"]
        self.assertEqual(doctor.post(f"{BREAK_GLASS}{grant_id}/end/").status_code, 200)
        self.assertNotIn(self.stranger.id, ids(doctor.get(PATIENTS)))
        actions = set(AuditLog.objects.filter(user=self.doctor).values_list("action", flat=True))
        self.assertTrue({"break_glass.open", "break_glass.end"} <= actions)

    def test_grant_lapses_on_its_own(self):
        self.open_grant()
        BreakGlassAccess.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertNotIn(self.stranger.id, ids(self.api(self.doctor).get(PATIENTS)))

    @override_settings(BREAK_GLASS_DURATION_MINUTES=15)
    def test_duration_comes_from_settings(self):
        self.open_grant()
        grant = BreakGlassAccess.objects.get()
        self.assertAlmostEqual((grant.expires_at - grant.created_at).total_seconds(), 15 * 60, delta=5)

    def test_reopening_returns_the_active_grant(self):
        self.assertEqual(self.open_grant().status_code, 201)
        self.assertEqual(self.open_grant().status_code, 200)
        self.assertEqual(BreakGlassAccess.objects.count(), 1)

    def test_short_reason_is_refused(self):
        self.assertEqual(self.open_grant(reason="emergency").status_code, 400)
        self.assertFalse(BreakGlassAccess.objects.exists())

    def test_only_doctors_and_nurses_may_break_glass(self):
        response = self.api(self.reception).post(
            BREAK_GLASS, {"patient": self.stranger.id, "reason": REASON}, format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_patient_of_another_hospital_is_refused(self):
        self.assertEqual(self.open_grant(patient=self.elsewhere).status_code, 400)

    def test_admin_reviews_and_doctor_cannot_review_own(self):
        grant_id = self.open_grant().json()["id"]
        self.assertEqual(self.api(self.doctor).post(f"{BREAK_GLASS}{grant_id}/review/").status_code, 403)

        admin = self.api(self.admin)
        self.assertEqual(ids(admin.get(f"{BREAK_GLASS}?pending_review=true")), {grant_id})
        response = admin.post(f"{BREAK_GLASS}{grant_id}/review/", {"note": "Justified."}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["reviewed_by_username"], "glass_admin")
        self.assertEqual(ids(admin.get(f"{BREAK_GLASS}?pending_review=true")), set())
        self.assertEqual(admin.post(f"{BREAK_GLASS}{grant_id}/review/").status_code, 400)

    def test_reads_are_audited_and_break_glass_rows_are_marked(self):
        doctor = self.api(self.doctor)
        doctor.get(PATIENTS)
        listed = AuditLog.objects.filter(user=self.doctor, action="patients.patient.list").latest("id")
        self.assertEqual(json.loads(listed.details)["patient_ids"], [self.mine.id])
        self.assertEqual(listed.hospital_id, self.hospital.id)

        self.open_grant()
        doctor.get(f"{PATIENTS}{self.stranger.id}/")
        read = AuditLog.objects.filter(user=self.doctor, action="patients.patient.read").latest("id")
        self.assertEqual(read.object_id, str(self.stranger.id))
        self.assertEqual(json.loads(read.details)["break_glass_patient_ids"], [self.stranger.id])

    def test_reading_audit_logs_is_not_itself_logged(self):
        self.api(self.admin).get("/api/audit/audit-logs/")
        self.assertFalse(AuditLog.objects.filter(action__startswith="audit.").exists())
