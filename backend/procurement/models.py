from django.db import models


class Supplier(models.Model):
    """A vendor/supplier a hospital buys medicines from.

    Suppliers are hospital-scoped: every supplier belongs to exactly
    one hospital and may never be used by another hospital.
    """

    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="suppliers"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        # A supplier name is unique within a hospital.
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "name"],
                name="unique_supplier_name_per_hospital",
            )
        ]


class PurchaseOrder(models.Model):
    """Header of a medicine purchase order placed with a supplier."""

    STATUS_DRAFT = "Draft"
    STATUS_ORDERED = "Ordered"
    STATUS_PARTIAL = "Partial"
    STATUS_RECEIVED = "Received"
    STATUS_CANCELLED = "Cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_RECEIVED, "Received"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    # Statuses that may still receive stock.
    RECEIVABLE_STATUSES = (STATUS_DRAFT, STATUS_ORDERED, STATUS_PARTIAL)

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="purchase_orders"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders"
    )
    reference = models.CharField(max_length=100)
    purchase_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ORDERED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference

    class Meta:
        ordering = ["-created_at"]
        # Reference must be unique per hospital.
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "reference"],
                name="unique_purchase_reference_per_hospital",
            )
        ]


class PurchaseItem(models.Model):
    """A single ordered line on a PurchaseOrder."""

    purchase = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items"
    )
    medicine = models.ForeignKey(
        "pharmacy.Medicine",
        on_delete=models.PROTECT,
        related_name="purchase_items"
    )
    batch = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    quantity_ordered = models.PositiveIntegerField(default=0)
    quantity_received = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"{self.purchase.reference} - {self.medicine.name}"

    class Meta:
        ordering = ["id"]

    @property
    def quantity_remaining(self):
        return max(self.quantity_ordered - self.quantity_received, 0)


class GoodsReceipt(models.Model):
    """A Goods Receipt Note (GRN).

    Receipts are append-only. ``reference`` is a persisted
    idempotency key, unique per hospital, that prevents the same
    receipt from being applied twice.
    """

    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="goods_receipts"
    )
    # Nullable to support a direct receipt with no prior order.
    purchase = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goods_receipts"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="goods_receipts"
    )
    reference = models.CharField(max_length=100)
    receipt_date = models.DateField()
    received_by = models.CharField(max_length=150, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference

    class Meta:
        ordering = ["-created_at"]
        # Idempotency guard: a receipt reference is unique per hospital.
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "reference"],
                name="unique_grn_reference_per_hospital",
            )
        ]


class GoodsReceiptItem(models.Model):
    """A single received line on a GoodsReceipt (GRN)."""

    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="items"
    )
    medicine = models.ForeignKey(
        "pharmacy.Medicine",
        on_delete=models.PROTECT,
        related_name="goods_receipt_items"
    )
    batch = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    quantity_received = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.goods_receipt.reference} - {self.medicine.name}"

    class Meta:
        ordering = ["id"]


class StockTransaction(models.Model):
    """Append-only inventory ledger for medicine stock movements.

    Every stock change (receipt, sale, manual adjustment) is
    recorded here. Rows are never updated or deleted.
    """

    TYPE_IN = "IN"
    TYPE_OUT = "OUT"
    TYPE_ADJUST = "ADJUST"

    TYPE_CHOICES = [
        (TYPE_IN, "IN"),
        (TYPE_OUT, "OUT"),
        (TYPE_ADJUST, "ADJUST"),
    ]

    medicine = models.ForeignKey(
        "pharmacy.Medicine",
        on_delete=models.PROTECT,
        related_name="stock_transactions"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="stock_transactions"
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_IN,
    )
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} {self.quantity} {self.medicine.name}"

    class Meta:
        ordering = ["-created_at"]
