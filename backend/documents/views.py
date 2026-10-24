"""
Documents Views for Hospital Management System.

Patient documents belong to the hospital they were uploaded at
(PatientDocument.hospital). Staff see documents of the hospitals they act
in; a patient sees their own. Every read of file content is audited.
"""

import logging
import os

import magic
from django.http import FileResponse
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import record_audit
from patients.models import Patient, PatientDocument
from users.permissions import (
    get_linked_patient,
    get_request_hospital_id,
    get_user_hospital_ids,
    get_user_roles,
    is_active_staff,
)
from users.models import StaffRole

logger = logging.getLogger(__name__)

# Allowed file types for healthcare documents
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'image/dicom',
    'application/dicom',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    '.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.dcm', '.txt', '.doc', '.docx'
}

# Types a browser may render inline; anything else is always an attachment.
INLINE_TYPES = {
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
}

CATEGORIES = {
    'clinical': 'Clinical Notes',
    'lab': 'Lab Reports',
    'imaging': 'Imaging',
    'prescription': 'Prescriptions',
    'consent': 'Consent Forms',
    'discharge': 'Discharge Summaries',
    'insurance': 'Insurance Documents',
    'doctor': 'Doctor',
    'other': 'Other',
}

# Roles allowed to upload or delete clinical documents.
UPLOAD_ROLES = {
    StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER, StaffRole.DOCTOR, StaffRole.NURSE,
    StaffRole.RECEPTIONIST, StaffRole.LAB_STAFF,
}
DELETE_ROLES = {StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER}


def validate_file_upload(file):
    """
    Validate uploaded file for type, size, and content.
    Returns (is_valid, error_message).
    """
    if file.size > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB"

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    # Content-based check: the declared name/extension is not trusted.
    file.seek(0)
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)

    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"File content type '{mime_type}' is not allowed."

    return True, None


def _acting_hospital_ids(request):
    allowed = get_user_hospital_ids(request.user)
    acting = get_request_hospital_id(request)
    if acting is not None:
        if acting not in allowed:
            raise PermissionDenied("You are not a member of that hospital.")
        return [acting]
    return allowed


def visible_documents(request):
    """Documents the requesting user may see."""
    if is_active_staff(request.user):
        return PatientDocument.objects.filter(
            hospital_id__in=_acting_hospital_ids(request)
        ).select_related('patient', 'hospital')
    linked_patient = get_linked_patient(request.user)
    if linked_patient:
        return PatientDocument.objects.filter(patient=linked_patient).select_related('patient', 'hospital')
    return PatientDocument.objects.none()


def _get_document(request, id):
    try:
        return visible_documents(request).get(pk=int(id))
    except (PatientDocument.DoesNotExist, ValueError, TypeError):
        raise NotFound("Document not found.")


def _payload(doc, with_patient=True):
    data = {
        'id': doc.id,
        'hospital': doc.hospital_id,
        'title': doc.title,
        'folder': doc.folder,
        'file_size': doc.file.size if doc.file else 0,
        'uploaded_at': doc.uploaded_at,
    }
    if with_patient:
        data['patient'] = doc.patient_id
        data['patient_name'] = doc.patient.name
    return data


def _file_response(document, inline):
    if not document.file:
        raise NotFound("File not found.")
    try:
        handle = document.file.open('rb')
    except (FileNotFoundError, OSError):
        raise NotFound("File not found.")
    name = os.path.basename(document.file.name)
    ext = os.path.splitext(name)[1].lower()
    content_type = INLINE_TYPES.get(ext) if inline else None
    response = FileResponse(handle, content_type=content_type or 'application/octet-stream')
    disposition = 'inline' if content_type else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{name}"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


