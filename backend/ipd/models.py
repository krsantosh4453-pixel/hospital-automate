from django.db import models


class Admission(models.Model):
    STATUS_CHOICES = [
        ("Admitted", "Admitted"),
        ("Discharge Initiated", "Discharge Initiated"),
        ("Discharged", "Discharged"),
        ("Transferred", "Transferred"),
        ("Cancelled", "Cancelled"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="admissions",
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="admissions",
        db_index=True
    )
    admission_date = models.DateTimeField(auto_now_add=True, db_index=True)
    discharge_date = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Admitted", db_index=True)
    reason = models.TextField(blank=True)
    admitting_doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admissions",
        db_index=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.status}"

    class Meta:
        ordering = ["-admission_date"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["patient", "admission_date"]),
            models.Index(fields=["hospital", "admission_date"]),
            models.Index(fields=["admitting_doctor", "admission_date"]),
        ]


class BedAllocation(models.Model):
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name="bed_allocations",
        db_index=True
    )
    bed = models.ForeignKey(
        "hospital.Bed",
        on_delete=models.CASCADE,
        related_name="allocations",
        db_index=True
    )
    allocated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    released_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.admission.patient.name} - {self.bed}"

    class Meta:
        ordering = ["-allocated_at"]
        indexes = [
            models.Index(fields=["admission", "is_active"]),
            models.Index(fields=["bed", "is_active"]),
        ]


class DischargePlan(models.Model):
    admission = models.OneToOneField(
        Admission,
        on_delete=models.CASCADE,
        related_name="discharge_plan"
    )
    instructions = models.TextField(blank=True)
    pending_tasks = models.TextField(blank=True)
    # Discharge checklist (requirement E7): every item must be ticked before
    # the discharge can be completed.
    medications_reconciled = models.BooleanField(default=False)
    patient_counselled = models.BooleanField(default=False)
    follow_up_arranged = models.BooleanField(default=False)
    documents_handed_over = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discharge_plans",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Discharge Plan for {self.admission.patient.name}"


class DischargeSummary(models.Model):
    admission = models.OneToOneField(
        Admission,
        on_delete=models.CASCADE,
        related_name="discharge_summary"
    )
    summary = models.TextField()
    authorized_doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discharge_summaries",
        db_index=True
    )
    finalized = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Discharge Summary for {self.admission.patient.name}"

    class Meta:
        ordering = ["-created_at"]


class DischargeNote(models.Model):
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name="discharge_notes",
        db_index=True
    )
    note = models.TextField()
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discharge_notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.admission.patient.name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["admission", "created_at"]),
        ]
