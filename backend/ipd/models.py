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
        related_name="admissions"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="admissions"
    )
    admission_date = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Admitted")
    reason = models.TextField(blank=True)
    admitting_doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admissions"
    )

    def __str__(self):
        return f"{self.patient.name} - {self.status}"

    class Meta:
        ordering = ["-admission_date"]


class BedAllocation(models.Model):
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name="bed_allocations"
    )
    bed = models.ForeignKey(
        "hospital.Bed",
        on_delete=models.CASCADE,
        related_name="allocations"
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.admission.patient.name} - {self.bed}"

    class Meta:
        ordering = ["-allocated_at"]


class DischargePlan(models.Model):
    admission = models.OneToOneField(
        Admission,
        on_delete=models.CASCADE,
        related_name="discharge_plan"
    )
    instructions = models.TextField(blank=True)
    pending_tasks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discharge_plans"
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
        related_name="discharge_summaries"
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
        related_name="discharge_notes"
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
