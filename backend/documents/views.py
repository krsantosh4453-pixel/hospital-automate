"""
Documents Views for Hospital Management System.

Provides document management with access control for sensitive healthcare documents.
"""

import os
import magic
from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, NotFound
import logging

from patients.models import Patient, PatientDocument
from users.permissions import (
    get_user_hospital_ids,
    get_linked_patient,
    is_active_staff,
    user_has_hospital_access,
)

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


def validate_file_upload(file):
    """
    Validate uploaded file for type, size, and content.
    Returns (is_valid, error_message).
    """
    # Check file size
    if file.size > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB"

    # Check file extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"

    # Check MIME type using python-magic (content-based)
    file.seek(0)
    mime_type = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)

    if mime_type not in ALLOWED_MIME_TYPES:
        return False, f"File content type '{mime_type}' is not allowed."

    return True, None


def check_patient_document_access(request, patient):
    """
    Check if user has permission to access patient's documents.
    """
    # Staff users: check hospital membership
    if is_active_staff(request.user):
        from users.permissions import get_user_active_hospital_memberships
        memberships = get_user_active_hospital_memberships(request.user)
        patient_hospitals = patient.hospital_memberships.filter(is_active=True).values_list('hospital_id', flat=True)
        user_hospitals = memberships.values_list('hospital_id', flat=True)

        # Check if user has access to any of the patient's hospitals
        if not set(patient_hospitals).intersection(set(user_hospitals)):
            # Also check direct hospital link
            if patient.hospital_id and patient.hospital_id not in user_hospitals:
                return False
        return True

    # Patient users: check if linked to this patient
    linked_patient = get_linked_patient(request.user)
    if linked_patient and linked_patient.id == patient.id:
        return True

    return False


