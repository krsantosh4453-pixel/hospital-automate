from django.db import models


class LabTest(models.Model):
    name = models.CharField(max_length=150)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="lab_tests"
    )
    result = models.TextField(blank=True)
    status = models.CharField(max_length=20, default="Pending")
    test_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.patient.name}"

    class Meta:
        ordering = ["-test_date"]