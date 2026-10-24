from django.db import models


class Hospital(models.Model):
    class Type(models.TextChoices):
        PRIVATE = "Private", "Private"
        GOVERNMENT = "Government", "Government"
        TRUST = "Trust", "Trust / Charitable"

    name = models.CharField(max_length=150, db_index=True)
    # Short registration code shown in admin lists; optional for older rows.
    code = models.CharField(max_length=30, unique=True, null=True, blank=True)
    hospital_type = models.CharField(max_length=20, choices=Type.choices, default=Type.PRIVATE)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]


class Department(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="departments",
        db_index=True
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.hospital.name} - {self.name}"

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["hospital", "is_active"]),
        ]


class Ward(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="wards",
        db_index=True
    )
    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["hospital", "name"]),
        ]


class Room(models.Model):
    ward = models.ForeignKey(
        Ward,
        on_delete=models.CASCADE,
        related_name="rooms",
        db_index=True
    )
    room_number = models.CharField(max_length=50)
    name = models.CharField(max_length=50, blank=True)
    room_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.room_number

    class Meta:
        ordering = ["room_number"]
        indexes = [
            models.Index(fields=["ward", "room_number"]),
        ]


class Bed(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="beds",
        db_index=True
    )
    bed_number = models.CharField(max_length=50)
    bed_type = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=30,
        default="Available",
        db_index=True
    )

    def __str__(self):
        return f"{self.room.room_number} - {self.bed_number}"

    class Meta:
        ordering = ["bed_number"]
        indexes = [
            models.Index(fields=["room", "status"]),
        ]