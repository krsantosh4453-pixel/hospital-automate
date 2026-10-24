"""AI scribe clinical-safety workflow (synthetic data, mock providers allowed in tests)."""

import shutil
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from ai_scribe.models import AIConsultationDraft, ConsultationSession
from clinical.models import ClinicalNote
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from users.models import StaffRole

from .test_tenant_isolation import make_staff

MEDIA = tempfile.mkdtemp(prefix="hms-ai-test-")


@override_settings(MEDIA_ROOT=MEDIA)
class AIScribeSafetyTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic AI Hospital", is_active=True)
        self.user, _ = make_staff("ai_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.unlinked_user, _ = make_staff("ai_unlinked", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(
            hospital=self.hospital, user=self.user, name="Dr Synthetic", specialization="General", phone="9000000020"
        )
        self.patient = Patient.objects.create(
            name="Synthetic AI Patient", age=45, gender="Male", phone="9000000021", hospital=self.hospital
        )
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="AI-1")
        self.visit = Visit.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor)
        self.client = self._client(self.user)

    def _client(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def _session(self):
        resp = self.client.post("/api/ai/consultation-sessions/", {
            "visit": self.visit.id, "hospital": self.hospital.id, "patient": self.patient.id,
            "doctor": self.doctor.id, "language": "en",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()["id"]

    def _record_and_transcribe(self, session_id):
        base = f"/api/ai/consultation-sessions/{session_id}"
        self.assertEqual(self.client.post(f"{base}/start_recording/", {}, format="json").status_code, 400)
        self.assertEqual(
            self.client.post(f"{base}/start_recording/", {"patient_consent": True}, format="json").status_code, 200
        )
        audio = SimpleUploadedFile("c.webm", b"\x1aE\xdf\xa3synthetic", content_type="audio/webm;codecs=opus")
        resp = self.client.post(f"{base}/stop_recording/", {"audio_file": audio, "duration_seconds": 5},
                                format="multipart")
        self.assertEqual(resp.status_code, 200, resp.content)
        resp = self.client.post(f"{base}/transcribe/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        return AIConsultationDraft.objects.get(consultation_id=session_id)

    def test_draft_needs_clinician_approval_before_entering_record(self):
        session_id = self._session()
        draft = self._record_and_transcribe(session_id)
        self.assertTrue(ConsultationSession.objects.get(pk=session_id).recording_consent_at)

        resp = self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["review_label"], "AI Draft — Pending Review")
        self.assertFalse(ClinicalNote.objects.exists())

        # Clients cannot approve by editing fields.
        self.client.patch(f"/api/ai/drafts/{draft.id}/", {"status": "approved"}, format="json")
        draft.refresh_from_db()
        self.assertNotEqual(draft.status, "approved")
        self.assertFalse(ClinicalNote.objects.exists())

        # A doctor without a linked Doctor profile cannot approve.
        resp = self._client(self.unlinked_user).post(f"/api/ai/drafts/{draft.id}/approve/", {}, format="json")
        self.assertEqual(resp.status_code, 403)

        resp = self.client.post(f"/api/ai/drafts/{draft.id}/approve/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        note = ClinicalNote.objects.get()
        self.assertEqual(note.visit_id, self.visit.id)
        self.assertEqual(note.doctor_id, self.doctor.id)
        draft.refresh_from_db()
        self.assertEqual(draft.approved_by_id, self.doctor.id)

    @override_settings(AI_SCRIBE_ALLOW_MOCK_PROVIDERS=False)
    def test_mock_draft_cannot_be_approved_where_mocks_are_disallowed(self):
        session = ConsultationSession.objects.create(
            visit=self.visit, hospital=self.hospital, patient=self.patient, doctor=self.doctor
        )
        draft = AIConsultationDraft.objects.create(
            consultation=session, version=1, status="under_review", provider="development"
        )
        resp = self.client.post(f"/api/ai/drafts/{draft.id}/approve/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ClinicalNote.objects.exists())

    def test_provider_failure_does_not_touch_clinical_record(self):
        session_id = self._session()
        draft = self._record_and_transcribe(session_id)
        with mock.patch(
            "ai_scribe.services.llm.LLMClinicalService.generate_clinical_draft",
            side_effect=RuntimeError("provider timeout"),
        ):
            resp = self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
        self.assertEqual(resp.status_code, 503)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "generated")
        self.assertFalse(ClinicalNote.objects.exists())

    @override_settings(AI_SCRIBE_ALLOW_MOCK_PROVIDERS=False)
    def test_no_provider_reports_unavailable_instead_of_mock_text(self):
        session_id = self._session()
        base = f"/api/ai/consultation-sessions/{session_id}"
        self.client.post(f"{base}/start_recording/", {"patient_consent": True}, format="json")
        audio = SimpleUploadedFile("c.webm", b"synthetic", content_type="audio/webm")
        self.client.post(f"{base}/stop_recording/", {"audio_file": audio}, format="multipart")
        with mock.patch.dict("os.environ", {}, clear=False):
            resp = self.client.post(f"{base}/transcribe/", {}, format="json")
        self.assertEqual(resp.status_code, 503)
        self.assertIn("not configured", resp.json()["error"])

    def test_rejects_non_audio_upload(self):
        session_id = self._session()
        base = f"/api/ai/consultation-sessions/{session_id}"
        self.client.post(f"{base}/start_recording/", {"patient_consent": True}, format="json")
        bad = SimpleUploadedFile("x.html", b"<script>", content_type="text/html")
        resp = self.client.post(f"{base}/stop_recording/", {"audio_file": bad}, format="multipart")
        self.assertEqual(resp.status_code, 400)

    def test_extraction_is_coerced_to_schema(self):
        from ai_scribe.services.llm import LLMClinicalService

        data = {"chief_complaint": "fever", "symptoms": [{"x": 1}, "cough"], "injected": "drop me",
                "vitals": {"heart_rate": 80, "evil": "x"}}
        LLMClinicalService()._validate_extraction(data)
        self.assertEqual(data["chief_complaint"], ["fever"])
        self.assertEqual(data["symptoms"], ["cough"])
        self.assertNotIn("injected", data)
        self.assertEqual(data["vitals"], {"heart_rate": "80"})
        self.assertEqual(data["allergies"], [])
