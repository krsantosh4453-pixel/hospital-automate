"""
AI scribe: provider configuration, privacy and the doctor-only workflow
(Prompt 09). Synthetic data only; no request ever reaches a real provider.
"""

import shutil
import tempfile
from unittest import mock

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from ai_scribe.models import AIConsultationDraft
from ai_scribe.services.llm import (
    LLMClinicalService,
    LLMGenerationError,
    OpenAILLMProvider,
    redact_identifiers,
)
from clinical.models import ClinicalNote, Prescription
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff, put_in_care
from users.models import StaffRole

FAKE_KEY = "sk-test-not-a-real-key"
MEDIA = tempfile.mkdtemp(prefix="hms-ai-wf-")


def _no_ollama():
    return mock.patch("ai_scribe.services.llm.LocalLLMProvider.is_available", return_value=False)


def _chat_reply(status=200, content='{"chief_complaint": ["fever"]}', model="gpt-4o-mini"):
    reply = mock.Mock(status_code=status)
    reply.json.return_value = {
        "model": model,
        "choices": [{"message": {"content": content}}],
        "usage": {"total_tokens": 12, "prompt_tokens": 9, "completion_tokens": 3},
    }
    return reply


@override_settings(AI_SCRIBE_API_KEY=FAKE_KEY, AI_SCRIBE_LLM_BASE_URL="https://llm.example.test/v1/",
                   AI_SCRIBE_MODEL="gpt-4o-mini", AI_SCRIBE_LLM_TIMEOUT_SECONDS=7)
class OpenAICompatibleProviderTests(SimpleTestCase):
    def test_posts_chat_completion_to_configured_host_with_timeout(self):
        provider = OpenAILLMProvider()
        with mock.patch("requests.post", return_value=_chat_reply()) as post:
            result = provider.generate("system", "user", response_format={"type": "object"})

        self.assertEqual(post.call_args.args[0], "https://llm.example.test/v1/chat/completions")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 7)
        self.assertEqual(kwargs["json"]["model"], "gpt-4o-mini")
        self.assertEqual(kwargs["json"]["response_format"]["type"], "json_schema")
        self.assertEqual(result.structured_extraction, {"chief_complaint": ["fever"]})
        self.assertEqual(result.metadata["tokens_used"], 12)

    def test_timeout_becomes_generation_error(self):
        with mock.patch("requests.post", side_effect=requests.Timeout("slow")):
            with self.assertRaisesMessage(LLMGenerationError, "timed out after 7s"):
                OpenAILLMProvider().generate("s", "u")

    def test_http_error_does_not_leak_key_or_body(self):
        reply = _chat_reply(status=401)
        reply.text = f"bad key {FAKE_KEY}"
        with mock.patch("requests.post", return_value=reply):
            with self.assertRaises(LLMGenerationError) as ctx:
                OpenAILLMProvider().generate("s", "u")
        self.assertIn("HTTP 401", str(ctx.exception))
        self.assertNotIn(FAKE_KEY, str(ctx.exception))

    def test_non_json_reply_is_rejected(self):
        with mock.patch("requests.post", return_value=_chat_reply(content="not json")):
            with self.assertRaisesMessage(LLMGenerationError, "expected JSON"):
                OpenAILLMProvider().generate("s", "u")


class ProviderSelectionTests(SimpleTestCase):
    @override_settings(AI_SCRIBE_API_KEY="", AI_SCRIBE_ALLOW_MOCK_PROVIDERS=False)
    def test_without_key_no_provider_is_registered(self):
        with _no_ollama():
            with self.assertRaises(LLMGenerationError):
                LLMClinicalService().get_provider()

    @override_settings(AI_SCRIBE_API_KEY=FAKE_KEY, AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True,
                       AI_SCRIBE_PROVIDER="openai", AI_SCRIBE_MODEL="gpt-4o-mini")
    def test_settings_key_registers_smallest_model_by_default(self):
        with _no_ollama():
            provider = LLMClinicalService().get_provider()
        self.assertEqual(provider.provider_name, "openai")
        self.assertEqual(provider.default_model, "gpt-4o-mini")

    @override_settings(AI_SCRIBE_API_KEY=FAKE_KEY, AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True,
                       AI_SCRIBE_PROVIDER="development")
    def test_explicit_provider_choice_wins(self):
        with _no_ollama():
            self.assertEqual(LLMClinicalService().get_provider().provider_name, "development")


