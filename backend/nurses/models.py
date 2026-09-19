from django.db import models


class Nurse(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]
