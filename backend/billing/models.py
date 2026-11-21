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
    # BUG-07: the outpatient bill a completed consultation and its verified
    # lab tests are charged to (billing/charges.py).
    visit = models.ForeignKey(
        "encounters.Visit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    # BUG-07: the bill that closes an inpatient stay. Charges of a stay collect
    # on its running bill; creating the final bill adds the bed days and sets this.
    is_final = models.BooleanField(default=False)
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
    # BUG-07: the price-list row this line was priced from. The row is never
    # edited, so the bill keeps showing what the price was on the day.
    service_price = models.ForeignKey(
        "billing.ServicePrice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoice_items",
    )
    # What kind of charge this is (a ServicePrice category, or "pharmacy").
    category = models.CharField(max_length=20, blank=True, default="")
    # BUG-07: the service an automatic charge bills, e.g. "visit:12:consultation"
    # or "labtest:5". Unique, so a retried request never charges twice. A
    # cancelled bill frees its keys (billing/charges.release_charges).
    charge_key = models.CharField(max_length=120, blank=True, default="")

    def __str__(self):
        return self.description

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="invoiceitem_price_non_negative"),
            models.CheckConstraint(condition=models.Q(tax_rate__gte=0, tax_rate__lte=100), name="invoiceitem_tax_rate_range"),
            models.UniqueConstraint(
                fields=["charge_key"], condition=~models.Q(charge_key=""), name="invoiceitem_unique_charge_key",
            ),
        ]


class ServicePrice(models.Model):
    """
    BUG-07: one entry of a hospital's price list (tariff), in INR.

    A row's price never changes once saved. A new price is a new row with a
    later ``effective_from``, which closes the previous row the day before
    (billing/price_list.py), so bills already issued keep their price and the
    history of every price stays readable. Medicine prices are not here: they
    are the selling price of each stocked batch (pharmacy.Medicine, capped by MRP).
    """

    class Category(models.TextChoices):
        CONSULTATION = "consultation", "Consultation"
        LABORATORY = "laboratory", "Laboratory investigation"
        BED = "bed", "Bed charge per day"
        INPATIENT = "inpatient", "Inpatient service"
        PROCEDURE = "procedure", "Procedure"
        OTHER = "other", "Other service"

    INR = "INR"

    hospital = models.ForeignKey("hospital.Hospital", on_delete=models.PROTECT, related_name="service_prices")
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=150)
    # What the price is for within its category: the lab test name, the bed
    # type, or the visit type of a consultation. Blank = the category default
    # (not allowed for laboratory: every investigation has its own price).
    applies_to = models.CharField(max_length=150, blank=True, default="")
    # A consultation fee for one doctor; it wins over the hospital default.
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.PROTECT, null=True, blank=True,
                               related_name="service_prices")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, choices=[(INR, "Indian rupee")], default=INR)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name", "-effective_from"]
        indexes = [models.Index(fields=["hospital", "category", "effective_from"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(unit_price__gt=0), name="serviceprice_price_positive"),
            models.CheckConstraint(condition=models.Q(tax_rate__gte=0, tax_rate__lte=100),
                                   name="serviceprice_tax_rate_range"),
            models.CheckConstraint(condition=models.Q(currency="INR"), name="serviceprice_currency_inr"),
            models.CheckConstraint(
                condition=models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=models.F("effective_from")),
                name="serviceprice_dates_in_order",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}: ₹{self.unit_price}"


class InvoiceWaiver(models.Model):
    """
    BUG-07: the only way a bill with charges on it may come to ₹0. An Admin or
    Hospital Manager writes it with a reason; rows are never edited or deleted.
    """

    invoice = models.OneToOneField(Invoice, on_delete=models.PROTECT, related_name="waiver")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    approved_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="+")
    approved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="invoicewaiver_amount_positive"),
        ]

    def __str__(self):
        return f"Waiver of {self.invoice_id}: ₹{self.amount}"


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
