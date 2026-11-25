from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class LabTest(models.Model):
    PRIORITY_CHOICES = [
        ("Normal", "Normal"),
        ("Urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("Ordered", "Ordered"),
        ("Sample Pending", "Sample Pending"),
        ("Collected", "Collected"),
        ("Dispatched", "Dispatched"),
        ("Received", "Received"),
        ("Processing", "Processing"),
        ("Result Entered", "Result Entered"),
        ("Verified", "Verified"),
        ("Released", "Released"),
        ("Cancelled", "Cancelled"),
    ]
    # A result is done once verified; until then the test is still pending.
    DONE_STATUSES = ("Verified", "Released")
    CLOSED_STATUSES = DONE_STATUSES + ("Cancelled",)

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="lab_tests",
        null=True,
        blank=True,
        db_index=True
    )
    name = models.CharField(max_length=150, db_index=True)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="lab_tests",
        db_index=True
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_tests",
        db_index=True
    )
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_tests",
        db_index=True
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Normal", db_index=True)
    result = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Ordered", db_index=True)
    test_date = models.DateField(auto_now_add=True, db_index=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.patient.name}"

    class Meta:
        ordering = ["-test_date"]
        indexes = [
            models.Index(fields=["hospital", "test_date"]),
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["patient", "test_date"]),
            models.Index(fields=["hospital", "priority", "status"]),
            models.Index(fields=["doctor", "test_date"]),
            models.Index(fields=["visit", "test_date"]),
        ]


class SampleCollection(models.Model):
    SAMPLE_TYPES = [
        ("Blood", "Blood"),
        ("Urine", "Urine"),
        ("Stool", "Stool"),
        ("Sputum", "Sputum"),
        ("Swab", "Swab"),
        ("Tissue", "Tissue"),
        ("Fluid", "Fluid"),
        ("Other", "Other"),
    ]

    CONTAINER_TYPES = [
        ("EDTA", "EDTA Tube"),
        ("Plain", "Plain Tube"),
        ("Heparin", "Heparin Tube"),
        ("Citrate", "Citrate Tube"),
        ("Fluoride", "Fluoride Tube"),
        ("Urine Container", "Urine Container"),
        ("Stool Container", "Stool Container"),
        ("Swab Tube", "Swab Tube"),
        ("Other", "Other"),
    ]

    lab_test = models.OneToOneField(
        LabTest,
        on_delete=models.CASCADE,
        related_name="sample_collection"
    )
    sample_type = models.CharField(max_length=20, choices=SAMPLE_TYPES)
    container_type = models.CharField(max_length=20, choices=CONTAINER_TYPES)
    sample_id = models.CharField(max_length=50, unique=True)
    collected_by = models.ForeignKey(
        "nurses.Nurse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sample_collections"
    )
    collected_at = models.DateTimeField(auto_now_add=True)
    collection_notes = models.TextField(blank=True)
    barcoded = models.BooleanField(default=False)

    def __str__(self):
        return f"Sample {self.sample_id} for {self.lab_test}"

    class Meta:
        ordering = ["-collected_at"]


class SampleDispatch(models.Model):
    DISPATCH_STATUS = [
        ("Pending", "Pending Dispatch"),
        ("Dispatched", "Dispatched"),
        ("In Transit", "In Transit"),
        ("Delivered", "Delivered"),
        ("Rejected", "Rejected"),
    ]

    lab_test = models.OneToOneField(
        LabTest,
        on_delete=models.CASCADE,
        related_name="sample_dispatch"
    )
    dispatched_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sample_dispatches"
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sample_receipts"
    )
    received_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=DISPATCH_STATUS, default="Pending")
    dispatch_notes = models.TextField(blank=True)
    external_lab = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Dispatch for {self.lab_test} - {self.status}"

    class Meta:
        ordering = ["-dispatched_at"]


class LabResult(models.Model):
    lab_test = models.OneToOneField(
        LabTest,
        on_delete=models.CASCADE,
        related_name="lab_result"
    )
    result_data = models.JSONField(default=dict, blank=True)
    result_text = models.TextField(blank=True)
    reference_ranges = models.JSONField(default=dict, blank=True)
    abnormal_flags = models.JSONField(default=list, blank=True)
    entered_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_results_entered"
    )
    entered_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_results_verified"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_released = models.BooleanField(default=False)

    # H-14: computed by the server from the hospital's reference ranges when
    # the result is entered (laboratory/flags.py), never typed by the client.
    # One entry per checked parameter: value, range, flag (L/H/LL/HH or "")
    # and whether it could be checked at all.
    flag_details = models.JSONField(default=list, blank=True)
    has_critical = models.BooleanField(default=False, db_index=True)
    critical_acknowledged_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_criticals_acknowledged",
    )
    critical_acknowledged_at = models.DateTimeField(null=True, blank=True)
    critical_acknowledgement_note = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Result for {self.lab_test}"

    class Meta:
        ordering = ["-entered_at"]


