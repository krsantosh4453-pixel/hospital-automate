from django.conf import settings
from django.db import models


class ABHALink(models.Model):
    """
    A patient's ABHA (Ayushman Bharat Health Account), verified by OTP with
    ABDM at this hospital. Only verified links are stored.
    """

    class OtpSystem(models.TextChoices):
        AADHAAR = "aadhaar", "Aadhaar-linked mobile"
        ABDM = "abdm", "ABHA-linked mobile"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="abha_links")
    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.CASCADE, related_name="abha_links")
    abha_number = models.CharField(max_length=17, db_index=True, help_text="14 digits, e.g. 91-1234-5678-9012")
    abha_address = models.CharField(max_length=100, blank=True, help_text="e.g. name@sbx")
    name_on_abha = models.CharField(max_length=200, blank=True)
    otp_system = models.CharField(max_length=10, choices=OtpSystem.choices)
    verified_at = models.DateTimeField(auto_now=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["patient", "hospital"], name="abdm_one_abha_per_patient_hospital"),
            models.UniqueConstraint(fields=["hospital", "abha_number"], name="abdm_abha_once_per_hospital"),
        ]

    def __str__(self):
        return f"ABHA ****{self.abha_number[-4:]}"
