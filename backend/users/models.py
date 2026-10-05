from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


class StaffRole(models.TextChoices):
    ADMIN = "Admin", "Admin"
    DOCTOR = "Doctor", "Doctor"
    NURSE = "Nurse", "Nurse"
    COMPOUNDER = "Compounder", "Compounder"
    RECEPTIONIST = "Receptionist", "Receptionist"
    PHARMACIST = "Pharmacist", "Pharmacist"
    LAB_STAFF = "Lab Staff", "Lab Staff"
    BLOOD_BANK_STAFF = "Blood Bank Staff", "Blood Bank Staff"
    BILLING_STAFF = "Billing Staff", "Billing Staff"
    INVENTORY_STAFF = "Inventory Staff", "Inventory Staff"
    HOSPITAL_MANAGER = "Hospital Manager", "Hospital Manager"


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile"
    )
    role = models.CharField(
        max_length=30,
        choices=StaffRole.choices,
        default=StaffRole.RECEPTIONIST
    )
    phone = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=50, blank=True, unique=True)
    license_number = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    department_name = models.CharField(max_length=100, blank=True)
    years_experience = models.CharField(max_length=20, blank=True)
    is_active_staff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    class Meta:
        ordering = ["-created_at"]


class StaffHospitalMembership(models.Model):
    staff = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name="hospital_memberships"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="staff_memberships"
    )
    role = models.CharField(
        max_length=30,
        choices=StaffRole.choices,
        default=StaffRole.RECEPTIONIST
    )
    department = models.ForeignKey(
        "hospital.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_memberships"
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("staff", "hospital")
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.staff.user.username} - {self.hospital.name} ({self.role})"


class GoogleAccount(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="google_account"
    )

    patient = models.OneToOneField(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="google_account"
    )

    google_id = models.CharField(
        max_length=255,
        unique=True
    )

    email = models.EmailField()

    name = models.CharField(
        max_length=150,
        blank=True
    )

    picture = models.URLField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.email