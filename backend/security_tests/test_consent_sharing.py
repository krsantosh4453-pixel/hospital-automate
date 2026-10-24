"""Consent forms and patient-controlled record sharing (end-to-end scenario 13)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from clinical.models import Diagnosis
from consent.models import RecordShare
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

User = get_user_model()


class RecordSharingTests(TestCase):
    def setUp(self):
        self.a = Hospital.objects.create(name="Synthetic Share A", is_active=True)
        self.b = Hospital.objects.create(name="Synthetic Share B", is_active=True)
        self.c = Hospital.objects.create(name="Synthetic Share C", is_active=True)
        self.doctor_b, _ = make_staff("share_doc_b", self.b, role=StaffRole.DOCTOR)
        self.reception_b, _ = make_staff("share_rec_b", self.b, role=StaffRole.RECEPTIONIST)
        self.doctor_c, _ = make_staff("share_doc_c", self.c, role=StaffRole.DOCTOR)
        self.login = User.objects.create_user(username="share_patient", password="Synthetic-Pass-123")
        self.patient = Patient.objects.create(name="Synthetic Sharer", age=60, gender="Female",
                                              phone="9000000060", hospital=self.a, user=self.login)
        PatientHospital.objects.create(patient=self.patient, hospital=self.a, uhid="SA-1")
        visit = Visit.objects.create(patient=self.patient, hospital=self.a)
        Diagnosis.objects.create(visit=visit, name="Type 2 diabetes", icd10_code="E11")

    def patient_client(self):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.login)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.a.id))
        return client

    def staff(self, user, hospital):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(hospital.id))
        return client

    def grant(self, **overrides):
        body = {
            "recipient_hospital": self.b.id, "scope": ["diagnoses"], "purpose": "Second opinion",
            "expires_at": (timezone.now() + timedelta(days=7)).isoformat(),
        }
        body.update(overrides)
        return self.patient_client().post("/api/consent/shares/", body, format="json")

    def test_share_read_then_revoke(self):
        resp = self.grant()
        self.assertEqual(resp.status_code, 201, resp.content)
        share_id = resp.json()["id"]

        received = self.staff(self.doctor_b, self.b).get("/api/consent/shares/received/").json()
        self.assertEqual([s["id"] for s in received["results"]], [share_id])

        records = self.staff(self.doctor_b, self.b).get(f"/api/consent/shares/{share_id}/records/")
        self.assertEqual(records.status_code, 200, records.content)
        self.assertEqual([d["name"] for d in records.json()["records"]["diagnoses"]], ["Type 2 diabetes"])
        self.assertNotIn("prescriptions", records.json()["records"])

        # Non-clinical staff at the recipient and a third hospital get nothing.
        self.assertEqual(self.staff(self.reception_b, self.b).get(f"/api/consent/shares/{share_id}/records/").status_code, 403)
        self.assertEqual(self.staff(self.doctor_c, self.c).get(f"/api/consent/shares/{share_id}/records/").status_code, 404)

        log = self.patient_client().get(f"/api/consent/shares/{share_id}/access-log/").json()["results"]
        self.assertEqual([row["accessed_by"] for row in log], ["share_doc_b"])

        self.assertEqual(self.patient_client().post(f"/api/consent/shares/{share_id}/revoke/").status_code, 200)
        after = self.staff(self.doctor_b, self.b).get(f"/api/consent/shares/{share_id}/records/")
        self.assertEqual(after.status_code, 403)

    def test_expired_share_denied(self):
        share_id = self.grant().json()["id"]
        RecordShare.objects.filter(pk=share_id).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.staff(self.doctor_b, self.b).get(f"/api/consent/shares/{share_id}/records/").status_code, 403)

    def test_share_validation(self):
        self.assertEqual(self.grant(scope=["everything"]).status_code, 400)
        self.assertEqual(self.grant(expires_at=(timezone.now() + timedelta(days=900)).isoformat()).status_code, 400)
        self.assertEqual(self.grant(recipient_hospital=self.a.id).status_code, 400)

    def test_consent_form_sign_and_revoke(self):
        client = self.patient_client()
        missing = client.post("/api/consent/records/", {"form": "ai-recording", "signed_name": "Synthetic Sharer"}, format="json")
        self.assertEqual(missing.status_code, 400)
        signed = client.post("/api/consent/records/", {
            "form": "ai-recording", "signed_name": "Synthetic Sharer", "confirm": True,
        }, format="json")
        self.assertEqual(signed.status_code, 201, signed.content)
        self.assertEqual(signed.json()["form_version"], "1.0")
        revoked = client.post(f"/api/consent/records/{signed.json()['id']}/revoke/")
        self.assertEqual(revoked.status_code, 200)
        self.assertFalse(revoked.json()["is_active"])
