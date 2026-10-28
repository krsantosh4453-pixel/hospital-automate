from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class VitalSign(models.Model):
    class Avpu(models.TextChoices):
        ALERT = "A", "Alert"
        VOICE = "V", "Responds to voice"
        PAIN = "P", "Responds to pain"
        UNRESPONSIVE = "U", "Unresponsive"

    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="vitals",
        db_index=True
    )
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    systolic_bp = models.PositiveIntegerField(null=True, blank=True)
    diastolic_bp = models.PositiveIntegerField(null=True, blank=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    blood_sugar = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    spo2 = models.PositiveIntegerField(null=True, blank=True)
    # Extended set (requirement D2).
    pain_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(10)], help_text="0 (none) to 10 (worst)"
    )
    gcs = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(3), MaxValueValidator(15)],
        help_text="Glasgow Coma Scale total, 3 to 15",
    )
    avpu = models.CharField(max_length=1, choices=Avpu.choices, blank=True)
    head_circumference = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="cm")
    muac = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Mid-upper arm circumference, cm")
    urine_output = models.PositiveIntegerField(null=True, blank=True, help_text="mL since the last reading")
    comments = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["visit", "recorded_at"]),
        ]


class Allergy(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="allergies",
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allergies",
        db_index=True,
    )
    name = models.CharField(max_length=150)
    reaction = models.TextField(blank=True)
    severity = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ClinicalNote(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="clinical_notes",
        db_index=True
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["visit", "created_at"]),
            models.Index(fields=["doctor", "created_at"]),
        ]


class Diagnosis(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="diagnoses",
        db_index=True
    )
    name = models.CharField(max_length=200)
    icd10_code = models.CharField(max_length=30, blank=True)
    diagnosis_type = models.CharField(max_length=50, default="Provisional")
    remarks = models.TextField(blank=True)
    # Clinician accountable for the entry (set by the API from the signed-in user).
    recorded_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["visit", "created_at"]),
        ]


class ServiceOrder(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="service_orders",
        db_index=True
    )
    service_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, default="Pending", db_index=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["visit", "status"]),
        ]


class Procedure(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="procedures",
        db_index=True
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, default="Planned", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["visit", "status"]),
        ]


class MedicalRecord(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="medical_records",
        db_index=True
    )
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="medical_records",
        null=True,
        blank=True,
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_records",
        db_index=True,
    )
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["visit", "created_at"]),
        ]


class Prescription(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="prescriptions",
        db_index=True
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="prescriptions",
        db_index=True
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
        db_index=True
    )
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions",
        db_index=True
    )
    status = models.CharField(max_length=30, default="Confirmed", db_index=True)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "created_at"]),
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["doctor", "created_at"]),
            models.Index(fields=["hospital", "status"]),
        ]

    def __str__(self):
        return f"RX-{self.pk}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True
    )
    name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    instructions = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["prescription"]),
        ]

    def __str__(self):
        return f"{self.name} x{self.quantity}"

class MedicalCertificate(models.Model):
    """A signed medical certificate (requirement D10). Never edited once issued."""

    class Kind(models.TextChoices):
        SICK_LEAVE = "Sick leave", "Sick leave"
        FITNESS = "Fitness", "Fitness"
        OTHER = "Other", "Other"

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="medical_certificates",
        db_index=True
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="medical_certificates",
        db_index=True
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        related_name="medical_certificates",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SICK_LEAVE)
    diagnosis = models.CharField(max_length=255, blank=True)
    remarks = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["hospital", "issued_at"]),
            models.Index(fields=["patient", "issued_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")),
                name="certificate_end_not_before_start",
            ),
        ]

    def __str__(self):
        return f"CERT-{self.pk}"


class Referral(models.Model):
    """A doctor's referral to a colleague or an outside facility (requirement D11)."""

    class Urgency(models.TextChoices):
        ROUTINE = "Routine", "Routine"
        URGENT = "Urgent", "Urgent"
        EMERGENCY = "Emergency", "Emergency"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        ACCEPTED = "Accepted", "Accepted"
        DECLINED = "Declined", "Declined"
        COMPLETED = "Completed", "Completed"

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="referrals",
        db_index=True
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="referrals",
        db_index=True
    )
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    referring_doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.PROTECT,
        related_name="referrals_made",
    )
    # Either a doctor of the same hospital or a named outside doctor/facility.
    referred_to_doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals_received",
    )
    referred_to_external = models.CharField(max_length=200, blank=True)
    specialty = models.CharField(max_length=100, blank=True)
    reason = models.TextField()
    urgency = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.ROUTINE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["patient", "created_at"]),
        ]

    def __str__(self):
        return f"REF-{self.pk}"


class Immunization(models.Model):
    """A vaccine dose given to a patient (requirement D15)."""

    class Route(models.TextChoices):
        IM = "IM", "Intramuscular"
        SC = "SC", "Subcutaneous"
        ID = "ID", "Intradermal"
        ORAL = "Oral", "Oral"
        NASAL = "Nasal", "Intranasal"

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="immunizations",
        db_index=True
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="immunizations",
        db_index=True
    )
    vaccine = models.CharField(max_length=150)
    dose_number = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    administered_on = models.DateField()
    batch_number = models.CharField(max_length=60, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    route = models.CharField(max_length=10, choices=Route.choices, blank=True)
    site = models.CharField(max_length=60, blank=True)
    next_due_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="immunizations_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-administered_on", "-created_at"]
        indexes = [
            models.Index(fields=["patient", "administered_on"]),
            models.Index(fields=["hospital", "next_due_on"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(next_due_on__isnull=True) | models.Q(next_due_on__gt=models.F("administered_on")),
                name="immunization_next_due_after_given",
            ),
        ]

    def __str__(self):
        return f"{self.vaccine} dose {self.dose_number}"
