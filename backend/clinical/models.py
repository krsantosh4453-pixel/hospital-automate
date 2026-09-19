from django.db import models


class VitalSign(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="vitals"
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
    comments = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)


class Allergy(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="allergies"
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
        related_name="clinical_notes"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Diagnosis(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="diagnoses"
    )
    name = models.CharField(max_length=200)
    icd10_code = models.CharField(max_length=30, blank=True)
    diagnosis_type = models.CharField(max_length=50, default="Provisional")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ServiceOrder(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="service_orders"
    )
    service_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, default="Pending")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Procedure(models.Model):
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="procedures"
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=30, default="Planned")
    created_at = models.DateTimeField(auto_now_add=True)


class MedicalRecord(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="medical_records"
    )
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.CASCADE,
        related_name="medical_records",
        null=True,
        blank=True
    )
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Prescription(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="prescriptions"
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="prescriptions"
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions"
    )
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions"
    )
    status = models.CharField(max_length=30, default="Confirmed")
    dispensed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"RX-{self.pk}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="items"
    )
    name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    instructions = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} x{self.quantity}"