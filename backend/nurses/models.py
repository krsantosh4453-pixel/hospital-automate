from django.db import models
from django.utils import timezone


class Nurse(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="nurses",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=100, blank=True)
    shift = models.CharField(max_length=20, blank=True)
    qualification = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]


class NursingAssessment(models.Model):
    ASSESSMENT_TYPES = [
        ("Initial", "Initial Assessment"),
        ("Shift", "Shift Assessment"),
        ("Focused", "Focused Assessment"),
        ("Discharge", "Discharge Assessment"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="nursing_assessments"
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="nursing_assessments",
        null=True,
        blank=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="nursing_assessments"
    )
    nurse = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments"
    )
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES, default="Shift")
    vitals = models.JSONField(default=dict, blank=True)
    pain_score = models.PositiveIntegerField(null=True, blank=True)
    level_of_consciousness = models.CharField(max_length=50, blank=True)
    skin_condition = models.TextField(blank=True)
    respiratory_assessment = models.TextField(blank=True)
    cardiovascular_assessment = models.TextField(blank=True)
    gastrointestinal_assessment = models.TextField(blank=True)
    neurological_assessment = models.TextField(blank=True)
    mobility_status = models.CharField(max_length=50, blank=True)
    nutritional_status = models.CharField(max_length=50, blank=True)
    elimination_status = models.TextField(blank=True)
    psychosocial_assessment = models.TextField(blank=True)
    plan_of_care = models.TextField(blank=True)
    assessed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.assessment_type} Assessment for {self.patient.name}"

    class Meta:
        ordering = ["-assessed_at"]


class NursingNote(models.Model):
    NOTE_TYPES = [
        ("Progress", "Progress Note"),
        ("Incident", "Incident Report"),
        ("Communication", "Communication"),
        ("Education", "Patient Education"),
        ("Handoff", "Shift Handoff"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="nursing_notes"
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="nursing_notes",
        null=True,
        blank=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="nursing_notes"
    )
    nurse = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nursing_notes"
    )
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default="Progress")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.note_type} Note for {self.patient.name}"

    class Meta:
        ordering = ["-created_at"]


class CareTask(models.Model):
    TASK_TYPES = [
        ("Vitals", "Vitals Monitoring"),
        ("Medication", "Medication Administration"),
        ("Wound Care", "Wound Care"),
        ("Hygiene", "Hygiene Care"),
        ("Mobility", "Mobility/Positioning"),
        ("Specimen", "Specimen Collection"),
        ("Tube Care", "Tube/Line Care"),
        ("Monitoring", "Continuous Monitoring"),
        ("Other", "Other"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
        ("Deferred", "Deferred"),
        ("Cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("Routine", "Routine"),
        ("Urgent", "Urgent"),
        ("Stat", "STAT"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="care_tasks"
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="care_tasks",
        null=True,
        blank=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="care_tasks"
    )
    assigned_nurse = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Routine")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_tasks"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task_type} for {self.patient.name} - {self.status}"

    class Meta:
        ordering = ["scheduled_at"]


class MAR(models.Model):
    """Medication Administration Record - links prescription to administration schedule."""
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="mar_records"
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="mar_records",
        null=True,
        blank=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="mar_records"
    )
    prescription = models.ForeignKey(
        "clinical.Prescription",
        on_delete=models.CASCADE,
        related_name="mar_records"
    )
    prescription_item = models.ForeignKey(
        "clinical.PrescriptionItem",
        on_delete=models.CASCADE,
        related_name="mar_records"
    )
    medicine_name = models.CharField(max_length=200)
    dose = models.CharField(max_length=100)
    route = models.CharField(max_length=50)
    frequency = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MAR: {self.medicine_name} for {self.patient.name}"

    class Meta:
        ordering = ["-created_at"]


class MARAdministration(models.Model):
    """Individual medication administration event."""
    STATUS_CHOICES = [
        ("Administered", "Administered"),
        ("Held", "Held"),
        ("Refused", "Refused"),
        ("Missed", "Missed"),
        ("Vomited", "Vomited"),
    ]

    mar = models.ForeignKey(
        MAR,
        on_delete=models.CASCADE,
        related_name="administrations"
    )
    scheduled_time = models.DateTimeField()
    administered_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Administered")
    administered_by = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mar_administrations"
    )
    dose_given = models.CharField(max_length=100, blank=True)
    route_given = models.CharField(max_length=50, blank=True)
    site = models.CharField(max_length=100, blank=True)
    reason_held = models.TextField(blank=True)
    reason_refused = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mar.medicine_name} - {self.scheduled_time} - {self.status}"

    class Meta:
        ordering = ["scheduled_time"]


class PatientAssignment(models.Model):
    """Nurse-patient assignment for a shift."""
    nurse = models.ForeignKey(
        Nurse,
        on_delete=models.CASCADE,
        related_name="patient_assignments"
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="nurse_assignments"
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="nurse_assignments",
        null=True,
        blank=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="patient_assignments"
    )
    shift = models.CharField(max_length=20)
    shift_date = models.DateField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nurse.name} - {self.patient.name} ({self.shift} {self.shift_date})"

    class Meta:
        unique_together = ("nurse", "patient", "shift", "shift_date")
        ordering = ["-shift_date", "shift"]