class DocumentBaseView(APIView):
    """Base view for document management."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class DocumentListView(DocumentBaseView):
    """List documents with filtering."""

    def get(self, request):
        documents = visible_documents(request)
        patient_id = request.query_params.get('patient')
        if patient_id:
            documents = documents.filter(patient_id=patient_id)
        folder = request.query_params.get('folder')
        if folder:
            documents = documents.filter(folder=folder)
        documents = documents.order_by('-uploaded_at')
        total = documents.count()
        return Response({
            'documents': [_payload(doc) for doc in documents[:100]],
            'count': total,
        })


class DocumentDetailView(DocumentBaseView):
    """Document metadata detail."""

    def get(self, request, id):
        return Response(_payload(_get_document(request, id)))

    def delete(self, request, id):
        document = _get_document(request, id)
        if not set(get_user_roles(request.user, document.hospital_id)) & DELETE_ROLES:
            raise PermissionDenied("Only an administrator can delete documents.")
        record_audit(request, "documents.document.delete", document, hospital=document.hospital_id)
        if document.file:
            try:
                document.file.delete(save=False)
            except Exception:
                logger.warning("Failed to delete file for document %s", document.pk)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentDownloadView(DocumentBaseView):
    def get(self, request, id):
        document = _get_document(request, id)
        record_audit(request, "documents.document.download", document, hospital=document.hospital_id)
        return _file_response(document, inline=False)


class DocumentPreviewView(DocumentBaseView):
    """Inline preview for PDFs and images; other types download."""

    def get(self, request, id):
        document = _get_document(request, id)
        record_audit(request, "documents.document.preview", document, hospital=document.hospital_id)
        return _file_response(document, inline=True)


def _patient_in_scope(request, patient_id):
    """The patient, if the requester may work with them at the acting hospital."""
    try:
        patient = Patient.objects.get(pk=int(patient_id))
    except (Patient.DoesNotExist, ValueError, TypeError):
        raise NotFound("Patient not found.")
    if is_active_staff(request.user):
        hospital_ids = _acting_hospital_ids(request)
        registered = (
            patient.hospital_id in hospital_ids
            or patient.hospital_memberships.filter(hospital_id__in=hospital_ids, is_active=True).exists()
        )
        if not registered:
            raise NotFound("Patient not found.")
        return patient
    linked_patient = get_linked_patient(request.user)
    if linked_patient and linked_patient.pk == patient.pk:
        return patient
    raise NotFound("Patient not found.")


class PatientDocumentListView(DocumentBaseView):
    """List documents for a specific patient."""

    def get(self, request, patient_id):
        patient = _patient_in_scope(request, patient_id)
        documents = visible_documents(request).filter(patient=patient).order_by('-uploaded_at')
        return Response({
            'patient_id': patient.pk,
            'patient_name': patient.name,
            'documents': [_payload(doc, with_patient=False) for doc in documents],
            'count': documents.count(),
        })


class PatientDocumentUploadView(DocumentBaseView):
    """Upload a document for a patient at the acting hospital."""

    def post(self, request, patient_id):
        patient = _patient_in_scope(request, patient_id)

        if is_active_staff(request.user):
            hospital_ids = _acting_hospital_ids(request)
            if len(hospital_ids) != 1:
                return Response(
                    {"error": "Select the hospital this document belongs to."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            hospital_id = hospital_ids[0]
            if not set(get_user_roles(request.user, hospital_id)) & UPLOAD_ROLES:
                raise PermissionDenied("Your role cannot upload patient documents.")
        else:
            # Patient self-upload goes to the hospital they selected in the portal.
            hospital_id = get_request_hospital_id(request)
            if hospital_id is None or not (
                patient.hospital_id == hospital_id
                or patient.hospital_memberships.filter(hospital_id=hospital_id, is_active=True).exists()
            ):
                return Response(
                    {"error": "Select the hospital this document is for."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                {"error": "A file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_valid, error = validate_file_upload(upload)
        if not is_valid:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document = PatientDocument.objects.create(
            patient=patient,
            hospital_id=hospital_id,
            title=(request.data.get('title') or upload.name)[:150],
            folder=(request.data.get('folder') or 'general')[:100],
            file=upload,
        )
        record_audit(request, "documents.document.upload", document, hospital=hospital_id)
        return Response(_payload(document), status=status.HTTP_201_CREATED)


class DocumentCategoryListView(DocumentBaseView):
    """List document categories/folders."""

    def get(self, request):
        return Response({'categories': [{'id': key, 'name': name} for key, name in CATEGORIES.items()]})


class DocumentCategoryDetailView(DocumentBaseView):
    """Document category detail."""

    def get(self, request, id):
        if id not in CATEGORIES:
            raise NotFound("Category not found.")
        return Response({'id': id, 'name': CATEGORIES[id]})


class DocumentSearchView(DocumentBaseView):
    """Search documents by title."""

    def get(self, request):
        query = request.query_params.get('q', '')
        documents = visible_documents(request)
        if query:
            documents = documents.filter(title__icontains=query)
        total = documents.count()
        return Response({
            'query': query,
            'results': [_payload(doc) for doc in documents.order_by('-uploaded_at')[:50]],
            'count': total,
        })
