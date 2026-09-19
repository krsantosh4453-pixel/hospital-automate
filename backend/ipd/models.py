from django.db import models


class Admission(models.Model):
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
    status = models.CharField(max_length=30, default="Admitted")
    reason = models.TextField(blank=True)

    def __str__(self):
        return self.patient.name


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


class DischargePlan(models.Model):
    admission = models.OneToOneField(
        Admission,
        on_delete=models.CASCADE,
        related_name="discharge_plan"
    )
    instructions = models.TextField(blank=True)
    pending_tasks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


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
        blank=True
    )
    finalized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class DischargeNote(models.Model):
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name="discharge_notes"
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
