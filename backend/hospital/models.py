from django.db import models


class Hospital(models.Model):
    class Type(models.TextChoices):
        PRIVATE = "Private", "Private"
        GOVERNMENT = "Government", "Government"
        TRUST = "Trust", "Trust / Charitable"

    name = models.CharField(max_length=150, db_index=True)
    # Short registration code shown in admin lists; optional for older rows.
    code = models.CharField(max_length=30, unique=True, null=True, blank=True)
    # F1: start of every UHID issued here (DCH -> DCH-2026-000001). Blank
    # falls back to the code, then to "H<id>" (patients/uhid.py).
    # P1-03 (DPDP Act): who answers patients' data requests and complaints; shown in the privacy notice.
    grievance_officer_name = models.CharField(max_length=150, blank=True, default="")
    grievance_officer_email = models.EmailField(blank=True, default="")
    grievance_officer_phone = models.CharField(max_length=20, blank=True, default="")
    uhid_prefix = models.CharField(max_length=10, blank=True, default="")
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
        constraints = [
            # A UHID also signs a patient in, so two hospitals never share a prefix.
            models.UniqueConstraint(
                "uhid_prefix", condition=~models.Q(uhid_prefix=""), name="unique_hospital_uhid_prefix",
            ),
        ]


class Department(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="departments",
        db_index=True
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    # Head of department: a doctor of the same hospital (validated in the serializer).
    head = models.ForeignKey(
        "doctors.Doctor", on_delete=models.SET_NULL, null=True, blank=True, related_name="headed_departments"
    )
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

class RoleModuleRestriction(models.Model):
    """
    A hospital administrator's narrowing of a built-in role for one module:
    "view" (read only) or "none" (no access). It can only take access away;
    what a role may do at all is still defined in code. Admin cannot be
    restricted. Enforced for every hospital-scoped API (users/module_access.py).
    """

    VIEW, NONE = "view", "none"

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="role_restrictions")
    role = models.CharField(max_length=30)
    module = models.CharField(max_length=30)
    access = models.CharField(max_length=4, choices=[(VIEW, "View only"), (NONE, "No access")])
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["role", "module"]
        constraints = [models.UniqueConstraint(fields=["hospital", "role", "module"], name="one_restriction_per_role_module")]

    def __str__(self):
        return f"{self.role} / {self.module}: {self.access}"