class PrivacyTests(SimpleTestCase):
    def test_redacts_full_name_name_parts_and_phone(self):
        text = "Ravi Kumar Sharma says ravi has fever; call 9000000021. Kumar? Ok, Ra."
        out = redact_identifiers(text, ["9000000021", "Ra"], names=["Ravi Kumar Sharma"])
        self.assertNotIn("Ravi", out)
        self.assertNotIn("ravi", out)
        self.assertNotIn("Kumar", out)
        self.assertNotIn("9000000021", out)
        self.assertIn("fever", out)
        self.assertIn("Ra.", out)  # too short to redact safely

    def test_generic_identifiers_are_masked_but_clinical_numbers_kept(self):
        text = ("Wife Sunita, phone +91 98765 43210, mail a.b@example.test, Aadhaar 1234 5678 9012, "
                "ABHA 91-1234-5678-9012, PAN ABCDE1234F. BP 120/80, platelets 150000, 500 mg twice daily, "
                "SpO2 97, lives at 12 MG Road, Pune; road traffic accident last year.")
        out = redact_identifiers(text, ["12 MG Road, Pune"], names=["Sunita Devi"])
        for gone in ("Sunita", "98765", "a.b@example.test", "1234 5678 9012", "91-1234-5678-9012",
                     "ABCDE1234F", "12 MG Road"):
            self.assertNotIn(gone, out)
        for kept in ("120/80", "150000", "500 mg", "SpO2 97", "road traffic accident"):
            self.assertIn(kept, out)

    @override_settings(AI_SCRIBE_API_KEY="", AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True)
    def test_prompt_sent_to_provider_has_no_patient_name(self):
        with _no_ollama():
            service = LLMClinicalService()
        provider = service.get_provider("development")
        with mock.patch.object(provider, "generate", wraps=provider.generate) as generate:
            service.generate_clinical_draft(
                "Doctor: Hello Meera Iyer, how is the cough?",
                patient_context={"name": "Meera Iyer", "age": 40, "gender": "Female"},
                provider="development",
                redact_terms=[],
                redact_names=["Meera Iyer"],
            )
        prompts = generate.call_args.kwargs["system_prompt"] + generate.call_args.kwargs["user_prompt"]
        self.assertNotIn("Meera", prompts)
        self.assertNotIn("Iyer", prompts)
        self.assertIn("Age: 40", prompts)

    def test_section_edit_is_coerced_and_unknown_section_refused(self):
        self.assertEqual(LLMClinicalService.coerce_section("plan", "rest"), ["rest"])
        self.assertEqual(LLMClinicalService.coerce_section("vitals", {"spo2": 97, "x": 1}), {"spo2": "97"})
        with self.assertRaises(ValueError):
            LLMClinicalService.coerce_section("prescription", ["drug"])


