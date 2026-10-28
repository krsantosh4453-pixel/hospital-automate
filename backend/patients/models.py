from django.conf import settings
from django.db import models


class Patient(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_account",
    )
    name = models.CharField(max_length=100, db_index=True)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=20)
    phone = models.CharField(max_length=15, db_index=True)
    address = models.TextField(blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    doctor = models.CharField(max_length=100, blank=True)
    # Free-text condition/reason shown in the Patients UI
    condition = models.CharField(max_length=150, blank=True)
    # Next of kin to call in an emergency (requirement B4). All optional.
    emergency_contact_name = models.CharField(max_length=100, blank=True, default="")
    emergency_contact_relation = models.CharField(max_length=50, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=15, blank=True, default="")
    # Direct hospital link used by the Patients UI.
    # PatientHospital (membership) is kept for backward compatibility.
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_patients",
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        default="Active",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["hospital", "created_at"]),
            models.Index(fields=["name", "hospital"]),
        ]


class PatientHospital(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="hospital_memberships"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="patients",
        db_index=True
    )
    uhid = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("patient", "hospital")
        indexes = [
            models.Index(fields=["hospital", "is_active"]),
            models.Index(fields=["patient", "is_active"]),
        ]

    def __str__(self):
        return f"{self.patient.name} - {self.hospital.name}"


class PatientDocument(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_documents",
        db_index=True,
    )
    title = models.CharField(max_length=150)
    folder = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to="patient_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title