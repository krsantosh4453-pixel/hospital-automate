"""Hindi / English / Hinglish speech-to-text: language handling and the Whisper API client.

No real provider is called: HTTP is mocked. A live check with a real key is
a separate manual step (see AI_SCRIBE_STT_* in .env.example).
"""

import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from ai_scribe.models import ConsultationSession
from ai_scribe.services import languages
from ai_scribe.services.stt import SpeechToTextService, TranscriptionError, WhisperSTTProvider
from ai_scribe.views import _draft_language
from doctors.models import Doctor
from encounters.models import Visit
from hospital.models import Hospital
from patients.models import Patient, PatientHospital
from security_tests.test_tenant_isolation import make_staff
from users.models import StaffRole

MEDIA = tempfile.mkdtemp(prefix="hms-stt-test-")
FAKE_KEY = "test-key-not-real"


def _audio_file():
    handle = tempfile.NamedTemporaryFile(suffix=".webm", dir=MEDIA, delete=False)
    handle.write(b"\x1aE\xdf\xa3synthetic")
    handle.close()
    return handle.name


def _whisper_response(status_code=200, payload=None):
    response = mock.Mock(status_code=status_code)
    response.json.return_value = payload or {}
    return response


class LanguageCodeTests(SimpleTestCase):
    def test_accepts_canonical_codes_and_aliases(self):
        self.assertEqual(languages.normalize_language("hi"), "hi")
        self.assertEqual(languages.normalize_language("hi-IN"), "hi")
        self.assertEqual(languages.normalize_language(" English "), "en")
        self.assertEqual(languages.normalize_language("hi-en"), "hinglish")
        self.assertEqual(languages.normalize_language("AUTO"), "auto")

    def test_rejects_unsupported_language(self):
        with self.assertRaisesMessage(ValueError, "Unsupported language 'fr'"):
            languages.normalize_language("fr")
        with self.assertRaises(ValueError):
            languages.normalize_language("")

    def test_maps_whisper_detected_names_to_codes(self):
        self.assertEqual(languages.detected_language_code("hindi"), "hi")
        self.assertEqual(languages.detected_language_code("English"), "en")
        self.assertEqual(languages.detected_language_code(None), "")


class WhisperOptionTests(SimpleTestCase):
    def test_hindi_and_english_are_forced_with_a_style_prompt(self):
        hindi = WhisperSTTProvider.whisper_request_options("hi")
        self.assertEqual(hindi["language"], "hi")
        self.assertIn("डॉक्टर", hindi["prompt"])
        self.assertEqual(WhisperSTTProvider.whisper_request_options("en")["language"], "en")

    def test_hinglish_lets_whisper_detect_and_steers_to_roman_script(self):
        options = WhisperSTTProvider.whisper_request_options("hinglish")
        self.assertNotIn("language", options)
        self.assertIn("Fever kab se hai", options["prompt"])

    def test_auto_sends_neither_language_nor_prompt(self):
        self.assertEqual(WhisperSTTProvider.whisper_request_options("auto"), {})


