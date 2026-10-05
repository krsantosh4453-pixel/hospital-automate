from django.db import models


class BloodInventory(models.Model):
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="blood_inventory"
    )
    blood_group = models.CharField(max_length=5)
    component = models.CharField(max_length=50)
    units = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.hospital.name} - {self.blood_group} - {self.component}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "blood_group", "component"],
                name="unique_hospital_blood_component"
            )
        ]
        ordering = ["blood_group", "component"]


class BloodRequest(models.Model):
    STATUS_CHOICES = [
        ("Requested", "Requested"),
        ("Approved", "Approved"),
        ("Issued", "Issued"),
        ("Rejected", "Rejected"),
        ("Cancelled", "Cancelled"),
    ]

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="blood_requests"
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="blood_requests"
    )
    blood_group = models.CharField(max_length=5)
    component = models.CharField(max_length=50)
    units = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Requested")
    requested_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blood_requests"
    )
    approved_by = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_blood_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.name} - {self.blood_group} {self.component} x{self.units}"

    class Meta:
        ordering = ["-created_at"]


class BloodTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("Receive", "Receive"),
        ("Issue", "Issue"),
        ("Return", "Return"),
        ("Expiry", "Expiry"),
        ("Adjustment", "Adjustment"),
    ]

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="blood_transactions"
    )
    request = models.ForeignKey(
        BloodRequest,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    inventory = models.ForeignKey(
        BloodInventory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    units = models.PositiveIntegerField()
    performed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blood_transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.units} units - {self.request}"

    class Meta:
        ordering = ["-created_at"]