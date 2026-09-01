from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'age', 'gender', 'phone', 'doctor', 'status', 'created_at')
    list_filter = ('status', 'gender', 'doctor', 'created_at')
    search_fields = ('name', 'phone', 'doctor')
    ordering = ('-created_at',)
