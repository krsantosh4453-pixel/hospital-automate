"""
Patient consent: signed consent forms and patient-controlled record sharing
("Share Everywhere"). Every share is scoped, expiring and revocable, and every
read by a recipient is logged.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

# Record types a share may include.
SHARE_SCOPES = {
    "visits": "Visit history",
    "diagnoses": "Diagnoses",
    "prescriptions": "Prescriptions",
    "lab_results": "Released lab results",
    "discharge_summaries": "Finalized discharge summaries",
    "allergies": "Allergies",
}

# Versioned consent-form templates. Text changes require a new version.
CONSENT_FORMS = {
    "general-treatment": {"name": "General Treatment Consent", "version": "1.0", "required": True,
                          "description": "Consent for general medical treatment."},
    "surgery": {"name": "Surgical Procedure Consent", "version": "1.0", "required": False,
                "description": "Informed consent for a surgical procedure."},
    "anesthesia": {"name": "Anesthesia Consent", "version": "1.0", "required": False,
                   "description": "Consent for anaesthesia administration."},
    "ai-recording": {"name": "AI Consultation Recording Consent", "version": "1.0", "required": False,
                     "description": "Consent to record the consultation for AI-assisted notes "
                                    "reviewed by your doctor."},
    "data-sharing": {"name": "Health Data Sharing Consent", "version": "1.0", "required": False,
                     "description": "Consent to share selected records with another provider."},
}


class ConsentRecord(models.Model):
    """A patient's signature on one version of a consent form at a hospital."""

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="consent_records")
    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.CASCADE, related_name="consent_records")
    form_code = models.CharField(max_length=50)
    form_version = models.CharField(max_length=20)
    signed_name = models.CharField(max_length=150)
    signed_by_proxy = models.BooleanField(default=False)
    proxy_relationship = models.CharField(max_length=50, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    signed_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-signed_at"]
        indexes = [models.Index(fields=["hospital", "patient"])]

    @property
    def is_active(self):
        return self.revoked_at is None


class RecordShare(models.Model):
    """Permission from a patient for a recipient hospital to read part of their record."""

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="record_shares")
    # Hospital whose records are shared.
    source_hospital = models.ForeignKey(
        "hospital.Hospital", on_delete=models.CASCADE, related_name="outgoing_record_shares"
    )
    recipient_hospital = models.ForeignKey(
        "hospital.Hospital", on_delete=models.CASCADE, related_name="incoming_record_shares"
    )
    scope = models.JSONField(default=list)
    purpose = models.CharField(max_length=200)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient_hospital", "revoked_at", "expires_at"]),
            models.Index(fields=["patient", "created_at"]),
        ]

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now()


class RecordShareAccess(models.Model):
    """One read of shared records by recipient staff."""

    share = models.ForeignKey(RecordShare, on_delete=models.CASCADE, related_name="accesses")
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-accessed_at"]
