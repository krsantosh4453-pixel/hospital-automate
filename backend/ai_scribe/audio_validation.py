"""
Upload checks for consultation audio (S-L6, 2026-11-18).

The client's Content-Type and file name are claims, not facts. An upload is
accepted only when its first bytes are the signature of an audio container we
accept, and that container agrees with the declared type. The stored file gets
a server-chosen name and extension, so a client-supplied name such as
``x.html`` never reaches storage.

Signatures (first bytes of the file):
- WAV: ``RIFF`` .... ``WAVE``
- MP3: an ``ID3`` tag, or an MPEG audio frame sync (11 set bits)
- MP4 / M4A: a ``ftyp`` box at offset 4
- Ogg (Opus/Vorbis): ``OggS``
- WebM (Matroska EBML): ``1A 45 DF A3``

This is a container check, not a decoder: it stops HTML, scripts, images and
executables posing as audio. The STT provider still decodes the audio.
"""

import uuid

HEADER_BYTES = 16

# Declared type (without parameters) -> the container it must be.
DECLARED_CONTAINER = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/m4a": "mp4",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
}

EXTENSION = {"wav": "wav", "mp3": "mp3", "mp4": "m4a", "ogg": "ogg", "webm": "webm"}


def sniff_container(head):
    """The audio container these leading bytes belong to, else None."""
    head = bytes(head or b"")
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:3] == b"ID3":
        return "mp3"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "mp3"
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return "mp4"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    return None


def declared_type(upload):
    return (getattr(upload, "content_type", "") or "").split(";")[0].strip().lower()


def read_head(upload):
    """The first bytes of an uploaded file, leaving it rewound for storage."""
    upload.seek(0)
    head = upload.read(HEADER_BYTES)
    upload.seek(0)
    return head


def container_error(upload):
    """An error message when the bytes are not the declared audio, else None."""
    expected = DECLARED_CONTAINER.get(declared_type(upload))
    if expected is None:
        return f"Unsupported audio format. Allowed: {', '.join(DECLARED_CONTAINER)}"
    actual = sniff_container(read_head(upload))
    if actual is None:
        return "The uploaded file is not a recognised audio recording."
    if actual != expected:
        return "The uploaded file's content does not match its declared audio format."
    return None


def safe_name(upload, prefix):
    """A server-chosen storage name with the extension of the detected container."""
    container = sniff_container(read_head(upload)) or "bin"
    return f"{prefix}-{uuid.uuid4().hex}.{EXTENSION.get(container, 'bin')}"
