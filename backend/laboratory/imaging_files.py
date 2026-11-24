"""
Prompt 5 (MF-005): images attached to an imaging study.

Files are stored as ordinary patient documents (patients.PatientDocument,
the existing private storage), linked to their study, and are only ever
served through the study's audited endpoint; never as a public media URL.

Accepted: PNG, JPEG, DICOM and PDF, checked three ways: the size, the file
extension, and the content itself (libmagic), which must match the
extension, so a script or executable renamed ".png" is refused.
"""

import os

import magic
from rest_framework.exceptions import ValidationError

from documents.views import validate_file_upload

MAX_IMAGE_BYTES = 50 * 1024 * 1024  # the documents limit (documents.views.MAX_FILE_SIZE)
CONTENT_FOR_EXTENSION = {
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".dcm": {"application/dicom", "image/dicom"},
    ".pdf": {"application/pdf"},
}
FOLDER = "imaging"


def check_image(upload):
    """Raise ValidationError unless ``upload`` is an allowed, non-empty imaging file."""
    if upload is None:
        raise ValidationError({"file": "Choose a file to upload."})
    if upload.size == 0:
        raise ValidationError({"file": "The file is empty."})
    if upload.size > MAX_IMAGE_BYTES:
        raise ValidationError({"file": f"The file is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB."})
    extension = os.path.splitext(upload.name or "")[1].lower()
    if extension not in CONTENT_FOR_EXTENSION:
        raise ValidationError({"file": "Upload a PNG, JPEG, DICOM (.dcm) or PDF file."})
    valid, message = validate_file_upload(upload)
    if not valid:
        raise ValidationError({"file": message})
    upload.seek(0)
    content = magic.from_buffer(upload.read(2048), mime=True)
    upload.seek(0)
    if content not in CONTENT_FOR_EXTENSION[extension]:
        raise ValidationError({"file": "The file's content does not match its type."})


def store_image(study, upload, title=""):
    """Save ``upload`` as a document of the study's patient at the study's hospital."""
    from patients.models import PatientDocument

    check_image(upload)
    name = (title or "").strip()[:150] or f"{study.modality} {study.body_part} ({study.accession_number})"[:150]
    return PatientDocument.objects.create(
        patient_id=study.patient_id, hospital_id=study.hospital_id, imaging_study=study,
        title=name, folder=FOLDER, file=upload,
    )


def image_payload(study, document):
    """What a list of a study's images shows. The file is fetched through the study, never /media/."""
    return {
        "id": document.pk,
        "title": document.title,
        "file_size": document.file.size if document.file else 0,
        "uploaded_at": document.uploaded_at,
        "url": f"/api/laboratory/imaging/{study.pk}/images/{document.pk}/",
    }
