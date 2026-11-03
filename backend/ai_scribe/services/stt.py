"""
Speech-to-Text Service Abstraction

Provides a unified interface for multiple STT providers.
Real providers: Whisper (local model or OpenAI-compatible API) and Google
Cloud Speech. The development provider returns canned text and is only
registered where settings allow mocks. Languages: see ``languages.py``.
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path

import requests
from django.conf import settings

from . import languages

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription"""
    text: str
    structured_data: Dict[str, Any]
    provider: str
    model: str
    metadata: Dict[str, Any]
    detected_language: str = ""
    language_confidence: Optional[float] = None


class SpeechToTextProvider(ABC):
    """Abstract base class for STT providers"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider"""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """List of supported audio MIME types"""
        pass

    @property
    @abstractmethod
    def max_file_size_mb(self) -> int:
        """Maximum file size in MB"""
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_file: str,
        language: str = "en",
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text.

        Args:
            audio_file: Path to audio file
            language: Language code (e.g., 'en', 'hi', 'auto')
            **kwargs: Provider-specific options

        Returns:
            TranscriptionResult with text and metadata

        Raises:
            TranscriptionError: If transcription fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available"""
        pass


class TranscriptionError(Exception):
    """Exception raised when transcription fails"""
    pass


class DevelopmentSTTProvider(SpeechToTextProvider):
    """
    Development STT provider that returns mock transcriptions.
    Used for development and testing when no real STT provider is configured.

    DO NOT USE IN PRODUCTION - This does not perform actual speech recognition.
    """

    @property
    def provider_name(self) -> str:
        return "development"

    @property
    def supported_formats(self) -> list[str]:
        return [
            "audio/wav", "audio/x-wav",
            "audio/mpeg", "audio/mp3",
            "audio/mp4", "audio/m4a",
            "audio/ogg", "audio/webm",
        ]

    @property
    def max_file_size_mb(self) -> int:
        return 100

    def is_available(self) -> bool:
        return True

    def transcribe(
        self,
        audio_file: str,
        language: str = "en",
        **kwargs
    ) -> TranscriptionResult:
        """
        Return a mock transcription for development.

        In production, this would be replaced with actual STT processing.
        """
        logger.warning(
            "Using DEVELOPMENT STT provider - not performing actual transcription. "
            "Configure a real provider (Whisper, Google, Azure, AWS) for production."
        )

        # Return mock transcript based on language
        mock_transcripts = {
            "en": (
                "Doctor: Good morning, what brings you in today? "
                "Patient: I have been having a headache for three days. "
                "Doctor: Is it on one side or both sides? "
                "Patient: It is on the right side, throbbing pain. "
                "Doctor: Any nausea or sensitivity to light? "
                "Patient: Yes, slight nausea and light bothers me. "
                "Doctor: Any history of migraines? "
                "Patient: No, this is the first time. "
                "Doctor: I will examine you and we may need some tests."
            ),
            "hi": (
                "डॉक्टर: नमस्ते, आज क्या तकलीफ है? "
                "मरीज: मुझे तीन दिन से सिरदर्द हो रहा है। "
                "डॉक्टर: दर्द एक तरफ है या दोनों तरफ? "
                "मरीज: दाईं तरफ है, धुकधुकी जैसा दर्द। "
                "डॉक्टर: मतली या रोशनी से परेशानी? "
                "मरीज: हाँ, थोड़ी मतली और रोशनी चुभती है। "
                "डॉक्टर: माइग्रेन का इतिहास है? "
                "मरीज: नहीं, पहली बार है। "
                "डॉक्टर: मैं जांच करूंगा और शायद कुछ टेस्ट करवाने पड़ें।"
            ),
            "hinglish": (
                "Doctor: Namaste, aaj kya problem hai? "
                "Patient: Teen din se headache ho raha hai. "
                "Doctor: Ek side hai ya dono side? "
                "Patient: Right side, throbbing pain hai. "
                "Doctor: Nausea ya light se problem? "
                "Patient: Haan, thoda nausea hai aur light chubhti hai. "
                "Doctor: Pehle kabhi migraine hua hai? "
                "Patient: Nahi, pehli baar hai. "
                "Doctor: Main examine karta hoon, shayad kuch tests karwane padenge."
            ),
        }

        transcript_text = mock_transcripts.get(language, mock_transcripts["en"])

        # Simple structured mock data
        structured_data = {
            "segments": [
                {"speaker": "doctor", "text": "Good morning, what brings you in today?", "start": 0.0, "end": 2.5},
                {"speaker": "patient", "text": "I have been having a headache for three days.", "start": 2.5, "end": 5.0},
                {"speaker": "doctor", "text": "Is it on one side or both sides?", "start": 5.0, "end": 7.0},
                {"speaker": "patient", "text": "It is on the right side, throbbing pain.", "start": 7.0, "end": 9.5},
                {"speaker": "doctor", "text": "Any nausea or sensitivity to light?", "start": 9.5, "end": 12.0},
                {"speaker": "patient", "text": "Yes, slight nausea and light bothers me.", "start": 12.0, "end": 14.5},
                {"speaker": "doctor", "text": "Any history of migraines?", "start": 14.5, "end": 16.0},
                {"speaker": "patient", "text": "No, this is the first time.", "start": 16.0, "end": 18.0},
                {"speaker": "doctor", "text": "I will examine you and we may need some tests.", "start": 18.0, "end": 21.0},
            ],
            "language": language,
        }

        return TranscriptionResult(
            text=transcript_text,
            structured_data=structured_data,
            provider=self.provider_name,
            model="mock-v1",
            metadata={
                "duration_seconds": 21.0,
                "note": "MOCK TRANSCRIPTION - NOT REAL STT",
            },
            detected_language=language,
            language_confidence=0.95,
        )


class WhisperSTTProvider(SpeechToTextProvider):
    """
    Whisper STT provider (local model or an OpenAI-compatible HTTP API).

    The API path talks to ``{AI_SCRIBE_STT_BASE_URL}/audio/transcriptions`` with
    ``requests``, so OpenAI or any compatible host (for example Groq's
    whisper-large-v3) works by changing settings only.
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "whisper-1"
    REQUEST_TIMEOUT_SECONDS = 120

    def __init__(self, use_api: bool = False, api_key: Optional[str] = None, model: Optional[str] = None):
        self.use_api = use_api
        # Read from settings only, so test settings can switch real providers off.
        self.api_key = api_key or getattr(settings, "AI_SCRIBE_STT_API_KEY", None)
        self.model = model or getattr(settings, "AI_SCRIBE_STT_MODEL", None) or self.DEFAULT_MODEL
        self.base_url = (getattr(settings, "AI_SCRIBE_STT_BASE_URL", None) or self.DEFAULT_BASE_URL).rstrip("/")
        self._local_model = None

    @property
    def provider_name(self) -> str:
        return "whisper"

    @property
    def supported_formats(self) -> list[str]:
        return [
            "audio/wav", "audio/x-wav",
            "audio/mpeg", "audio/mp3",
            "audio/mp4", "audio/m4a",
            "audio/ogg", "audio/webm",
            "audio/flac",
        ]

    @property
    def max_file_size_mb(self) -> int:
        return 25 if self.use_api else 1000  # API has 25MB limit

    def is_available(self) -> bool:
        if self.use_api:
            return bool(self.api_key)
        try:
            import whisper
            return True
        except ImportError:
            return False

    def transcribe(
        self,
        audio_file: str,
        language: str = "en",
        **kwargs
    ) -> TranscriptionResult:
        if self.use_api:
            return self._transcribe_api(audio_file, language, **kwargs)
        else:
            return self._transcribe_local(audio_file, language, **kwargs)

    @staticmethod
    def whisper_request_options(language: str) -> Dict[str, str]:
        """
        Translate our language code into Whisper's ``language`` and ``prompt``.

        Hinglish is left to Whisper's own detection (forcing "hi" makes it write
        everything in Devanagari) and steered towards Roman script by the prompt.
        """
        options = {}
        if language in (languages.ENGLISH, languages.HINDI):
            options["language"] = language
        prompt = languages.WHISPER_STYLE_PROMPTS.get(language)
        if prompt:
            options["prompt"] = prompt
        return options

    def _transcribe_api(self, audio_file: str, language: str, **kwargs) -> TranscriptionResult:
        """Call an OpenAI-compatible /audio/transcriptions endpoint."""
        if not self.api_key:
            raise TranscriptionError("Whisper API key is not configured (AI_SCRIBE_STT_API_KEY).")

        form = {
            "model": self.model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "segment",
            **self.whisper_request_options(language),
        }
        try:
            with open(audio_file, "rb") as audio:
                response = requests.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data=form,
                    files={"file": (Path(audio_file).name, audio)},
                    timeout=self.REQUEST_TIMEOUT_SECONDS,
                )
        except requests.RequestException as exc:
            logger.error("Whisper API request failed: %s", type(exc).__name__)
            raise TranscriptionError("Could not reach the speech-to-text service.") from exc

        if response.status_code != 200:
            # The body can echo request details; log only the status.
            logger.error("Whisper API returned HTTP %s", response.status_code)
            raise TranscriptionError(f"Speech-to-text service returned HTTP {response.status_code}.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise TranscriptionError("Speech-to-text service returned an unreadable response.") from exc

        detected = languages.detected_language_code(payload.get("language"))
        return TranscriptionResult(
            text=(payload.get("text") or "").strip(),
            structured_data={
                "segments": [
                    {"start": seg.get("start"), "end": seg.get("end"), "text": seg.get("text", "")}
                    for seg in payload.get("segments") or []
                ],
                "language": detected,
                "requested_language": language,
            },
            provider=self.provider_name,
            model=self.model,
            metadata={
                "duration": payload.get("duration"),
                "api": True,
            },
            detected_language=detected,
            language_confidence=None,  # Whisper does not return a confidence score
        )

    def _transcribe_local(self, audio_file: str, language: str, **kwargs) -> TranscriptionResult:
        """Use local Whisper model"""
        try:
            import whisper
        except ImportError:
            raise TranscriptionError("whisper package not installed. Run: pip install openai-whisper")

        model_size = kwargs.pop("model_size", "base")
        if self._local_model is None:
            # Load model on first use
            logger.info(f"Loading Whisper model: {model_size}")
            self._local_model = whisper.load_model(model_size)

        options = self.whisper_request_options(language)
        result = self._local_model.transcribe(
            audio_file,
            language=options.get("language"),
            initial_prompt=options.get("prompt"),
            word_timestamps=True,
            **kwargs
        )

        detected = languages.detected_language_code(result.get("language", language))
        return TranscriptionResult(
            text=result["text"],
            structured_data={
                "segments": result.get("segments", []),
                "language": detected,
                "requested_language": language,
            },
            provider=self.provider_name,
            model=f"whisper-{model_size}",
            metadata={
                "duration": result.get("duration", 0),
                "api": False,
            },
            detected_language=detected,
            language_confidence=None,
        )


class GoogleSTTProvider(SpeechToTextProvider):
    """Google Cloud Speech-to-Text provider"""

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self._client = None

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def supported_formats(self) -> list[str]:
        return [
            "audio/wav", "audio/x-wav",
            "audio/mpeg", "audio/mp3",
            "audio/flac",
            "audio/ogg", "audio/webm",
            "audio/amr",
        ]

    @property
    def max_file_size_mb(self) -> int:
        return 100  # Google has generous limits

    def is_available(self) -> bool:
        if not self.credentials_path:
            return False
        try:
            from google.cloud import speech
            return True
        except ImportError:
            return False

    def transcribe(
        self,
        audio_file: str,
        language: str = "en",
        **kwargs
    ) -> TranscriptionResult:
        try:
            from google.cloud import speech
        except ImportError:
            raise TranscriptionError("google-cloud-speech package not installed")

        if self._client is None:
            self._client = speech.SpeechClient()

        with open(audio_file, "rb") as f:
            content = f.read()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=kwargs.get("sample_rate", 16000),
            language_code=language if language != "auto" else "en-US",
            alternative_language_codes=kwargs.get("alternative_languages", ["hi-IN", "en-IN"]),
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            enable_speaker_diarization=kwargs.get("speaker_diarization", True),
            diarization_speaker_count=kwargs.get("speaker_count", 2),
        )

        response = self._client.recognize(config=config, audio=audio)

        # Process results
        full_text = ""
        segments = []
        for result in response.results:
            alternative = result.alternatives[0]
            full_text += alternative.transcript + " "
            if hasattr(alternative, "words"):
                for word in alternative.words:
                    segments.append({
                        "speaker": getattr(word, "speaker_tag", 0),
                        "word": word.word,
                        "start": word.start_time.total_seconds(),
                        "end": word.end_time.total_seconds(),
                    })

        return TranscriptionResult(
            text=full_text.strip(),
            structured_data={"segments": segments},
            provider=self.provider_name,
            model="google-cloud-speech",
            metadata={},
            detected_language=language,
            language_confidence=None,
        )


