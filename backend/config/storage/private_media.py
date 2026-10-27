"""
Private media storage for sensitive healthcare documents.

Ensures patient documents, medical reports, and other sensitive files
are not publicly accessible and require authentication/authorization.
"""

import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    """
    Storage for private media files.

    Files are stored outside the web root and served through
    a view that checks permissions.
    """

    def __init__(self, *args, **kwargs):
        # Use MEDIA_ROOT/private by default
        location = kwargs.pop('location', os.path.join(settings.MEDIA_ROOT, 'private'))
        base_url = kwargs.pop('base_url', None)  # No direct URL access
        super().__init__(location=location, base_url=base_url, *args, **kwargs)

    def url(self, name):
        """
        Private files don't have direct URLs.
        Use the serve_private_media view instead.
        """
        return None


@deconstructible
class PatientDocumentStorage(FileSystemStorage):
    """
    Storage for patient documents.

    Organizes files by hospital and patient for access control.
    """

    def __init__(self, *args, **kwargs):
        location = kwargs.pop('location', os.path.join(settings.MEDIA_ROOT, 'patient_documents'))
        super().__init__(location=location, *args, **kwargs)

    def get_available_name(self, name, max_length=None):
        """Generate unique filename to prevent overwrites."""
        import uuid
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        unique_name = f"{file_root}_{uuid.uuid4().hex[:8]}{file_ext}"
        return os.path.join(dir_name, unique_name)


@deconstructible
class ConsultationAudioStorage(FileSystemStorage):
    """
    Storage for consultation audio recordings.

    Highly sensitive - requires strict access control.
    """

    def __init__(self, *args, **kwargs):
        location = kwargs.pop('location', os.path.join(settings.MEDIA_ROOT, 'consultation_audio'))
        super().__init__(location=location, *args, **kwargs)

    def get_available_name(self, name, max_length=None):
        import uuid
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        unique_name = f"{file_root}_{uuid.uuid4().hex[:12]}{file_ext}"
        return os.path.join(dir_name, unique_name)


# Cloud storage variants (for production with S3/GCS/Azure)
# These would be used when DEFAULT_FILE_STORAGE is set to a cloud backend

try:
    from storages.backends.s3boto3 import S3Boto3Storage

    class PrivateS3Storage(S3Boto3Storage):
        """Private S3 storage with no public access."""
        default_acl = 'private'
        file_overwrite = False
        custom_domain = False
        querystring_auth = True
        querystring_expire = 3600  # 1 hour signed URLs

    class PatientDocumentS3Storage(PrivateS3Storage):
        """S3 storage for patient documents."""
        location = 'patient_documents'

    class ConsultationAudioS3Storage(PrivateS3Storage):
        """S3 storage for consultation audio."""
        location = 'consultation_audio'

except ImportError:
    # storages not installed
    pass


def get_storage_for_model(model_name: str):
    """
    Get appropriate storage for a model.

    Returns storage instance based on model type and configuration.
    """
    storage_map = {
        'PatientDocument': 'config.storage.PatientDocumentStorage',
        'ConsultationSession': 'config.storage.ConsultationAudioStorage',
        'LabResult': 'config.storage.PrivateMediaStorage',
        'MedicalReport': 'config.storage.PrivateMediaStorage',
        'Prescription': 'config.storage.PrivateMediaStorage',
        'DischargeSummary': 'config.storage.PrivateMediaStorage',
    }

    storage_path = storage_map.get(model_name, 'config.storage.PrivateMediaStorage')

    # Import and instantiate
    module_path, class_name = storage_path.rsplit('.', 1)
    module = __import__(module_path, fromlist=[class_name])
    storage_class = getattr(module, class_name)
    return storage_class()