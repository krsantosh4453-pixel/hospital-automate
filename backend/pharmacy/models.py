from django.db import models


class Medicine(models.Model):
    name = models.CharField(max_length=150)
    # Hospital this medicine stock belongs to.
    # Nullable so existing rows migrate safely; the API always
    # scopes medicines to a hospital.
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicines"
    )
    category = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default="Available")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Sale(models.Model):
    """A pharmacy sale (medicine dispensed to a patient).

    Sales are append-only records: creating a Sale atomically
    deducts the sold quantity from the related Medicine stock.
    """

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="sales"
    )
    hospital = models.ForeignKey(
        "hospital.Hospital",
        on_delete=models.CASCADE,
        related_name="pharmacy_sales"
    )
    patient_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    # Optional link to the clinical prescription this sale fulfils.
    prescription = models.ForeignKey(
        "clinical.Prescription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pharmacy_sales"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SALE-{self.pk}"

    class Meta:
        ordering = ["-created_at"]