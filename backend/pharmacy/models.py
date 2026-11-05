from django.db import models


class Medicine(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    # Hospital this medicine stock belongs to.
    # Nullable so existing rows migrate safely; the API always
    # scopes medicines to a hospital.
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicines",
        db_index=True
    )
    category = models.CharField(max_length=100, blank=True, db_index=True)
    batch = models.CharField(max_length=100, blank=True, db_index=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # GST % charged on this medicine when it is billed to a patient (F9).
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, default="Available", db_index=True)
    # Generic (salt) names, comma-separated for combinations; used by the prescription safety check.
    generic_name = models.CharField(max_length=255, blank=True, default="")
    # Store settings: how stock is counted, when it is low, and who usually supplies it.
    unit = models.CharField(max_length=30, default="Unit")
    reorder_level = models.PositiveIntegerField(default=10)
    supplier = models.ForeignKey(
        "procurement.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicines",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["hospital", "name"]),
            models.Index(fields=["hospital", "category"]),
            models.Index(fields=["hospital", "expiry_date"]),
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["name", "hospital"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(tax_rate__gte=0, tax_rate__lte=100), name="medicine_tax_rate_range"),
        ]


class Sale(models.Model):
    """A pharmacy sale (medicine dispensed to a patient).

    Sales are append-only records: creating a Sale atomically
    deducts the sold quantity from the related Medicine stock.
    """

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="sales",
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="pharmacy_sales",
        db_index=True
    )
    patient_name = models.CharField(max_length=150, db_index=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    # Optional link to the clinical prescription this sale fulfils.
    prescription = models.ForeignKey(
        "clinical.Prescription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pharmacy_sales",
        db_index=True
    )
    # The prescribed line this sale issues, so a prescription can be dispensed in parts.
    prescription_item = models.ForeignKey(
        "clinical.PrescriptionItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="pharmacy_sales"
    )
    # F8: set when a same-salt brand was given instead of the prescribed one.
    substituted_for = models.CharField(max_length=200, blank=True, default="")
    substitution_reason = models.CharField(max_length=255, blank=True, default="")
    dispensed_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"SALE-{self.pk}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "created_at"]),
            models.Index(fields=["medicine", "created_at"]),
            models.Index(fields=["patient_name", "hospital"]),
            models.Index(fields=["prescription", "created_at"]),
        ]

class SaleReturn(models.Model):
    """
    Medicine handed back by an OPD or IPD patient (F5). Returned stock goes
    back to its batch only when the pharmacist confirms it is fit to reissue
    and the batch has not expired; otherwise it is recorded as discarded.
    Rows are never edited or deleted.
    """

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="returns")
    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="pharmacy_returns")
    quantity = models.PositiveIntegerField()
    restocked = models.BooleanField(default=False)
    reason = models.CharField(max_length=255)
    # Quantity x the sale's unit price; paid back by the pharmacy counter.
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    returned_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["hospital", "created_at"])]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name="sale_return_quantity_positive")]

    def __str__(self):
        return f"RET-{self.pk}"
