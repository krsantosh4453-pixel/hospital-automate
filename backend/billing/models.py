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
    # F9: set on the medicine bill of a prescription (billing/pharmacy_charges.py).
    prescription = models.ForeignKey(
        "clinical.Prescription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    # P1-05: INV/26-27/000001, consecutive per hospital per financial year
    # (billing/numbering.py), so unique within a hospital, not across them.
    invoice_number = models.CharField(max_length=50)
    discount =models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
            models.UniqueConstraint(fields=["hospital", "invoice_number"], name="unique_invoice_number_per_hospital"),
        ]


class InvoiceSequence(models.Model):
    """
    P1-05: the last invoice number a hospital issued in a financial year
    (April to March, keyed by its starting year). Only billing/numbering.py
    changes it, through a row-locking UPDATE, so two counters never share one.
    """

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.CASCADE, related_name="invoice_sequences")
    financial_year = models.PositiveIntegerField()
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hospital", "financial_year"],
                                    name="one_invoice_sequence_per_hospital_year"),
        ]

    def __str__(self):
        return f"{self.hospital_id} FY{self.financial_year}: {self.last_value}"


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
    # P1-10: HSN code of a medicine line, printed on the GST bill.
    hsn_code = models.CharField(max_length=8, blank=True, default="")
    # F9: the pharmacy sale this line bills. One line per sale, so a sale is
    # never charged twice; the quantity drops when medicine is returned.
    pharmacy_sale = models.OneToOneField(
        "pharmacy.Sale",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoice_item",
    )

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

class AdvanceAccount(models.Model):
    """
    A patient's advance (deposit) balance at one hospital (H4). The balance
    changes only through AdvanceTransaction rows written by billing.advances,
    with this row locked, so it never goes below zero or double-counts.
    """

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="advance_accounts")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="advance_accounts")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "patient"], name="advance_account_one_per_patient"),
            models.CheckConstraint(condition=models.Q(balance__gte=0), name="advance_balance_non_negative"),
        ]

    def __str__(self):
        return f"Advance {self.patient_id} @ {self.hospital_id}: {self.balance}"


class AdvanceTransaction(models.Model):
    """One movement of advance money. Rows are never edited or deleted."""

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        APPLIED = "applied", "Applied to bill"
        RETURNED = "returned", "Returned from bill"
        REFUND = "refund", "Refunded to patient"

    account = models.ForeignKey(AdvanceAccount, on_delete=models.PROTECT, related_name="transactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, blank=True, default="")
    receipt_number = models.CharField(max_length=40)
    reference = models.CharField(max_length=200, blank=True, default="")
    idempotency_key = models.CharField(max_length=80, blank=True, default="")
    # The invoice payment (or refund) this movement created, for applied/returned rows.
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, null=True, blank=True, related_name="advance_transactions")
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, null=True, blank=True, related_name="advance_transaction")
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["account", "created_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="advance_amount_positive"),
            models.CheckConstraint(condition=models.Q(balance_after__gte=0), name="advance_balance_after_non_negative"),
            models.UniqueConstraint(
                fields=["account", "idempotency_key"], condition=~models.Q(idempotency_key=""),
                name="advance_unique_idempotency_key",
            ),
        ]