class DocumentBaseView(APIView):
    """Base view for document management."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class DocumentListView(DocumentBaseView):
    """List documents with filtering."""

    def get(self, request):
        # Staff users see documents from their hospitals
        if is_active_staff(request.user):
            hospital_ids = get_user_hospital_ids(request.user)
            documents = PatientDocument.objects.filter(
                patient__hospital_memberships__hospital_id__in=hospital_ids,
                patient__hospital_memberships__is_active=True
            ).select_related('patient', 'patient__hospital').distinct()
        else:
            # Patients see only their own documents
            linked_patient = get_linked_patient(request.user)
            if not linked_patient:
                return Response({'documents': [], 'count': 0})
            documents = PatientDocument.objects.filter(patient=linked_patient)

        # Apply filters
        patient_id = request.query_params.get('patient')
        if patient_id:
            documents = documents.filter(patient_id=patient_id)

        folder = request.query_params.get('folder')
        if folder:
            documents = documents.filter(folder=folder)

        documents = documents.order_by('-uploaded_at')[:100]

        return Response({
            'documents': [
                {
                    'id': doc.id,
                    'patient': doc.patient_id,
                    'patient_name': doc.patient.name,
                    'title': doc.title,
                    'folder': doc.folder,
                    'file_size': doc.file.size if doc.file else 0,
                    'uploaded_at': doc.uploaded_at,
                }
                for doc in documents
            ],
            'count': documents.count(),
        })


class DocumentDetailView(DocumentBaseView):
    """Document metadata detail."""

    def get(self, request, id):
        try:
            document = PatientDocument.objects.select_related('patient').get(pk=id)
        except PatientDocument.DoesNotExist:
            raise NotFound("Document not found.")

        if not check_patient_document_access(request, document.patient):
            raise PermissionDenied("You do not have permission to access this document.")

        return Response({
            'id': document.id,
            'patient': document.patient_id,
            'patient_name': document.patient.name,
            'title': document.title,
            'folder': document.folder,
            'file_size': document.file.size if document.file else 0,
            'uploaded_at': document.uploaded_at,
        })

    def delete(self, request, id):
        try:
            document = PatientDocument.objects.select_related('patient').get(pk=id)
        except PatientDocument.DoesNotExist:
            raise NotFound("Document not found.")

        if not check_patient_document_access(request, document.patient):
            raise PermissionDenied("You do not have permission to delete this document.")

        # Delete file from storage
        if document.file:
            try:
                document.file.delete(save=False)
            except Exception as e:
                logger.warning(f"Failed to delete file for document {id}: {e}")

        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def document_download(request, id):
    """Download document file with access control."""
    try:
        document = PatientDocument.objects.select_related('patient').get(pk=id)
    except PatientDocument.DoesNotExist:
        raise Http404("Document not found.")

    if not check_patient_document_access(request, document.patient):
        raise PermissionDenied("You do not have permission to download this document.")

    if not document.file:
        raise Http404("File not found.")

    # Serve file
    file_path = document.file.path
    if not os.path.exists(file_path):
        raise Http404("File not found on disk.")

    response = FileResponse(
        open(file_path, 'rb'),
        content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(document.file.name)}"'
    response['Content-Length'] = document.file.size

    # Audit log
    logger.info(f"Document downloaded: {id} by user {request.user.id}")

    return response


def document_preview(request, id):
    """Preview document (for images, PDFs)."""
    try:
        document = PatientDocument.objects.select_related('patient').get(pk=id)
    except PatientDocument.DoesNotExist:
        raise Http404("Document not found.")

    if not check_patient_document_access(request, document.patient):
        raise PermissionDenied("You do not have permission to preview this document.")

    if not document.file:
        raise Http404("File not found.")

    file_path = document.file.path
    if not os.path.exists(file_path):
        raise Http404("File not found on disk.")

    # Determine content type for preview
    ext = os.path.splitext(document.file.name)[1].lower()
    content_type_map = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        '.txt': 'text/plain',
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')

    response = FileResponse(
        open(file_path, 'rb'),
        content_type=content_type
    )
    response['Content-Disposition'] = f'inline; filename="{os.path.basename(document.file.name)}"'

    return response


class PatientDocumentListView(DocumentBaseView):
    """List documents for a specific patient."""

    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            raise NotFound("Patient not found.")

        if not check_patient_document_access(request, patient):
            raise PermissionDenied("You do not have permission to access this patient's documents.")

        documents = patient.documents.all().order_by('-uploaded_at')

        return Response({
            'patient_id': patient_id,
            'patient_name': patient.name,
            'documents': [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'folder': doc.folder,
                    'file_size': doc.file.size if doc.file else 0,
                    'uploaded_at': doc.uploaded_at,
                }
                for doc in documents
            ],
            'count': documents.count(),
        })


class PatientDocumentUploadView(DocumentBaseView):
    """Upload document for a patient."""

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            raise NotFound("Patient not found.")

        if not check_patient_document_access(request, patient):
            raise PermissionDenied("You do not have permission to upload documents for this patient.")

        upload = request.FILES.get('file')
        if upload is None:
            return Response(
                {"error": "A file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file
        is_valid, error = validate_file_upload(upload)
        if not is_valid:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = (request.data.get('title') or upload.name)[:150]
        folder = (request.data.get('folder') or 'general')[:100]

        document = PatientDocument.objects.create(
            patient=patient,
            title=title,
            folder=folder,
            file=upload,
        )

        # Audit log
        logger.info(f"Document uploaded: {document.id} for patient {patient_id} by user {request.user.id}")

        return Response({
            'id': document.id,
            'patient': document.patient_id,
            'title': document.title,
            'folder': document.folder,
            'file_size': document.file.size,
            'uploaded_at': document.uploaded_at,
        }, status=status.HTTP_201_CREATED)


class DocumentCategoryListView(DocumentBaseView):
    """List document categories/folders."""

    def get(self, request):
        return Response({
            'categories': [
                {'id': 'clinical', 'name': 'Clinical Notes'},
                {'id': 'lab', 'name': 'Lab Reports'},
                {'id': 'imaging', 'name': 'Imaging'},
                {'id': 'prescription', 'name': 'Prescriptions'},
                {'id': 'consent', 'name': 'Consent Forms'},
                {'id': 'discharge', 'name': 'Discharge Summaries'},
                {'id': 'insurance', 'name': 'Insurance Documents'},
                {'id': 'other', 'name': 'Other'},
            ]
        })


class DocumentCategoryDetailView(DocumentBaseView):
    """Document category detail."""

    def get(self, request, id):
        categories = {
            'clinical': 'Clinical Notes',
            'lab': 'Lab Reports',
            'imaging': 'Imaging',
            'prescription': 'Prescriptions',
            'consent': 'Consent Forms',
            'discharge': 'Discharge Summaries',
            'insurance': 'Insurance Documents',
            'other': 'Other',
        }
        if id not in categories:
            raise NotFound("Category not found.")
        return Response({'id': id, 'name': categories[id]})


def document_search(request):
    """Search documents."""
    query = request.query_params.get('q', '')

    if is_active_staff(request.user):
        hospital_ids = get_user_hospital_ids(request.user)
        documents = PatientDocument.objects.filter(
            patient__hospital_memberships__hospital_id__in=hospital_ids,
            patient__hospital_memberships__is_active=True
        ).select_related('patient').distinct()
    else:
        linked_patient = get_linked_patient(request.user)
        if not linked_patient:
            return Response({'query': query, 'results': [], 'count': 0})
        documents = linked_patient.documents.all()

    if query:
        documents = documents.filter(title__icontains=query)

    documents = documents[:50]

    return Response({
        'query': query,
        'results': [
            {
                'id': doc.id,
                'patient': doc.patient_id,
                'patient_name': doc.patient.name,
                'title': doc.title,
                'folder': doc.folder,
                'uploaded_at': doc.uploaded_at,
            }
            for doc in documents
        ],
        'count': documents.count(),
    })