class SpeechToTextService:
    """
    Main service class for speech-to-text operations.
    Manages provider selection and fallback.
    """

    def __init__(self):
        self._providers: Dict[str, SpeechToTextProvider] = {}
        self._default_provider: Optional[str] = None
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers based on configuration"""
        # The development provider returns canned clinical text. It is only
        # registered where settings explicitly allow it (local dev, tests).
        if getattr(settings, "AI_SCRIBE_ALLOW_MOCK_PROVIDERS", False):
            self._providers["development"] = DevelopmentSTTProvider()

        # Try to register Whisper (local)
        whisper_local = WhisperSTTProvider(use_api=False)
        if whisper_local.is_available():
            self._providers["whisper_local"] = whisper_local
            if not self._default_provider:
                self._default_provider = "whisper_local"

        # Try to register Whisper (API); available once a key is configured
        whisper_api = WhisperSTTProvider(use_api=True)
        if whisper_api.is_available():
            self._providers["whisper_api"] = whisper_api
            if not self._default_provider:
                self._default_provider = "whisper_api"

        # Try to register Google
        google = GoogleSTTProvider()
        if google.is_available():
            self._providers["google"] = google
            if not self._default_provider:
                self._default_provider = "google"

        # An explicitly chosen provider wins when it is actually registered.
        preferred = getattr(settings, "AI_SCRIBE_STT_PROVIDER", "")
        if preferred and preferred in self._providers:
            self._default_provider = preferred
        elif preferred:
            logger.warning("AI_SCRIBE_STT_PROVIDER=%s is not configured; ignoring it.", preferred)

        # Fall back to the development provider only where it is allowed;
        # otherwise there is no provider and callers report "unavailable".
        if not self._default_provider and "development" in self._providers:
            self._default_provider = "development"
            logger.warning("No real STT provider configured; using the DEVELOPMENT mock provider.")

    def get_provider(self, provider_name: Optional[str] = None) -> SpeechToTextProvider:
        """Get STT provider by name or default"""
        name = provider_name or self._default_provider
        if name not in self._providers:
            raise TranscriptionError(f"STT provider '{name}' not available. Available: {list(self._providers.keys())}")
        return self._providers[name]

    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """List all available providers with their capabilities"""
        return {
            name: {
                "name": provider.provider_name,
                "supported_formats": provider.supported_formats,
                "max_file_size_mb": provider.max_file_size_mb,
                "is_available": provider.is_available(),
            }
            for name, provider in self._providers.items()
        }

    def transcribe(
        self,
        audio_file: str,
        language: str = "en",
        provider: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe audio file using specified or default provider.

        Args:
            audio_file: Path to audio file
            language: Language code (en, hi, hinglish, auto; aliases like hi-IN accepted)
            provider: Specific provider to use (optional)
            **kwargs: Provider-specific options

        Returns:
            TranscriptionResult
        """
        try:
            language = languages.normalize_language(language)
        except ValueError as exc:
            raise TranscriptionError(str(exc)) from exc
        stt_provider = self.get_provider(provider)

        # Validate file
        path = Path(audio_file)
        if not path.exists():
            raise TranscriptionError(f"Audio file not found: {audio_file}")

        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > stt_provider.max_file_size_mb:
            raise TranscriptionError(
                f"File too large: {file_size_mb:.1f}MB > {stt_provider.max_file_size_mb}MB limit"
            )

        logger.info(f"Transcribing {audio_file} with {stt_provider.provider_name} (language={language})")
        return stt_provider.transcribe(audio_file, language, **kwargs)
