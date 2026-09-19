from django.db import models


class Hospital(models.Model):
    name = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]


class Department(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="departments"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.hospital.name} - {self.name}"

    class Meta:
        ordering = ["name"]


class Ward(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="wards"
    )
    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Room(models.Model):
    ward = models.ForeignKey(
        Ward,
        on_delete=models.CASCADE,
        related_name="rooms"
    )
    room_number = models.CharField(max_length=50)
    room_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.room_number

    class Meta:
        ordering = ["room_number"]


class Bed(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="beds"
    )
    bed_number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=30,
        default="Available"
    )

    def __str__(self):
        return f"{self.room.room_number} - {self.bed_number}"

    class Meta:
        ordering = ["bed_number"]