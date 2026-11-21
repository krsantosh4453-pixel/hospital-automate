"""
LLM Clinical Service Abstraction

Provides a unified interface for multiple LLM providers for clinical extraction.
Supports structured output with schema validation.
"""

import os
import re
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

from django.conf import settings

from .stt import TranscriptionError

REDACTED = "[patient]"
REDACTED_ID = "[identifier]"
MIN_REDACT_CHARS = 3

# Identifiers masked wherever they appear, whoever they belong to (a relative
# or another patient mentioned in the conversation). Clinical values (doses,
# lab counts, vitals) never match: they are short or not in these shapes.
GENERIC_IDENTIFIER_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),                              # e-mail
    re.compile(r"(?<!\d)\d{2}-\d{4}-\d{4}-\d{4}(?!\d)"),                       # ABHA number
    re.compile(r"\b[\w.]+@(?:sbx|abdm)\b", re.IGNORECASE),                      # ABHA address
    re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"),                    # Aadhaar
    re.compile(r"(?<![\d+])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"),      # Indian mobile
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),                                       # PAN
]


def _pieces(value: str, split_words: bool) -> set:
    """A term and its parts worth masking: comma-separated segments, and
    for names also each word. Fragments under MIN_REDACT_CHARS are kept."""
    value = str(value or "").strip()
    if len(value) < MIN_REDACT_CHARS:
        return set()
    parts = {value} | {seg.strip() for seg in value.split(",")}
    if split_words:
        parts |= {word.strip(",.;:") for word in value.split()}
    return {p for p in parts if len(p) >= MIN_REDACT_CHARS}


def redact_identifiers(text: str, terms: List[str], names: Optional[List[str]] = None) -> str:
    """
    Mask the patient's own identifiers in ``text``: ``names`` whole and word
    by word, ``terms`` (phones, address, IDs) whole and by comma-separated
    segment, case-insensitively on word boundaries. Then mask any e-mail,
    phone, Aadhaar, ABHA or PAN, whoever it belongs to.
    """
    pieces = set()
    for name in names or []:
        pieces |= _pieces(name, split_words=True)
    for term in terms:
        pieces |= _pieces(term, split_words=False)
    for piece in sorted(pieces, key=len, reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(piece)}(?!\w)", REDACTED, text, flags=re.IGNORECASE)
    for pattern in GENERIC_IDENTIFIER_PATTERNS:
        text = pattern.sub(REDACTED_ID, text)
    return text

logger = logging.getLogger(__name__)


