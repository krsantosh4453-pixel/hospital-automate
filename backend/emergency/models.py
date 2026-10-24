from django.db import models
from django.utils import timezone


class EmergencyVisit(models.Model):
    TRIAGE_LEVELS = [
        ("Critical", "Critical - Immediate"),
        ("Emergency", "Emergency - < 15 min"),
        ("Urgent", "Urgent - < 30 min"),
        ("Semi-Urgent", "Semi-Urgent - < 60 min"),
        ("Non-Urgent", "Non-Urgent - < 120 min"),
    ]

    STATUS_CHOICES = [
        ("Registered", "Registered"),
        ("Triage", "Triage"),
        ("Waiting", "Waiting"),
        ("Under Consultation", "Under Consultation"),
        ("Investigations", "Investigations"),
        ("Treatment", "Treatment"),
        ("Observation", "Observation"),
        ("Admitted", "Admitted"),
        ("Discharged", "Discharged"),
        ("Referred", "Referred"),
        ("Left Against Advice", "Left Against Advice"),
        ("Expired", "Expired"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="emergency_visits",
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="emergency_visits",
        db_index=True
    )
    visit_number = models.CharField(max_length=50, unique=True, db_index=True)
    triage_level = models.CharField(max_length=30, choices=TRIAGE_LEVELS, default="Non-Urgent", db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Registered", db_index=True)
    arrival_time = models.DateTimeField(auto_now_add=True, db_index=True)
    triage_time = models.DateTimeField(null=True, blank=True)
    consultation_start_time = models.DateTimeField(null=True, blank=True)
    discharge_time = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    attending_doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_visits",
        db_index=True
    )
    disposition = models.CharField(max_length=30, blank=True)
    discharge_diagnosis = models.TextField(blank=True)
    follow_up_instructions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.visit_number} - {self.patient.name}"

    class Meta:
        ordering = ["-arrival_time"]
        indexes = [
            models.Index(fields=["hospital", "arrival_time"]),
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["patient", "arrival_time"]),
            models.Index(fields=["attending_doctor", "arrival_time"]),
            models.Index(fields=["hospital", "triage_level", "status"]),
        ]


class EmergencyTriage(models.Model):
    visit = models.OneToOneField(
        EmergencyVisit,
        on_delete=models.CASCADE,
        related_name="triage"
    )
    chief_complaint = models.TextField()
    vitals = models.JSONField(default=dict, blank=True)
    pain_score = models.PositiveIntegerField(null=True, blank=True)
    glasgow_coma_scale = models.PositiveIntegerField(null=True, blank=True)
    triage_notes = models.TextField(blank=True)
    triaged_by = models.ForeignKey(
        "nurses.Nurse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triage_records"
    )
    triaged_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Triage for {self.visit}"


class EmergencyVitals(models.Model):
    visit = models.ForeignKey(
        EmergencyVisit,
        on_delete=models.CASCADE,
        related_name="vitals_records",
        db_index=True
    )
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    systolic_bp = models.PositiveIntegerField(null=True, blank=True)
    diastolic_bp = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    spo2 = models.PositiveIntegerField(null=True, blank=True)
    blood_sugar = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    recorded_by = models.ForeignKey(
        "nurses.Nurse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="er_vitals"
    )
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Vitals for {self.visit} at {self.recorded_at}"

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["visit", "recorded_at"]),
        ]


class EmergencyOrder(models.Model):
    ORDER_TYPES = [
        ("Lab", "Lab Investigation"),
        ("Imaging", "Imaging"),
        ("Medication", "Medication"),
        ("Procedure", "Procedure"),
        ("Consultation", "Specialist Consultation"),
    ]

    STATUS_CHOICES = [
        ("Ordered", "Ordered"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    visit = models.ForeignKey(
        EmergencyVisit,
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True
    )
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, db_index=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Ordered", db_index=True)
    ordered_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="er_orders"
    )
    ordered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.TextField(blank=True)

    def __str__(self):
        return f"{self.order_type} Order for {self.visit}"

    class Meta:
        ordering = ["-ordered_at"]
        indexes = [
            models.Index(fields=["visit", "status"]),
            models.Index(fields=["visit", "order_type"]),
            models.Index(fields=["ordered_by", "ordered_at"]),
        ]


class EmergencyMedication(models.Model):
    visit = models.ForeignKey(
        EmergencyVisit,
        on_delete=models.CASCADE,
        related_name="medications",
        db_index=True
    )
    name = models.CharField(max_length=200)
    dose = models.CharField(max_length=100)
    route = models.CharField(max_length=50)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100, blank=True)
    prescribed_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="er_prescriptions"
    )
    prescribed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    administered = models.BooleanField(default=False)
    administered_by = models.ForeignKey(
        "nurses.Nurse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="er_med_admin"
    )
    administered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} for {self.visit}"

    class Meta:
        ordering = ["-prescribed_at"]
        indexes = [
            models.Index(fields=["visit", "prescribed_at"]),
            models.Index(fields=["prescribed_by", "prescribed_at"]),
        ]