@override_settings(
    AI_SCRIBE_STT_API_KEY=FAKE_KEY,
    AI_SCRIBE_STT_BASE_URL="https://stt.example.test/v1/",
    AI_SCRIBE_STT_MODEL="whisper-large-v3",
)
class WhisperApiClientTests(SimpleTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.audio = _audio_file()
        self.provider = WhisperSTTProvider(use_api=True)

    def test_sends_openai_compatible_request_and_parses_hindi_reply(self):
        reply = _whisper_response(payload={
            "text": " मुझे तीन दिन से बुखार है। ",
            "language": "hindi",
            "duration": 4.2,
            "segments": [{"start": 0.0, "end": 4.2, "text": "मुझे तीन दिन से बुखार है।", "tokens": [1]}],
        })
        with mock.patch("ai_scribe.services.stt.requests.post", return_value=reply) as post:
            result = self.provider.transcribe(self.audio, "hi")

        url = post.call_args.args[0]
        kwargs = post.call_args.kwargs
        self.assertEqual(url, "https://stt.example.test/v1/audio/transcriptions")
        self.assertEqual(kwargs["headers"], {"Authorization": f"Bearer {FAKE_KEY}"})
        self.assertEqual(kwargs["data"]["model"], "whisper-large-v3")
        self.assertEqual(kwargs["data"]["language"], "hi")
        self.assertEqual(kwargs["data"]["response_format"], "verbose_json")
        self.assertIn("file", kwargs["files"])
        self.assertGreater(kwargs["timeout"], 0)

        self.assertEqual(result.text, "मुझे तीन दिन से बुखार है।")
        self.assertEqual(result.detected_language, "hi")
        self.assertEqual(result.structured_data["requested_language"], "hi")
        self.assertEqual(result.structured_data["segments"], [
            {"start": 0.0, "end": 4.2, "text": "मुझे तीन दिन से बुखार है।"},
        ])
        self.assertEqual(result.provider, "whisper")

    def test_http_error_raises_without_leaking_key(self):
        with mock.patch("ai_scribe.services.stt.requests.post", return_value=_whisper_response(401)):
            with self.assertRaises(TranscriptionError) as ctx:
                self.provider.transcribe(self.audio, "en")
        self.assertIn("HTTP 401", str(ctx.exception))
        self.assertNotIn(FAKE_KEY, str(ctx.exception))

    def test_network_failure_raises_transcription_error(self):
        with mock.patch("ai_scribe.services.stt.requests.post", side_effect=requests.ConnectionError("down")):
            with self.assertRaisesMessage(TranscriptionError, "Could not reach"):
                self.provider.transcribe(self.audio, "en")

    def test_unreadable_reply_raises_transcription_error(self):
        reply = _whisper_response()
        reply.json.side_effect = ValueError("not json")
        with mock.patch("ai_scribe.services.stt.requests.post", return_value=reply):
            with self.assertRaisesMessage(TranscriptionError, "unreadable"):
                self.provider.transcribe(self.audio, "en")


class ProviderSelectionTests(SimpleTestCase):
    @override_settings(AI_SCRIBE_STT_API_KEY="", AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True)
    def test_without_a_key_only_the_mock_is_registered(self):
        service = SpeechToTextService()
        self.assertNotIn("whisper_api", service.list_providers())
        self.assertEqual(service.get_provider().provider_name, "development")

    @override_settings(AI_SCRIBE_STT_API_KEY=FAKE_KEY, AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True,
                       AI_SCRIBE_STT_PROVIDER="")
    def test_a_key_registers_whisper_api_as_default(self):
        service = SpeechToTextService()
        self.assertIn("whisper_api", service.list_providers())
        self.assertEqual(service.get_provider().provider_name, "whisper")

    @override_settings(AI_SCRIBE_STT_API_KEY=FAKE_KEY, AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True,
                       AI_SCRIBE_STT_PROVIDER="development")
    def test_explicit_provider_choice_wins(self):
        self.assertEqual(SpeechToTextService().get_provider().provider_name, "development")

    @override_settings(AI_SCRIBE_STT_API_KEY="", AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True)
    def test_service_rejects_unsupported_language(self):
        with self.assertRaisesMessage(TranscriptionError, "Unsupported language"):
            SpeechToTextService().transcribe(_audio_file(), language="fr")


class DraftLanguageTests(SimpleTestCase):
    def _draft(self, chosen, detected):
        return SimpleNamespace(
            consultation=SimpleNamespace(language=chosen),
            transcript=SimpleNamespace(detected_language=detected),
        )

    def test_doctor_choice_wins_over_detection(self):
        # Hinglish audio is usually detected as Hindi; the note stays English.
        self.assertEqual(_draft_language(self._draft("hinglish", "hi")), "hinglish")

    def test_auto_uses_detected_language_when_supported(self):
        self.assertEqual(_draft_language(self._draft("auto", "hi")), "hi")
        self.assertEqual(_draft_language(self._draft("auto", "tamil")), "auto")


@override_settings(MEDIA_ROOT=MEDIA, AI_SCRIBE_STT_API_KEY="", AI_SCRIBE_ALLOW_MOCK_PROVIDERS=True)
class ConsultationLanguageApiTests(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(name="Synthetic STT Hospital", is_active=True)
        self.user, _ = make_staff("stt_doctor", self.hospital, role=StaffRole.DOCTOR)
        self.doctor = Doctor.objects.create(
            hospital=self.hospital, user=self.user, name="Dr Synthetic", specialization="General", phone="9000000030"
        )
        self.patient = Patient.objects.create(
            name="Synthetic STT Patient", age=40, gender="Female", phone="9000000031", hospital=self.hospital
        )
        PatientHospital.objects.create(patient=self.patient, hospital=self.hospital, uhid="STT-1")
        self.visit = Visit.objects.create(patient=self.patient, hospital=self.hospital, doctor=self.doctor)
        self.client = APIClient(raise_request_exception=False)
        self.client.force_authenticate(self.user)
        self.client.credentials(HTTP_X_HOSPITAL_ID=str(self.hospital.id))

    def _create(self, language):
        return self.client.post("/api/ai/consultation-sessions/", {
            "visit": self.visit.id, "hospital": self.hospital.id, "patient": self.patient.id,
            "doctor": self.doctor.id, "language": language,
        }, format="json")

    def _recorded_session(self):
        session_id = self._create("en").json()["id"]
        base = f"/api/ai/consultation-sessions/{session_id}"
        self.client.post(f"{base}/start_recording/", {"patient_consent": True}, format="json")
        audio = SimpleUploadedFile("c.webm", b"\x1aE\xdf\xa3synthetic", content_type="audio/webm")
        resp = self.client.post(f"{base}/stop_recording/", {"audio_file": audio, "duration_seconds": 5},
                                format="multipart")
        self.assertEqual(resp.status_code, 200, resp.content)
        return session_id, base

    def test_session_language_is_normalised(self):
        resp = self._create("hi-IN")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["language"], "hi")

    def test_session_rejects_unsupported_language(self):
        resp = self._create("fr")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("language", str(resp.json()))

    def test_transcribe_uses_language_chosen_by_doctor(self):
        session_id, base = self._recorded_session()
        resp = self.client.post(f"{base}/transcribe/", {"language": "hinglish"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("Teen din se headache", resp.json()["text"])
        self.assertEqual(ConsultationSession.objects.get(id=session_id).language, "hinglish")

    def test_changing_language_redoes_a_finished_transcript(self):
        _, base = self._recorded_session()
        self.assertEqual(self.client.post(f"{base}/transcribe/", {}, format="json").status_code, 200)
        resp = self.client.post(f"{base}/transcribe/", {"language": "hi"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn("सिरदर्द", resp.json()["text"])

    def test_transcribe_rejects_unsupported_language(self):
        _, base = self._recorded_session()
        resp = self.client.post(f"{base}/transcribe/", {"language": "fr"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported language", resp.json()["error"])