@dataclass
class ClinicalExtractionResult:
    """Result of clinical extraction from transcript"""
    structured_extraction: Dict[str, Any]
    summary: str
    provider: str
    model: str
    prompt_version: str
    metadata: Dict[str, Any]
    raw_response: str = ""


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider"""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """List of supported model names"""
        pass

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ClinicalExtractionResult:
        """
        Generate structured clinical extraction.

        Args:
            system_prompt: System prompt defining AI role
            user_prompt: User prompt with transcript
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: JSON schema for structured output
            **kwargs: Provider-specific options

        Returns:
            ClinicalExtractionResult

        Raises:
            LLMGenerationError: If generation fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available"""
        pass


class LLMGenerationError(Exception):
    """Exception raised when LLM generation fails"""
    pass


class DevelopmentLLMProvider(LLMProvider):
    """
    Development LLM provider that returns mock clinical extractions.
    Used for development and testing when no real LLM provider is configured.

    DO NOT USE IN PRODUCTION - This does not perform actual LLM inference.
    """

    @property
    def provider_name(self) -> str:
        return "development"

    @property
    def supported_models(self) -> List[str]:
        return ["mock-clinical-v1"]

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "mock-clinical-v1",
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ClinicalExtractionResult:
        """
        Return a mock clinical extraction for development.
        """
        logger.warning(
            "Using DEVELOPMENT LLM provider - not performing actual LLM inference. "
            "Configure a real provider (OpenAI, Anthropic, Google, Local) for production."
        )

        # Extract key information from the prompt for more realistic mock
        # In production, this would be actual LLM output
        mock_extraction = {
            "chief_complaint": ["Headache for 3 days"],
            "symptoms": [
                "Right-sided throbbing headache",
                "Nausea",
                "Photophobia (light sensitivity)",
            ],
            "history": [
                "No previous migraine history",
                "First episode of this type",
                "Duration: 3 days",
            ],
            "allergies": [],
            "medications": [],
            "examination": [
                "Patient appears uncomfortable",
                "No focal neurological deficits",
                "Pupils equal and reactive",
            ],
            "vitals": {
                "blood_pressure": "130/85",
                "heart_rate": "78",
                "temperature": "37.0",
                "spo2": "98",
            },
            "assessment": [
                "Probable migraine without aura",
                "Rule out secondary causes",
            ],
            "investigations": [
                "CBC",
                "Basic metabolic panel",
                "Consider MRI brain if not improving",
            ],
            "plan": [
                "Start acute migraine treatment",
                "Advise hydration and rest",
                "Avoid known triggers",
                "Follow up in 1 week",
            ],
            "follow_up": [
                "Return in 1 week for reassessment",
                "Earlier if symptoms worsen",
            ],
        }

        mock_summary = (
            "Patient presents with 3-day history of right-sided throbbing headache "
            "associated with nausea and photophobia. No prior migraine history. "
            "Clinical picture consistent with migraine without aura. "
            "Recommended investigations and symptomatic treatment initiated. "
            "Follow-up in 1 week."
        )

        return ClinicalExtractionResult(
            structured_extraction=mock_extraction,
            summary=mock_summary,
            provider=self.provider_name,
            model=model,
            prompt_version="v1",
            metadata={
                "tokens_used": 0,
                "latency_ms": 0,
                "note": "MOCK EXTRACTION - NOT REAL LLM",
            },
            raw_response=json.dumps(mock_extraction, indent=2),
        )


class OpenAILLMProvider(LLMProvider):
    """
    Chat-completions provider for OpenAI or any OpenAI-compatible host
    (``{AI_SCRIBE_LLM_BASE_URL}/chat/completions``), called with ``requests``
    so no vendor SDK is needed. Key, base URL, model and timeout come from
    settings only, so test settings can switch it off.
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_TIMEOUT_SECONDS = 60

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "AI_SCRIBE_API_KEY", "") or ""
        self.default_model = default_model or getattr(settings, "AI_SCRIBE_MODEL", "") or self.DEFAULT_MODEL
        self.base_url = (getattr(settings, "AI_SCRIBE_LLM_BASE_URL", "") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = getattr(settings, "AI_SCRIBE_LLM_TIMEOUT_SECONDS", None) or self.DEFAULT_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> List[str]:
        return [self.default_model]

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ClinicalExtractionResult:
        import requests

        if not self.is_available():
            raise LLMGenerationError("OpenAI-compatible provider not available: AI_SCRIBE_API_KEY is not set.")
        model = model or self.default_model
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": (
                {"type": "json_schema",
                 "json_schema": {"name": "clinical_extraction", "schema": response_format, "strict": False}}
                if response_format else {"type": "json_object"}
            ),
        }
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise LLMGenerationError(f"LLM request timed out after {self.timeout}s.") from exc
        except requests.RequestException as exc:
            raise LLMGenerationError(f"LLM request failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            # The body may echo the prompt; keep only the status code.
            raise LLMGenerationError(f"LLM provider answered HTTP {response.status_code}.")

        latency_ms = int((time.time() - start_time) * 1000)
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            structured_data = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMGenerationError("LLM reply was not the expected JSON.") from exc
        if not isinstance(structured_data, dict):
            raise LLMGenerationError("LLM reply was not a JSON object.")
        usage = body.get("usage") or {}

        return ClinicalExtractionResult(
            structured_extraction=structured_data,
            summary=structured_data.get("summary", "") or self._build_summary(structured_data),
            provider=self.provider_name,
            model=body.get("model") or model,
            prompt_version=kwargs.get("prompt_version", "v1"),
            metadata={
                "tokens_used": usage.get("total_tokens", 0),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "latency_ms": latency_ms,
            },
            raw_response=content,
        )

    def _build_summary(self, data: Dict[str, Any]) -> str:
        """Build narrative summary from structured data"""
        parts = []
        if data.get("chief_complaint"):
            parts.append(f"Chief complaint: {', '.join(data['chief_complaint'])}")
        if data.get("assessment"):
            parts.append(f"Assessment: {', '.join(data['assessment'])}")
        if data.get("plan"):
            parts.append(f"Plan: {', '.join(data['plan'])}")
        return ". ".join(parts)


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude provider for clinical extraction"""

    def __init__(self, api_key: Optional[str] = None, default_model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.default_model = default_model
        self._client = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def supported_models(self) -> List[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
        ]

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import anthropic
            return True
        except ImportError:
            return False

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ClinicalExtractionResult:
        if not self.is_available():
            raise LLMGenerationError("Anthropic provider not available. Check API key and anthropic package.")

        client = self._get_client()

        start_time = time.time()

        try:
            # Build messages with system prompt
            messages = [{"role": "user", "content": user_prompt}]

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages,
            )
        except Exception as e:
            raise LLMGenerationError(f"Anthropic API error: {str(e)}")

        latency_ms = int((time.time() - start_time) * 1000)

        # Parse response
        content = response.content[0].text

        try:
            structured_data = json.loads(content)
        except json.JSONDecodeError:
            raise LLMGenerationError(f"Failed to parse JSON response: {content[:500]}")

        return ClinicalExtractionResult(
            structured_extraction=structured_data,
            summary=structured_data.get("summary", "") or self._build_summary(structured_data),
            provider=self.provider_name,
            model=model,
            prompt_version=kwargs.get("prompt_version", "v1"),
            metadata={
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "latency_ms": latency_ms,
            },
            raw_response=content,
        )

    def _build_summary(self, data: Dict[str, Any]) -> str:
        parts = []
        if data.get("chief_complaint"):
            parts.append(f"Chief complaint: {', '.join(data['chief_complaint'])}")
        if data.get("assessment"):
            parts.append(f"Assessment: {', '.join(data['assessment'])}")
        if data.get("plan"):
            parts.append(f"Plan: {', '.join(data['plan'])}")
        return ". ".join(parts)


class GoogleLLMProvider(LLMProvider):
    """Google Gemini provider for clinical extraction"""

    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-1.5-pro"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.default_model = default_model
        self._model = None

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def supported_models(self) -> List[str]:
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import google.generativeai as genai
            return True
        except ImportError:
            return False

    def _get_model(self, model_name: str):
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(model_name)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gemini-1.5-pro",
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ClinicalExtractionResult:
        if not self.is_available():
            raise LLMGenerationError("Google provider not available. Check API key and google-generativeai package.")

        model_instance = self._get_model(model)

        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if response_format:
            generation_config["response_mime_type"] = "application/json"

        start_time = time.time()

        try:
            response = model_instance.generate_content(
                full_prompt,
                generation_config=generation_config,
            )
        except Exception as e:
            raise LLMGenerationError(f"Google API error: {str(e)}")

        latency_ms = int((time.time() - start_time) * 1000)

        # Parse response
        content = response.text

        try:
            structured_data = json.loads(content)
        except json.JSONDecodeError:
            raise LLMGenerationError(f"Failed to parse JSON response: {content[:500]}")

        return ClinicalExtractionResult(
            structured_extraction=structured_data,
            summary=structured_data.get("summary", "") or self._build_summary(structured_data),
            provider=self.provider_name,
            model=model,
            prompt_version=kwargs.get("prompt_version", "v1"),
            metadata={
                "latency_ms": latency_ms,
            },
            raw_response=content,
        )

    def _build_summary(self, data: Dict[str, Any]) -> str:
        parts = []
        if data.get("chief_complaint"):
            parts.append(f"Chief complaint: {', '.join(data['chief_complaint'])}")
        if data.get("assessment"):
            parts.append(f"Assessment: {', '.join(data['assessment'])}")
        if data.get("plan"):
            parts.append(f"Plan: {', '.join(data['plan'])}")
        return ". ".join(parts)


class LocalLLMProvider(LLMProvider):
    """Local LLM provider (Ollama, vLLM, etc.)"""

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.1"):
        self.base_url = base_url
        self.default_model = default_model

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def supported_models(self) -> List[str]:
        # These would be dynamically fetched from Ollama
        return ["llama3.1", "llama3.1:70b", "mistral", "mixtral", "medllama"]

    def is_available(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "llama3.1",
        temperature: float = 0.1,
        max_tokens: int = 4000,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ClinicalExtractionResult:
        if not self.is_available():
            raise LLMGenerationError("Local LLM provider not available. Check Ollama/vLLM is running.")

        import requests

        # Format for Ollama
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if response_format:
            payload["format"] = "json"

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
        except Exception as e:
            raise LLMGenerationError(f"Local LLM error: {str(e)}")

        latency_ms = int((time.time() - start_time) * 1000)

        # Parse response
        result = response.json()
        content = result.get("response", "")

        try:
            structured_data = json.loads(content)
        except json.JSONDecodeError:
            raise LLMGenerationError(f"Failed to parse JSON response: {content[:500]}")

        return ClinicalExtractionResult(
            structured_extraction=structured_data,
            summary=structured_data.get("summary", "") or self._build_summary(structured_data),
            provider=self.provider_name,
            model=model,
            prompt_version=kwargs.get("prompt_version", "v1"),
            metadata={
                "latency_ms": latency_ms,
            },
            raw_response=content,
        )

    def _build_summary(self, data: Dict[str, Any]) -> str:
        parts = []
        if data.get("chief_complaint"):
            parts.append(f"Chief complaint: {', '.join(data['chief_complaint'])}")
        if data.get("assessment"):
            parts.append(f"Assessment: {', '.join(data['assessment'])}")
        if data.get("plan"):
            parts.append(f"Plan: {', '.join(data['plan'])}")
        return ". ".join(parts)


class LLMClinicalService:
    """
    Main service class for LLM clinical extraction operations.
    Manages provider selection, prompt templates, and schema validation.
    """

    # Default clinical extraction schema
    DEFAULT_SCHEMA = {
        "type": "object",
        "properties": {
            "chief_complaint": {"type": "array", "items": {"type": "string"}},
            "symptoms": {"type": "array", "items": {"type": "string"}},
            "history": {"type": "array", "items": {"type": "string"}},
            "allergies": {"type": "array", "items": {"type": "string"}},
            "medications": {"type": "array", "items": {"type": "string"}},
            "examination": {"type": "array", "items": {"type": "string"}},
            "vitals": {
                "type": "object",
                "properties": {
                    "blood_pressure": {"type": "string"},
                    "heart_rate": {"type": "string"},
                    "temperature": {"type": "string"},
                    "spo2": {"type": "string"},
                },
            },
            "assessment": {"type": "array", "items": {"type": "string"}},
            "investigations": {"type": "array", "items": {"type": "string"}},
            "plan": {"type": "array", "items": {"type": "string"}},
            "follow_up": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
        },
        "required": ["chief_complaint", "symptoms", "assessment", "plan"],
        "additionalProperties": False,
    }

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._default_provider: Optional[str] = None
        self._prompt_template: Optional[str] = None
        self._initialize_providers()
        self._load_default_prompt()

    def _initialize_providers(self):
        """Initialize available providers based on configuration"""
        # The development provider returns canned clinical text. It is only
        # registered where settings explicitly allow it (local dev, tests).
        if getattr(settings, "AI_SCRIBE_ALLOW_MOCK_PROVIDERS", False):
            self._providers["development"] = DevelopmentLLMProvider()

        # OpenAI or any OpenAI-compatible host, once AI_SCRIBE_API_KEY is set.
        openai_provider = OpenAILLMProvider()
        if openai_provider.is_available():
            self._providers["openai"] = openai_provider
            if not self._default_provider:
                self._default_provider = "openai"

        # Try to register Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            anthropic_provider = AnthropicLLMProvider()
            if anthropic_provider.is_available():
                self._providers["anthropic"] = anthropic_provider
                if not self._default_provider:
                    self._default_provider = "anthropic"

        # Try to register Google
        if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            google_provider = GoogleLLMProvider()
            if google_provider.is_available():
                self._providers["google"] = google_provider
                if not self._default_provider:
                    self._default_provider = "google"

        # Try to register Local (Ollama)
        local_provider = LocalLLMProvider()
        if local_provider.is_available():
            self._providers["local"] = local_provider
            if not self._default_provider:
                self._default_provider = "local"

        # An explicitly chosen provider wins when it is actually registered.
        preferred = getattr(settings, "AI_SCRIBE_PROVIDER", "")
        if preferred and preferred in self._providers:
            self._default_provider = preferred

        # Fall back to the development provider only where it is allowed;
        # otherwise there is no provider and callers report "unavailable".
        if not self._default_provider and "development" in self._providers:
            self._default_provider = "development"
            logger.warning("No real LLM provider configured; using the DEVELOPMENT mock provider.")

    def _load_default_prompt(self):
        """Load the default clinical extraction prompt template"""
        self._prompt_template = """You are a medical AI assistant helping doctors create clinical documentation.
Your task is to extract structured clinical information from a doctor-patient conversation transcript.

IMPORTANT RULES:
1. Extract ONLY information explicitly stated in the transcript
2. Do NOT invent, assume, or hallucinate any clinical information
3. If information is not mentioned, use empty arrays/objects
4. Clearly mark uncertain information with "?" prefix
5. Do NOT make autonomous clinical decisions or diagnoses
6. Return ONLY valid JSON matching the provided schema

The output will be reviewed and approved by a licensed physician before becoming part of the medical record.

Patient Context:
- Age: {patient_age}
- Gender: {patient_gender}

Conversation Transcript:
{transcript}

Extract the following clinical information in the specified JSON format:"""

    def get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """Get LLM provider by name or default"""
        name = provider_name or self._default_provider
        if name not in self._providers:
            raise LLMGenerationError(f"LLM provider '{name}' not available. Available: {list(self._providers.keys())}")
        return self._providers[name]

    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """List all available providers with their capabilities"""
        return {
            name: {
                "name": provider.provider_name,
                "supported_models": provider.supported_models,
                "is_available": provider.is_available(),
            }
            for name, provider in self._providers.items()
        }

    def get_schema(self) -> Dict[str, Any]:
        """Get the clinical extraction JSON schema"""
        return self.DEFAULT_SCHEMA

    def get_prompt_template(self) -> str:
        """Get the current prompt template"""
        return self._prompt_template

    def generate_clinical_draft(
        self,
        transcript_text: str,
        language: str = "en",
        patient_context: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        redact_terms: Optional[List[str]] = None,
        redact_names: Optional[List[str]] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        prompt_version: str = "v1",
    ) -> Dict[str, Any]:
        """
        Generate clinical draft from transcript.

        Args:
            transcript_text: Full conversation transcript
            language: Language code
            patient_context: Dict with age and gender. A name is never sent.
            redact_terms: Patient identifiers (phones, address, IDs) masked
                in the transcript before it leaves the server
            redact_names: Patient and family names, masked word by word
            provider: Specific provider to use
            model: Specific model to use
            temperature: Sampling temperature
            prompt_version: Version of prompt template

        Returns:
            Dict with structured_extraction, summary, provider, model, prompt_version, metadata
        """
        llm_provider = self.get_provider(provider)

        # Use provider's default model if not specified
        if model is None:
            model = llm_provider.default_model if hasattr(llm_provider, 'default_model') else llm_provider.supported_models[0]

        # Build prompts
        patient_ctx = patient_context or {}
        system_prompt = self._build_system_prompt(language)
        user_prompt = self._build_user_prompt(
            redact_identifiers(transcript_text, redact_terms or [], redact_names),
            patient_ctx.get("age", "Unknown"),
            patient_ctx.get("gender", "Unknown"),
        )

        # Generate
        result = llm_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            max_tokens=4000,
            response_format=self.DEFAULT_SCHEMA,
            prompt_version=prompt_version,
        )

        # Validate output against schema
        self._validate_extraction(result.structured_extraction)

        return {
            "structured_extraction": result.structured_extraction,
            "summary": result.summary,
            "provider": result.provider,
            "model": result.model,
            "prompt_version": result.prompt_version,
            "metadata": result.metadata,
        }

    def _build_system_prompt(self, language: str) -> str:
        """Build system prompt with language-specific instructions"""
        lang_instructions = {
            "en": "Respond in English.",
            "hi": "हिंदी में जवाब दें।",
            # Hinglish consultations: Indian clinical notes are written in English.
            "hinglish": "The transcript mixes Hindi and English. Respond in English.",
            "auto": "Respond in the same language as the transcript.",
        }
        lang_instruction = lang_instructions.get(language, lang_instructions["en"])

        return f"""You are a medical AI assistant helping doctors create clinical documentation.
Your task is to extract structured clinical information from a doctor-patient conversation transcript.

IMPORTANT RULES:
1. Extract ONLY information explicitly stated in the transcript
2. Do NOT invent, assume, or hallucinate any clinical information
3. If information is not mentioned, use empty arrays/objects
4. Clearly mark uncertain information with "?" prefix
5. Do NOT make autonomous clinical decisions or diagnoses
6. Return ONLY valid JSON matching the provided schema
7. {lang_instruction}

The output will be reviewed and approved by a licensed physician before becoming part of the medical record."""

    def _build_user_prompt(
        self,
        transcript: str,
        patient_age: Any,
        patient_gender: str,
    ) -> str:
        """Build user prompt with transcript and non-identifying patient context"""
        return f"""Patient Context:
- Age: {patient_age}
- Gender: {patient_gender}

Conversation Transcript:
{transcript}

Extract the clinical information in the specified JSON format. 
Remember: Only extract what is explicitly stated. Use empty arrays for missing information."""

    MAX_ITEM_CHARS = 1000
    MAX_ITEMS = 50

    @classmethod
    def coerce_section(cls, section: str, value: Any) -> Any:
        """
        A doctor's edit of one draft section, held to the same schema as
        provider output. Raises ValueError for an unknown section.
        """
        if section not in cls.DEFAULT_SCHEMA["properties"]:
            raise ValueError(f"Unknown section: {section}")
        extraction = {section: value}
        cls._validate_extraction(extraction)
        return extraction[section]

    @classmethod
    def _validate_extraction(cls, extraction: Dict[str, Any]) -> None:
        """
        Coerce provider output to the schema in place: unknown keys are
        dropped, list fields hold only short strings, the vitals object only
        known string fields. Nothing is invented: missing fields become empty.
        """
        if not isinstance(extraction, dict):
            raise LLMGenerationError("Provider output is not a JSON object.")
        properties = cls.DEFAULT_SCHEMA["properties"]
        for key in list(extraction):
            if key not in properties:
                extraction.pop(key)
        for field, prop in properties.items():
            value = extraction.get(field)
            if prop["type"] == "array":
                if value in (None, ""):
                    value = []
                elif not isinstance(value, list):
                    value = [value]
                extraction[field] = [
                    str(item).strip()[: cls.MAX_ITEM_CHARS]
                    for item in value[: cls.MAX_ITEMS]
                    if item not in (None, "") and not isinstance(item, (dict, list))
                ]
            elif prop["type"] == "object":
                allowed = prop.get("properties", {})
                value = value if isinstance(value, dict) else {}
                extraction[field] = {
                    k: str(v).strip()[: cls.MAX_ITEM_CHARS]
                    for k, v in value.items()
                    if k in allowed and v not in (None, "") and not isinstance(v, (dict, list))
                }
            elif prop["type"] == "string":
                extraction[field] = "" if value is None else str(value).strip()[: cls.MAX_ITEM_CHARS * 4]
