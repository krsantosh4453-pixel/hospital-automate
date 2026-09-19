from django.contrib import admin

from .models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseItem,
    PurchaseOrder,
    StockTransaction,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "hospital",
        "contact_person",
        "phone",
        "email",
        "is_active",
        "created_at",
    )
    list_filter = ("hospital", "is_active")
    search_fields = ("name", "contact_person", "phone", "email")
    readonly_fields = ("created_at",)


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "hospital",
        "supplier",
        "purchase_date",
        "status",
        "created_at",
    )
    list_filter = ("hospital", "status")
    search_fields = ("reference", "supplier__name")
    readonly_fields = ("created_at",)
    inlines = (PurchaseItemInline,)


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "purchase",
        "medicine",
        "batch",
        "expiry_date",
        "quantity_ordered",
        "quantity_received",
        "unit_cost",
        "line_total",
    )
    list_filter = ("purchase__hospital",)
    search_fields = ("purchase__reference", "medicine__name", "batch")


class GoodsReceiptItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 0


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "hospital",
        "supplier",
        "purchase",
        "receipt_date",
        "received_by",
        "created_at",
    )
    list_filter = ("hospital", "supplier")
    search_fields = ("reference", "supplier__name", "received_by")
    readonly_fields = ("created_at",)
    inlines = (GoodsReceiptItemInline,)


@admin.register(GoodsReceiptItem)
class GoodsReceiptItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "goods_receipt",
        "medicine",
        "batch",
        "expiry_date",
        "quantity_received",
        "unit_cost",
    )
    list_filter = ("goods_receipt__hospital",)
    search_fields = ("goods_receipt__reference", "medicine__name", "batch")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "hospital",
        "medicine",
        "transaction_type",
        "quantity",
        "reason",
        "reference",
        "created_at",
    )
    list_filter = ("hospital", "transaction_type")
    search_fields = ("medicine__name", "reason", "reference")
    readonly_fields = ("created_at",)
