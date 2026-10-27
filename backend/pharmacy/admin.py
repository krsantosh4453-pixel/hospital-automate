from django.contrib import admin

from .models import Medicine, Sale


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "hospital",
        "category",
        "batch",
        "quantity",
        "price",
        "status",
    )
    list_filter = ("hospital", "category", "status")
    search_fields = ("name", "batch")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "medicine",
        "hospital",
        "patient_name",
        "quantity",
        "unit_price",
        "total",
        "prescription",
        "created_at",
    )
    list_filter = ("hospital",)
    search_fields = ("patient_name", "medicine__name")
    readonly_fields = ("created_at",)


# Every other pharmacy table, with default columns (config/admin_registry.py).
from config.admin_registry import register_app_models  # noqa: E402

register_app_models("pharmacy")
