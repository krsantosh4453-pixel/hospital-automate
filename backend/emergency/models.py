from django.db import models


class EmergencyVisit(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="emergency_visits"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="emergency_visits"
    )
    visit_number = models.CharField(max_length=50, unique=True)
    triage_level = models.CharField(max_length=30, default="Normal")
    status = models.CharField(max_length=30, default="Waiting")
    arrival_time = models.DateTimeField(auto_now_add=True)
    discharge_time = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return self.visit_number
