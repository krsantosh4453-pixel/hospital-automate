from django.db import models
from decimal import Decimal


class Invoice(models.Model):
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
        return sum(payment.amount for payment in self.payments.all())

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


class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, default="Cash")
    paid_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-paid_at"]
        indexes = [
            models.Index(fields=["invoice", "paid_at"]),
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