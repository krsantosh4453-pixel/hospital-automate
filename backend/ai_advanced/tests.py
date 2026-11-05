"""Discharge summary AI assist (K6): drafts only, never saved without a clinician."""

import json
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from ai_scribe.services.llm import ClinicalExtractionResult
from audit.models import AIInteraction, AuditLog
from clinical.models import ClinicalNote, Diagnosis, VitalSign
from encounters.models import Visit
from hospital.models import Hospital
from ipd.models import Admission, DischargePlan, DischargeSummary
from laboratory.models import LabTest
from patients.models import Patient
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

from .discharge import SECTIONS, TO_COMPLETE, draft_discharge_summary


class FakeProvider:
    provider_name = "fake"
    default_model = "fake-model"

    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.prompts = reply, error, []

    def generate(self, system_prompt, user_prompt, model, **kwargs):
        self.prompts.append(user_prompt)
        if self.error:
            raise self.error
        return ClinicalExtractionResult(
            structured_extraction=self.reply, summary="", provider="fake", model=model,
            prompt_version="discharge-v1", metadata={},
        )


class DischargeDraftTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic Discharge Hospital", is_active=True)
        self.other = Hospital.objects.create(name="Synthetic Other Hospital", is_active=True)
        self.patient = Patient.objects.create(name="Synthetic Inpatient", age=64, gender="Male",
                                              phone="9000000091", hospital=self.hospital)
        self.doctor_user, _ = make_staff("dd_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = put_in_care(self.doctor_user, self.hospital, self.patient)
        self.admission = Admission.objects.create(
            patient=self.patient, hospital=self.hospital, reason="Community-acquired pneumonia",
            admitting_doctor=self.doctor,
        )
        Admission.objects.filter(pk=self.admission.pk).update(admission_date=timezone.now() - timedelta(days=3))
        self.admission.refresh_from_db()
        visit = Visit.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor)
        Diagnosis.objects.create(visit=visit, name="Pneumonia, unspecified organism", icd10_code="J18.9")
        VitalSign.objects.create(visit=visit, heart_rate=88, spo2=95)
        ClinicalNote.objects.create(visit=visit, doctor=self.doctor, note="Afebrile for 48h on IV antibiotics.")
        LabTest.objects.create(hospital=self.hospital, patient=self.patient, name="CBC", status="Released",
                               result="WBC 9.1", released_at=timezone.now())
        DischargePlan.objects.create(admission=self.admission, instructions="Complete oral antibiotics for 5 days.")

    def client_for(self, user, hospital=None):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str((hospital or self.hospital).id))
        return client

    def draft_url(self, admission=None):
        return f"/api/ai/discharge/admissions/{(admission or self.admission).pk}/draft/"

    @mock.patch("ai_advanced.discharge._llm_provider", return_value=None)
    def test_records_draft_without_a_model(self, _):
        resp = self.client_for(self.doctor_user).post(self.draft_url())
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body["source"], "records")
        for expected in ("Community-acquired pneumonia", "Pneumonia, unspecified organism [J18.9]",
                         "CBC: WBC 9.1", "Afebrile for 48h", "Complete oral antibiotics", TO_COMPLETE):
            self.assertIn(expected, body["text"])
        self.assertTrue(body["warnings"])
        # A draft only: nothing is written to the discharge summary.
        self.assertFalse(DischargeSummary.objects.exists())
        interaction = AIInteraction.objects.get(pk=body["draft_id"])
        self.assertEqual((interaction.patient, interaction.status), (self.patient, "Discharge Draft"))
        self.assertTrue(AuditLog.objects.filter(action="ai.discharge_draft.generated").exists())

    def test_model_draft_uses_record_without_identifiers(self):
        reply = {key: f"{heading} text" for key, heading in SECTIONS}
        provider = FakeProvider(reply=reply)
        _, draft = draft_discharge_summary(self.admission, provider=provider)
        self.assertEqual((draft.source, draft.provider, draft.model), ("llm", "fake", "fake-model"))
        self.assertIn("Hospital course:\nHospital course text", draft.text)
        sent = json.loads(provider.prompts[0].split("\n", 1)[1])
        self.assertEqual(sent["reason_for_admission"], "Community-acquired pneumonia")
        self.assertNotIn("Synthetic Inpatient", provider.prompts[0])
        self.assertNotIn("9000000091", provider.prompts[0])

    def test_model_failure_falls_back_to_records(self):
        _, draft = draft_discharge_summary(self.admission, provider=FakeProvider(error=RuntimeError("down")))
        self.assertEqual(draft.source, "records")
        self.assertIn("could not produce", draft.warnings[0])
        _, empty = draft_discharge_summary(self.admission, provider=FakeProvider(reply={}))
        self.assertEqual(empty.source, "records")

    @mock.patch("ai_advanced.discharge._llm_provider", return_value=None)
    def test_review_is_recorded_once(self, _):
        draft_id = self.client_for(self.doctor_user).post(self.draft_url()).json()["draft_id"]
        url = f"/api/ai/discharge/admissions/{self.admission.pk}/draft-review/"
        client = self.client_for(self.doctor_user)
        self.assertEqual(client.post(url, {"draft_id": draft_id, "outcome": "maybe"}).status_code, 400)
        resp = client.post(url, {"draft_id": draft_id, "outcome": "edited"})
        self.assertEqual(resp.status_code, 200, resp.content)
        interaction = AIInteraction.objects.get(pk=draft_id)
        self.assertEqual((interaction.status, interaction.reviewed_by), ("Discharge Draft Edited", self.doctor))
        self.assertEqual(client.post(url, {"draft_id": draft_id, "outcome": "accepted"}).status_code, 404)

    @mock.patch("ai_advanced.discharge._llm_provider", return_value=None)
    def test_only_doctors_of_the_hospital(self, _):
        nurse, _ = make_staff("dd_nurse", self.hospital, role=StaffRole.NURSE)
        self.assertEqual(self.client_for(nurse).post(self.draft_url()).status_code, 403)
        outsider, _ = make_staff("dd_outsider", self.other, role=StaffRole.DOCTOR)
        self.assertEqual(self.client_for(outsider, self.other).post(self.draft_url()).status_code, 404)
        self.assertEqual(self.client_for(self.doctor_user).get(self.draft_url()).status_code, 405)
