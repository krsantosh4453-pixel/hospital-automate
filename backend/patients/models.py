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
    # Demographics (requirement B3). Address parts are kept beside the
    # free-text ``address`` used by older screens.
    marital_status = models.CharField(
        max_length=20, blank=True, default="",
        choices=[(v, v) for v in ("Single", "Married", "Widowed", "Divorced", "Separated")],
    )
    address_line = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    district = models.CharField(max_length=80, blank=True, default="")
    state = models.CharField(max_length=80, blank=True, default="")
    pincode = models.CharField(max_length=6, blank=True, default="")
    # Only the ID type and its last four characters: the full number of a
    # government ID (e.g. Aadhaar) is not stored.
    id_type = models.CharField(
        max_length=30, blank=True, default="",
        choices=[(v, v) for v in ("Aadhaar", "PAN", "Voter ID", "Passport", "Driving licence", "ABHA", "Other")],
    )
    id_last4 = models.CharField(max_length=4, blank=True, default="")
    payer_type = models.CharField(
        max_length=30, blank=True, default="",
        choices=[(v, v) for v in ("Self", "Insurance", "Government scheme", "Corporate")],
    )
    payer_name = models.CharField(max_length=120, blank=True, default="")
    policy_number = models.CharField(max_length=60, blank=True, default="")
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