from django.db import models
from decimal import Decimal


class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "Unpaid", "Unpaid"
        PARTIALLY_PAID = "Partially Paid", "Partially Paid"
        PAID = "Paid", "Paid"
        CANCELLED = "Cancelled", "Cancelled"

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="invoices",
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="invoices",
        db_index=True
    )
    # Set on the final bill of an inpatient stay (requirements E12, H8).
    admission = models.ForeignKey(
        "ipd.Admission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=30, default="Unpaid", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.invoice_number

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def tax_amount(self):
        return self.tax

    @property
    def total_amount(self):
        return self.total

    @property
    def total_paid(self):
        """Net amount received: payments minus refunds."""
        from .services import net_paid
        return net_paid(self)

    @property
    def balance_due(self):
        return self.total_amount - self.total_paid

    @property
    def is_paid(self):
        return self.balance_due <= Decimal("0.00")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hospital", "status"]),
            models.Index(fields=["hospital", "created_at"]),
            models.Index(fields=["patient", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(discount__gte=0), name="invoice_discount_non_negative"),
            models.CheckConstraint(condition=models.Q(total__gte=0), name="invoice_total_non_negative"),
        ]


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True
    )
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="invoiceitem_price_non_negative"),
            models.CheckConstraint(condition=models.Q(tax_rate__gte=0, tax_rate__lte=100), name="invoiceitem_tax_rate_range"),
        ]


class Payment(models.Model):
    """Money received (kind=payment) or returned (kind=refund). Rows are never edited or deleted."""

    class Kind(models.TextChoices):
        PAYMENT = "payment", "Payment"
        REFUND = "refund", "Refund"

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
        db_index=True
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PAYMENT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, default="Cash")
    receipt_number = models.CharField(max_length=40, blank=True, default="")
    reference = models.CharField(max_length=200, blank=True, default="")
    idempotency_key = models.CharField(max_length=80, blank=True, default="")
    received_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    paid_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-paid_at"]
        indexes = [
            models.Index(fields=["invoice", "paid_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_amount_positive"),
            models.UniqueConstraint(
                fields=["invoice", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="payment_unique_idempotency_key",
            ),
        ]


class InsuranceClaim(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="insurance_claims",
        db_index=True
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insurance_claims",
        db_index=True,
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )
    insurance_company = models.CharField(max_length=150)
    claim_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=30, default="Pending", db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["invoice", "status"]),
        ]