class LabResultRejection(models.Model):
    """
    L-1: a result sent back before release because it was wrong. The values
    as entered are kept here (the result row itself is removed so the test
    can be entered again); who entered, who rejected, when and why.
    """

    lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name="rejections")
    result_data = models.JSONField(default=dict, blank=True)
    result_text = models.TextField(blank=True)
    reference_ranges = models.JSONField(default=dict, blank=True)
    abnormal_flags = models.JSONField(default=list, blank=True)
    flag_details = models.JSONField(default=list, blank=True)
    entered_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    entered_at = models.DateTimeField(null=True, blank=True)
    was_verified = models.BooleanField(default=False)
    rejected_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    rejected_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()

    class Meta:
        ordering = ["-rejected_at"]

    def __str__(self):
        return f"Rejected result for {self.lab_test}"


class LabReferenceRange(models.Model):
    """
    H-14: a hospital's reference and critical limits for one parameter of a
    test, set by its laboratory (values are the lab director's decision; none
    ship with the app). Results are flagged against these when entered, and
    the limits in force are copied onto the result, so a later change never
    alters a released report.
    """

    SEX_ANY = ""
    SEX_CHOICES = [(SEX_ANY, "Any"), ("Male", "Male"), ("Female", "Female")]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.CASCADE,
                                 related_name="lab_reference_ranges")
    # Matched without regard to case against LabTest.name and the keys of
    # LabResult.result_data.
    test_name = models.CharField(max_length=150)
    parameter = models.CharField(max_length=80)
    unit = models.CharField(max_length=30, blank=True, default="")
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True, default=SEX_ANY)
    low = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    high = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    critical_low = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    critical_high = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["test_name", "parameter", "sex"]
        constraints = [
            models.UniqueConstraint(
                models.F("hospital"),
                Lower("test_name"),
                Lower("parameter"),
                models.F("sex"),
                condition=models.Q(is_active=True),
                name="unique_active_lab_reference_range",
            ),
        ]
        indexes = [models.Index(fields=["hospital", "test_name"])]

    def __str__(self):
        return f"{self.test_name} / {self.parameter}"


class ResultVerification(models.Model):
    lab_result = models.OneToOneField(
        LabResult,
        on_delete=models.CASCADE,
        related_name="verification"
    )
    verified_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="result_verifications"
    )
    verified_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    action = models.CharField(
        max_length=20,
        choices=[
            ("Verified", "Verified"),
            ("Rejected", "Rejected"),
            ("Corrected", "Corrected"),
        ]
    )

    # BUG-06: verified by the user who entered the result, allowed only by the
    # hospital's LabVerificationPolicy and audited as "lab.result.self_verified".
    self_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Verification for {self.lab_result}"

    class Meta:
        ordering = ["-verified_at"]


class LabVerificationPolicy(models.Model):
    """
    BUG-06: a hospital's exception to maker-checker on laboratory results.

    By default a result is verified by a different user from the one who
    entered it. A hospital that runs with one technician on a shift may let
    the same user verify; each such verification is then marked
    ``self_verified`` and audited. Only an Admin sets this, with a reason.
    """

    hospital = models.OneToOneField("hospital.Hospital", on_delete=models.CASCADE,
                                    related_name="lab_verification_policy")
    allow_self_verification = models.BooleanField(default=False)
    reason = models.TextField(blank=True, default="")
    updated_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        allowed = "allowed" if self.allow_self_verification else "not allowed"
        return f"Self-verification {allowed} at {self.hospital_id}"

class ImagingStudy(models.Model):
    """
    A radiology / imaging order and its report (requirement G4).
    Ordered by a doctor, scheduled and performed by the technician (Lab Staff),
    reported and signed by a doctor. A signed report is never edited.
    """

    class Modality(models.TextChoices):
        XRAY = "X-ray", "X-ray"
        ULTRASOUND = "Ultrasound", "Ultrasound"
        CT = "CT", "CT"
        MRI = "MRI", "MRI"
        MAMMOGRAPHY = "Mammography", "Mammography"
        FLUOROSCOPY = "Fluoroscopy", "Fluoroscopy"
        ECG = "ECG", "ECG"
        ECHO = "Echo", "Echo"
        OTHER = "Other", "Other"

    class Status(models.TextChoices):
        ORDERED = "Ordered", "Ordered"
        SCHEDULED = "Scheduled", "Scheduled"
        PERFORMED = "Performed", "Performed"
        REPORTED = "Reported", "Reported"
        CANCELLED = "Cancelled", "Cancelled"

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.CASCADE, related_name="imaging_studies")
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="imaging_studies")
    visit = models.ForeignKey("encounters.Visit", on_delete=models.SET_NULL, null=True, blank=True, related_name="imaging_studies")
    accession_number = models.CharField(max_length=40, unique=True)
    modality = models.CharField(max_length=20, choices=Modality.choices)
    body_part = models.CharField(max_length=120)
    indication = models.TextField(help_text="Clinical question for the radiologist.")
    priority = models.CharField(max_length=10, choices=[("Routine", "Routine"), ("Urgent", "Urgent"), ("STAT", "STAT")], default="Routine")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ORDERED, db_index=True)
    ordered_by = models.ForeignKey("doctors.Doctor", on_delete=models.PROTECT, related_name="imaging_ordered")
    ordered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    performed_at = models.DateTimeField(null=True, blank=True)
    performed_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    technician_notes = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    reported_by = models.ForeignKey("doctors.Doctor", on_delete=models.SET_NULL, null=True, blank=True, related_name="imaging_reported")
    reported_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-ordered_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["patient", "ordered_at"]),
        ]

    def __str__(self):
        return f"{self.accession_number} {self.modality} {self.body_part}"
