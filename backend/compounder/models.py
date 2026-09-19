from django.db import models


class Compounder(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, default="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]