@override_settings(MEDIA_ROOT=MEDIA, AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True, AI_SCRIBE_API_KEY="")
class ScribeWorkflowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        patcher = _no_ollama()
        patcher.start()
        self.addCleanup(patcher.stop)
        self.hospital = Hospital.objects.create(name="Synthetic Scribe Hospital", is_active=True)
        self.user, _ = make_staff("wf_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(
            hospital=self.hospital, user=self.user, name="Dr Wf", specialization="General", phone="9000000030"
        )
        self.patient = Patient.objects.create(
            name="Synthetic Wf Patient", age=52, gender="Female", phone="9000000031", hospital=self.hospital,
            emergency_contact_name="Synthetic Relative", emergency_contact_phone="9000000032",
        )
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="WF-1")
        self.visit = Visit.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor)
        # A second doctor who also cares for the patient (through an own visit).
        self.other_user, _ = make_staff("wf_other", self.hospital, role=StaffRole.DOCTOR)
        self.other_doctor = put_in_care(self.other_user, self.hospital, self.patient)
        self.client = self._client(self.user)

    def _client(self, user):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user)
        client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))
        return client

    def _draft(self):
        resp = self.client.post("/api/ai/consultation-sessions/", {
            "visit": self.visit.id, "hospital": self.hospital.id, "patient": self.patient.id,
            "doctor": self.doctor.id, "language": "en",
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        base = f"/api/ai/consultation-sessions/{resp.json()['id']}"
        self.client.post(f"{base}/start_recording/", {"patient_consent": True}, format="json")
        audio = SimpleUploadedFile("c.m4a", b"synthetic-audio", content_type="audio/mp4")
        self.client.post(f"{base}/stop_recording/", {"audio_file": audio}, format="multipart")
        resp = self.client.post(f"{base}/transcribe/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        return AIConsultationDraft.objects.get(consultation__visit=self.visit)

    def test_session_must_belong_to_visit_doctor(self):
        resp = self.client.post("/api/ai/consultation-sessions/", {
            "visit": self.visit.id, "hospital": self.hospital.id, "patient": self.patient.id,
            "doctor": self.other_doctor.id, "language": "en",
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("doctor", resp.json()["details"])

    def test_another_doctor_cannot_record_generate_or_approve(self):
        draft = self._draft()
        other = self._client(self.other_user)
        session_url = f"/api/ai/consultation-sessions/{draft.consultation_id}"
        self.assertEqual(other.post(f"{session_url}/start_recording/", {"patient_consent": True},
                                    format="json").status_code, 403)
        self.assertEqual(other.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json").status_code, 403)
        self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
        self.assertEqual(other.post(f"/api/ai/drafts/{draft.id}/approve/", {}, format="json").status_code, 403)
        self.assertFalse(ClinicalNote.objects.exists())

    def test_generation_runs_once_per_draft(self):
        draft = self._draft()
        real = LLMClinicalService.generate_clinical_draft
        calls = []

        def spy(service, *args, **kwargs):
            calls.append(kwargs)
            return real(service, *args, **kwargs)

        with mock.patch.object(LLMClinicalService, "generate_clinical_draft", spy):
            first = self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
            second = self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("name", calls[0]["patient_context"])
        self.assertIn(self.patient.name, calls[0]["redact_names"])
        self.assertIn("Synthetic Relative", calls[0]["redact_names"])
        self.assertIn("WF-1", calls[0]["redact_terms"])
        self.assertIn(self.patient.phone, calls[0]["redact_terms"])

    def test_edit_validates_section_and_refuses_backdoor_approval(self):
        draft = self._draft()
        self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
        url = f"/api/ai/drafts/{draft.id}/review/"

        bad = self.client.post(url, {"action": "edited_section", "section": "prescription",
                                     "doctor_value": ["x"]}, format="json")
        self.assertEqual(bad.status_code, 400)
        sneaky = self.client.post(url, {"action": "approved", "section": "full_draft"}, format="json")
        self.assertEqual(sneaky.status_code, 400)

        ok = self.client.post(url, {"action": "edited_section", "section": "plan",
                                    "doctor_value": ["Review in 3 days"]}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "edited")
        self.assertEqual(draft.structured_extraction["plan"], ["Review in 3 days"])

    def test_approval_marks_missing_sections_and_never_prescribes(self):
        draft = self._draft()
        self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
        self.client.post(f"/api/ai/drafts/{draft.id}/review/", {
            "action": "edited_section", "section": "investigations", "doctor_value": [],
        }, format="json")
        resp = self.client.post(f"/api/ai/drafts/{draft.id}/approve/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        note = ClinicalNote.objects.get()
        self.assertIn("Investigations:\n  Not recorded in this consultation.", note.note)
        self.assertFalse(Prescription.objects.exists())
        self.assertEqual(
            self.client.post(f"/api/ai/drafts/{draft.id}/regenerate/", {}, format="json").status_code, 400
        )

    def test_async_steps_return_202_and_finish_in_the_background(self):
        resp = self.client.post("/api/ai/consultation-sessions/", {
            "visit": self.visit.id, "hospital": self.hospital.id, "patient": self.patient.id,
            "doctor": self.doctor.id, "language": "en",
        }, format="json")
        base = f"/api/ai/consultation-sessions/{resp.json()['id']}"
        self.client.post(f"{base}/start_recording/", {"patient_consent": True}, format="json")
        audio = SimpleUploadedFile("c.m4a", b"synthetic-audio", content_type="audio/mp4")
        self.client.post(f"{base}/stop_recording/", {"audio_file": audio}, format="multipart")

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(f"{base}/transcribe/", {"async": True}, format="json")
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertEqual(resp.json()["status"], "processing")
        # A second request while it runs (or after) never re-sends the audio.
        again = self.client.post(f"{base}/transcribe/", {"async": True}, format="json")
        self.assertEqual(again.status_code, 200)
        draft = AIConsultationDraft.objects.get(consultation__visit=self.visit)
        self.assertEqual(draft.transcript.status, "completed")

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {"async": True}, format="json")
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertIsNone(resp.json()["generation_completed_at"])
        draft.refresh_from_db()
        self.assertEqual(draft.status, "under_review")
        self.assertIsNotNone(draft.generation_completed_at)

    def test_unfinished_draft_cannot_be_approved_and_stuck_claim_recovers(self):
        from datetime import timedelta

        from django.utils import timezone

        draft = self._draft()
        stuck_at = timezone.now() - timedelta(hours=1)
        AIConsultationDraft.objects.filter(pk=draft.pk).update(
            status="under_review", generation_started_at=stuck_at, generation_completed_at=None, provider="")
        resp = self.client.post(f"/api/ai/drafts/{draft.id}/approve/", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ClinicalNote.objects.exists())
        # The worker died: after the provider timeout the draft can be generated again.
        resp = self.client.post(f"/api/ai/drafts/{draft.id}/generate/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.client.post(f"/api/ai/drafts/{draft.id}/approve/", {}, format="json").status_code, 200)

    def test_capabilities_report_providers_without_keys_and_block_cnn(self):
        with override_settings(AI_SCRIBE_API_KEY=FAKE_KEY, AI_SCRIBE_PROVIDER="openai"):
            resp = self.client.get("/api/ai/capabilities/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["scribe"]["drafting"]["provider"], "openai")
        self.assertEqual(body["scribe"]["drafting"]["model"], "gpt-4o-mini")
        self.assertEqual(body["image_prediction"]["status"], "blocked")
        self.assertFalse(body["image_prediction"]["available"])
        self.assertNotIn(FAKE_KEY, resp.content.decode())
        self.assertEqual(APIClient().get("/api/ai/capabilities/").status_code, 401)
