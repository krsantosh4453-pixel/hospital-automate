from django.contrib import admin
from .models import StaffProfile, StaffHospitalMembership, GoogleAccount


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "employee_id", "is_active_staff", "license_number", "created_at"]
    list_filter = ["role", "is_active_staff"]
    search_fields = ["user__username", "user__email", "employee_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(StaffHospitalMembership)
class StaffHospitalMembershipAdmin(admin.ModelAdmin):
    list_display = ["staff", "hospital", "role", "department", "is_active", "joined_at"]
    list_filter = ["role", "is_active", "hospital"]
    search_fields = ["staff__user__username", "hospital__name"]
    readonly_fields = ["joined_at", "updated_at"]


@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = ["email", "user", "patient", "created_at"]
    search_fields = ["email", "user__username", "google_id"]
    readonly_fields = ["created_at", "updated_at"]
