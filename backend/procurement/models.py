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
    # I4: consignment stock is the supplier's until used; it is paid through
    # ConsignmentSettlement rows, not on receipt.
    is_consignment = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cancel_reason = models.CharField(max_length=255, blank=True, default="")
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


class PurchaseRequisition(models.Model):
    """
    A department's request for stock (I2). An administrator or hospital
    manager other than the requester approves or rejects it; an approved
    requisition becomes a purchase order, directly or through a quotation.
    """

    DRAFT, SUBMITTED, APPROVED, REJECTED, ORDERED, CANCELLED = (
        "Draft", "Submitted", "Approved", "Rejected", "Ordered", "Cancelled")
    STATUS_CHOICES = [(s, s) for s in (DRAFT, SUBMITTED, APPROVED, REJECTED, ORDERED, CANCELLED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="requisitions")
    department = models.ForeignKey("hospital.Department", on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="requisitions")
    reference = models.CharField(max_length=40)
    reason = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=SUBMITTED, db_index=True)
    requested_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True, default="")
    purchase_order = models.OneToOneField(PurchaseOrder, on_delete=models.PROTECT, null=True, blank=True,
                                          related_name="requisition")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["hospital", "reference"], name="unique_requisition_reference")]

    def __str__(self):
        return self.reference


class RequisitionItem(models.Model):
    requisition = models.ForeignKey(PurchaseRequisition, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey("pharmacy.Medicine", on_delete=models.PROTECT, related_name="requisition_items")
    quantity = models.PositiveIntegerField()
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name="requisition_quantity_positive")]


class SupplierQuotation(models.Model):
    """A supplier's prices for an approved requisition; accepting one places the order."""

    RECEIVED, ACCEPTED, REJECTED = "Received", "Accepted", "Rejected"
    STATUS_CHOICES = [(s, s) for s in (RECEIVED, ACCEPTED, REJECTED)]

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="quotations")
    requisition = models.ForeignKey(PurchaseRequisition, on_delete=models.PROTECT, related_name="quotations")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="quotations")
    reference = models.CharField(max_length=100)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=RECEIVED, db_index=True)
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["requisition", "supplier"], name="one_quotation_per_supplier")]


class QuotationItem(models.Model):
    quotation = models.ForeignKey(SupplierQuotation, on_delete=models.CASCADE, related_name="items")
    requisition_item = models.ForeignKey(RequisitionItem, on_delete=models.PROTECT, related_name="quotes")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["quotation", "requisition_item"], name="one_quote_per_line"),
            models.CheckConstraint(condition=models.Q(unit_cost__gte=0), name="quote_cost_non_negative"),
        ]


class StockIssue(models.Model):
    """Stock handed from the store to a department (ward, OT, ...). Rows are never edited or deleted."""

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="stock_issues")
    department = models.ForeignKey("hospital.Department", on_delete=models.PROTECT, related_name="stock_issues")
    medicine = models.ForeignKey("pharmacy.Medicine", on_delete=models.PROTECT, related_name="issues")
    quantity = models.PositiveIntegerField()
    received_by_name = models.CharField(max_length=150, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")
    idempotency_key = models.CharField(max_length=80, blank=True, default="")
    issued_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="stock_issue_quantity_positive"),
            models.UniqueConstraint(fields=["hospital", "idempotency_key"], condition=~models.Q(idempotency_key=""),
                                    name="stock_issue_unique_key"),
        ]


class SupplierReturn(models.Model):
    """Received stock sent back to its supplier (I4): damaged, expired, wrong or unused consignment."""

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="supplier_returns")
    receipt_item = models.ForeignKey(GoodsReceiptItem, on_delete=models.PROTECT, related_name="returns")
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    returned_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name="supplier_return_quantity_positive")]


class ConsignmentSettlement(models.Model):
    """Consignment stock reported as used and so payable to the supplier (I4)."""

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="consignment_settlements")
    receipt_item = models.ForeignKey(GoodsReceiptItem, on_delete=models.PROTECT, related_name="settlements")
    quantity = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, default="")
    settled_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name="consignment_quantity_positive")]
