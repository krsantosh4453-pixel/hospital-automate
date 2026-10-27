from django.db import models
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

    def __str__(self):
        return f"Result for {self.lab_test}"

    class Meta:
        ordering = ["-entered_at"]


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

    def __str__(self):
        return f"Verification for {self.lab_result}"

    class Meta:
        ordering = ["-verified_at"]