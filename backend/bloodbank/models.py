from django.db import models


class BloodInventory(models.Model):
    blood_group = models.CharField(max_length=5)
    component = models.CharField(max_length=50)
    units = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.blood_group} - {self.component}"


class BloodRequest(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="blood_requests"
    )
    blood_group = models.CharField(max_length=5)
    component = models.CharField(max_length=50)
    units = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, default="Requested")
    created_at = models.DateTimeField(auto_now_add=True)


class BloodTransaction(models.Model):
    request = models.ForeignKey(
        BloodRequest,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transaction_type = models.CharField(max_length=30)
    units = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)