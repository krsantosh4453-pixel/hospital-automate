from django.conf import settings
from django.db import models
from django.utils import timezone

# Duty shifts used by ward assignments. A Night shift runs past midnight.
SHIFTS = ("Morning", "Evening", "Night")
NIGHT_SHIFT = "Night"


class Nurse(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="nurses",
        null=True,
        blank=True,
        db_index=True
    )
    # The staff login of this nurse; a Nurse sees only the patients of
    # their own duty, which needs this link. Null for unlinked profiles.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nurse_profiles",
    )
    name = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=100, blank=True, db_index=True)
    shift = models.CharField(max_length=20, blank=True, db_index=True)
    qualification = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default="Active", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["hospital", "department"]),
            models.Index(fields=["hospital", "shift"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "hospital"],
                condition=models.Q(user__isnull=False),
                name="nurse_unique_user_per_hospital",
            ),
        ]


class NurseWardAssignment(models.Model):
    """A nurse on duty in a ward for one shift of one day."""
    nurse = models.ForeignKey(Nurse, on_delete=models.CASCADE, related_name="ward_assignments")
    ward = models.ForeignKey("hospital.Ward", on_delete=models.CASCADE, related_name="nurse_assignments")
    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.CASCADE, related_name="nurse_ward_assignments")
    shift = models.CharField(max_length=20, choices=[(s, s) for s in SHIFTS])
    shift_date = models.DateField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nurse.name} - {self.ward.name} ({self.shift} {self.shift_date})"

    class Meta:
        ordering = ["-shift_date", "shift"]
        constraints = [
            models.UniqueConstraint(
                fields=["nurse", "ward", "shift", "shift_date"], name="nurse_ward_shift_once",
            ),
        ]
        indexes = [models.Index(fields=["hospital", "shift_date", "is_active"])]


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
        related_name="nursing_assessments",
        db_index=True
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="nursing_assessments",
        null=True,
        blank=True,
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="nursing_assessments",
        db_index=True
    )
    nurse = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
        db_index=True
    )
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES, default="Shift", db_index=True)
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
    assessed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.assessment_type} Assessment for {self.patient.name}"

    class Meta:
        ordering = ["-assessed_at"]
        indexes = [
            models.Index(fields=["hospital", "assessed_at"]),
            models.Index(fields=["patient", "assessed_at"]),
            models.Index(fields=["admission", "assessed_at"]),
            models.Index(fields=["nurse", "assessed_at"]),
        ]


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
        related_name="nursing_notes",
        db_index=True
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="nursing_notes",
        null=True,
        blank=True,
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="nursing_notes",
        db_index=True
    )
    nurse = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nursing_notes",
        db_index=True
    )
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default="Progress", db_index=True)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.note_type} Note for {self.patient.name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "created_at"]),
            models.Index(fields=["patient", "created_at"]),
            models.Index(fields=["admission", "created_at"]),
            models.Index(fields=["nurse", "created_at"]),
        ]


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
        related_name="care_tasks",
        db_index=True
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="care_tasks",
        null=True,
        blank=True,
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="care_tasks",
        db_index=True
    )
    assigned_nurse = models.ForeignKey(
        Nurse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        db_index=True
    )
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, db_index=True)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Routine", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending", db_index=True)
    scheduled_at = models.DateTimeField(db_index=True)
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
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.task_type} for {self.patient.name} - {self.status}"

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["hospital", "scheduled_at"]),
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["patient", "scheduled_at"]),
            models.Index(fields=["assigned_nurse", "scheduled_at"]),
            models.Index(fields=["admission", "scheduled_at"]),
            models.Index(fields=["status", "priority", "scheduled_at"]),
        ]


class MAR(models.Model):
    """Medication Administration Record - links prescription to administration schedule."""
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="mar_records",
        db_index=True
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="mar_records",
        null=True,
        blank=True,
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="mar_records",
        db_index=True
    )
    prescription = models.ForeignKey(
        "clinical.Prescription",
        on_delete=models.CASCADE,
        related_name="mar_records",
        db_index=True
    )
    prescription_item = models.ForeignKey(
        "clinical.PrescriptionItem",
        on_delete=models.CASCADE,
        related_name="mar_records",
        db_index=True
    )
    medicine_name = models.CharField(max_length=200, db_index=True)
    dose = models.CharField(max_length=100)
    route = models.CharField(max_length=50)
    frequency = models.CharField(max_length=100)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"MAR: {self.medicine_name} for {self.patient.name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "is_active"]),
            models.Index(fields=["patient", "is_active"]),
            models.Index(fields=["admission", "is_active"]),
            models.Index(fields=["prescription", "is_active"]),
        ]


class MARAdministration(models.Model):
    """
    One scheduled (or PRN) dose. A dose starts as Scheduled and is only marked
    Administered / Held / Refused / Missed / Vomited / Excluded by a nurse
    action, which records who and when. "Delay" is a Scheduled dose more than
    30 minutes past its time (computed, not stored).
    """
    SCHEDULED = "Scheduled"
    ADMINISTERED = "Administered"
    STATUS_CHOICES = [
        ("Scheduled", "Scheduled (due)"),
        ("Administered", "Administered"),
        ("Held", "Held"),
        ("Refused", "Refused"),
        ("Missed", "Missed"),
        ("Vomited", "Vomited"),
        ("Excluded", "Administration Excluded"),
    ]

    mar = models.ForeignKey(
        MAR,
        on_delete=models.CASCADE,
        related_name="administrations",
        db_index=True
    )
    scheduled_time = models.DateTimeField(db_index=True)
    administered_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SCHEDULED, db_index=True)
    is_prn = models.BooleanField(default=False)
    # Login that recorded the outcome (Nurse rows are not linked to logins).
    recorded_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
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
        indexes = [
            models.Index(fields=["mar", "scheduled_time"]),
            models.Index(fields=["mar", "status"]),
            models.Index(fields=["administered_by", "scheduled_time"]),
        ]


class PatientAssignment(models.Model):
    """Nurse-patient assignment for a shift."""
    nurse = models.ForeignKey(
        Nurse,
        on_delete=models.CASCADE,
        related_name="patient_assignments",
        db_index=True
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="nurse_assignments",
        db_index=True
    )
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.CASCADE,
        related_name="nurse_assignments",
        null=True,
        blank=True,
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="patient_assignments",
        db_index=True
    )
    shift = models.CharField(max_length=20, db_index=True)
    shift_date = models.DateField(db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.nurse.name} - {self.patient.name} ({self.shift} {self.shift_date})"

    class Meta:
        unique_together = ("nurse", "patient", "shift", "shift_date")
        ordering = ["-shift_date", "shift"]
        indexes = [
            models.Index(fields=["hospital", "shift_date", "shift"]),
            models.Index(fields=["nurse", "shift_date", "is_active"]),
            models.Index(fields=["patient", "shift_date", "is_active"]),
        ]
