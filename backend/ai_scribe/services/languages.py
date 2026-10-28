"""
Consultation languages the AI scribe accepts.

Doctors in OPD often speak Hindi, English, or both in one sentence (Hinglish).
Each consultation stores one of the codes below; providers translate the code
into whatever their API expects.
"""

ENGLISH = "en"
HINDI = "hi"
HINGLISH = "hinglish"
AUTO = "auto"

SUPPORTED_LANGUAGES = {
    ENGLISH: "English",
    HINDI: "Hindi",
    HINGLISH: "Hinglish (Hindi + English mixed)",
    AUTO: "Detect automatically",
}

_ALIASES = {
    "en-in": ENGLISH,
    "en-us": ENGLISH,
    "en-gb": ENGLISH,
    "english": ENGLISH,
    "hi-in": HINDI,
    "hindi": HINDI,
    "hi-en": HINGLISH,
    "hien": HINGLISH,
}

# Whisper reports the language it heard as a lowercase English name.
_DETECTED_NAMES = {
    "english": ENGLISH,
    "hindi": HINDI,
}

# Whisper uses the prompt as "previous text": a sample in the target style
# steers spelling and script. These are style hints only, never patient data.
WHISPER_STYLE_PROMPTS = {
    ENGLISH: (
        "Doctor: Since when do you have fever? Patient: Three days, with body ache. "
        "Doctor: Take paracetamol 650 mg twice daily and get a CBC done."
    ),
    HINDI: (
        "डॉक्टर: बुखार कब से है? मरीज़: तीन दिन से, बदन दर्द भी है। "
        "डॉक्टर: पैरासिटामोल 650 mg दिन में दो बार लीजिए और CBC करवाइए।"
    ),
    HINGLISH: (
        "Doctor: Fever kab se hai? Patient: Teen din se, body ache bhi hai. "
        "Doctor: Paracetamol 650 mg din mein do baar lijiye aur CBC karwa lijiye."
    ),
}


def normalize_language(code) -> str:
    """Return the canonical code for ``code``; raise ValueError if unsupported."""
    value = str(code or "").strip().lower()
    value = _ALIASES.get(value, value)
    if value not in SUPPORTED_LANGUAGES:
        allowed = ", ".join(SUPPORTED_LANGUAGES)
        raise ValueError(f"Unsupported language '{code}'. Use one of: {allowed}.")
    return value


def detected_language_code(name) -> str:
    """Map a provider's detected-language label ("hindi", "hi") to our code."""
    value = str(name or "").strip().lower()
    return _DETECTED_NAMES.get(value, value)
