from rest_framework import serializers
from .models import (
    AdvanceAccount,
    AdvanceTransaction,
    Invoice,
    InvoiceItem,
    InvoiceWaiver,
    Payment,
    InsuranceClaim,
    ServicePrice,
)
from django.db import transaction

from hospital.models import Hospital
from patients.models import Patient

from .numbering import next_invoice_number
from .price_list import price_line
from .services import line_subtotal, money, recalculate, refuse_unexplained_zero

FREE_LINE = "Price must be more than ₹0. Free care is recorded as a waiver by an Admin or Hospital Manager."


class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Line subtotal is always quantity x unit price, computed on the server.
    BUG-07: a line may name a ``service_price`` from the price list; its
    price, GST and category then come from the list.
    """

    class Meta:
        model = InvoiceItem
        fields = ["id", "invoice", "description", "quantity", "unit_price", "subtotal", "tax_rate", "pharmacy_sale",
                  "service_price", "category", "charge_key"]
        extra_kwargs = {
            "invoice": {"required": False},
            "unit_price": {"required": False},
            "description": {"required": False},
        }
        # pharmacy_sale is set only by billing/pharmacy_charges.py (F9);
        # category and charge_key by billing/charges.py (BUG-07).
        read_only_fields = ["id", "subtotal", "pharmacy_sale", "category", "charge_key"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate_unit_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(FREE_LINE)
        return value

    def validate(self, attrs):
        if self.instance is None and attrs.get("service_price") is None:
            if attrs.get("unit_price") is None:
                raise serializers.ValidationError({"unit_price": "Give the price, or choose the service from the price list."})
            if not (attrs.get("description") or "").strip():
                raise serializers.ValidationError({"description": "Describe the charge."})
        return attrs

    def validate_tax_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Tax rate must be between 0 and 100.")
        return value

    def create(self, validated_data):
        validated_data = price_line(validated_data, validated_data["invoice"].hospital_id)
        validated_data["subtotal"] = line_subtotal(validated_data.get("quantity", 1), validated_data["unit_price"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.service_price_id and "service_price" not in validated_data:
            # A line priced from the list keeps the list's price and GST.
            for field in ("unit_price", "tax_rate"):
                if field in validated_data and validated_data[field] != getattr(instance, field):
                    raise serializers.ValidationError({field: "This line is priced from the price list."})
        validated_data = price_line(validated_data, instance.invoice.hospital_id)
        instance = super().update(instance, validated_data)
        instance.subtotal = line_subtotal(instance.quantity, instance.unit_price)
        instance.save(update_fields=["subtotal"])
        return instance


class PaymentSerializer(serializers.ModelSerializer):
    """Create-only; amounts are checked against the server-side balance."""

    idempotency_key = serializers.CharField(max_length=80, required=False, allow_blank=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "kind",
            "amount",
            "payment_method",
            "receipt_number",
            "reference",
            "idempotency_key",
            "received_by",
            "paid_at",
        ]
        read_only_fields = ["id", "kind", "receipt_number", "received_by", "paid_at"]
        # Duplicate keys are resolved by billing.services.record_payment
        # (returns the original payment), not rejected as a validation error.
        validators = []


class InsuranceClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceClaim
        fields = [
            "id",
            "hospital",
            "patient",
            "invoice",
            "insurance_company",
            "claim_number",
            "status",
            "amount",
        ]
        read_only_fields = ["id", "hospital"]

    def validate(self, attrs):
        invoice = attrs.get("invoice")
        patient = attrs.get("patient")
        amount = attrs.get("amount")
        if invoice is not None and patient is not None and invoice.patient_id != patient.id:
            raise serializers.ValidationError({"invoice": "Invoice belongs to a different patient."})
        if invoice is not None and amount is not None and amount > invoice.total:
            raise serializers.ValidationError({"amount": "Claim cannot exceed the invoice total."})
        return attrs

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        return value


class InvoiceWaiverSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceWaiver
        fields = ["id", "amount", "reason", "approved_by", "approved_by_name", "approved_at"]
        read_only_fields = fields

    def get_approved_by_name(self, obj) -> str:
        user = obj.approved_by
        return (user.get_full_name() or user.username) if user else ""


class ServicePriceSerializer(serializers.ModelSerializer):
    """BUG-07: a price-list row. Rows are created and retired, never edited."""

    doctor_name = serializers.CharField(source="doctor.name", read_only=True, default="")
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = ServicePrice
        fields = ["id", "hospital", "category", "code", "name", "applies_to", "doctor", "doctor_name", "unit_price",
                  "tax_rate", "currency", "effective_from", "effective_to", "is_current", "created_by", "created_at"]
        read_only_fields = ["id", "effective_to", "created_by", "created_at", "doctor_name", "is_current"]
        extra_kwargs = {"hospital": {"required": False}, "effective_from": {"required": False}}

    def get_is_current(self, obj) -> bool:
        from config.hospital_time import hospital_today

        today = hospital_today()
        return obj.effective_from <= today and (obj.effective_to is None or obj.effective_to >= today)

    def validate_code(self, value):
        code = value.strip().upper()
        if not code:
            raise serializers.ValidationError("Give the service a code.")
        return code

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name the service.")
        return value.strip()

    def validate_unit_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("A price must be more than ₹0. Free care is recorded as a waiver.")
        return value

    def validate_tax_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("GST must be between 0 and 100 percent.")
        return value

    def validate(self, attrs):
        category = attrs.get("category")
        attrs["applies_to"] = (attrs.get("applies_to") or "").strip()
        if category == ServicePrice.Category.LABORATORY and not attrs["applies_to"]:
            raise serializers.ValidationError({"applies_to": "Give the investigation name exactly as doctors order it."})
        if attrs.get("doctor") is not None and category != ServicePrice.Category.CONSULTATION:
            raise serializers.ValidationError({"doctor": "Only a consultation fee can belong to one doctor."})
        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    # Read-only display helpers
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    # RL-16: the UHID this bill's hospital issued, shown instead of a made-up number.
    patient_uhid = serializers.SerializerMethodField()
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    
    # Write-only for creating invoice with items
    items_data = InvoiceItemSerializer(many=True, write_only=True, required=False)
    
    # Calculated fields - use SerializerMethodField to avoid setting issues
    total_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    waiver = InvoiceWaiverSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "admission",
            "prescription",
            "visit",
            "is_final",
            "waiver",
            "patient",
            "patient_name",
            "patient_uhid",
            "hospital",
            "hospital_name",
            "discount",
            "tax",
            "total",
            "status",
            "created_at",
            "items",
            "items_data",
            "payments",
            "total_paid",
            "balance_due",
            "is_paid",
            "subtotal",
            "tax_amount",
            "total_amount",
        ]
        # Money and status are derived from items and payments (billing.services).
        read_only_fields = [
            "id", "created_at", "total_paid", "balance_due", "is_paid", "hospital", "invoice_number", "admission",
            "prescription", "visit", "is_final", "waiver",
            "subtotal", "tax_amount", "total_amount", "tax", "total", "status",
        ]

    def validate_hospital(self, value):
        """Ensure user has access to the hospital."""
        request = self.context.get("request")
        if request and value:
            from users.permissions import get_user_hospital_ids
            user_hospital_ids = get_user_hospital_ids(request.user)
            if value.id not in user_hospital_ids:
                raise serializers.ValidationError(
                    "You do not have access to this hospital."
                )
        return value

    def validate_patient(self, value):
        """Ensure patient belongs to the hospital."""
        hospital = self.initial_data.get("hospital") or self.context.get("scoped_hospital")
        if hospital and value:
            from hospital.models import Hospital
            from clinical.serializers import _patient_belongs_to_hospital
            # hospital may be an ID (int) or a Hospital object
            if isinstance(hospital, int):
                try:
                    hospital = Hospital.objects.get(pk=hospital)
                except Hospital.DoesNotExist:
                    raise serializers.ValidationError(
                        "Invalid hospital."
                    )
            if not _patient_belongs_to_hospital(value, hospital):
                raise serializers.ValidationError(
                    "This patient is not registered in this hospital."
                )
        return value

    def get_patient_uhid(self, obj) -> str:
        if not obj.patient_id:
            return ""
        memberships = getattr(obj.patient, "_prefetched_objects_cache", {}).get("hospital_memberships")
        if memberships is None:
            memberships = obj.patient.hospital_memberships.all()
        return next((m.uhid for m in memberships if m.hospital_id == obj.hospital_id and m.is_active), "")

    def get_total_paid(self, obj) -> str:
        # Exact decimal string, like the stored money fields.
        return str(money(obj.total_paid))

    def get_balance_due(self, obj) -> str:
        return str(money(obj.balance_due))

    def get_is_paid(self, obj) -> bool:
        return obj.is_paid

    def get_subtotal(self, obj) -> str:
        return str(money(obj.subtotal))

    def get_tax_amount(self, obj) -> str:
        return str(money(obj.tax_amount))

    def get_total_amount(self, obj) -> str:
        return str(money(obj.total_amount))

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def create(self, validated_data):
        if "hospital" not in validated_data:
            scoped_hospital = self.context.get("scoped_hospital")
            if scoped_hospital:
                validated_data["hospital"] = scoped_hospital
        items_data = validated_data.pop("items_data", [])
        if not items_data:
            # BUG-07: an empty bill would read as ₹0 "Paid".
            raise serializers.ValidationError({"items_data": "Add at least one bill line."})
        with transaction.atomic():
            # P1-05: the hospital's consecutive GST series, locked until this bill is saved.
            validated_data["invoice_number"] = next_invoice_number(validated_data["hospital"])
            invoice = Invoice.objects.create(**validated_data)
            self._add_lines(invoice, items_data)
            recalculate(invoice)
            refuse_unexplained_zero(invoice)
        return invoice

    @staticmethod
    def _add_lines(invoice, items_data):
        for item_data in items_data:
            item_data.pop("invoice", None)
            item_data = price_line(item_data, invoice.hospital_id)
            item_data["subtotal"] = line_subtotal(item_data.get("quantity", 1), item_data["unit_price"])
            InvoiceItem.objects.create(invoice=invoice, **item_data)

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items_data", None)
        if items_data is not None and instance.payments.exists():
            raise serializers.ValidationError(
                {"items_data": "Items cannot be replaced after a payment; issue a refund or a new invoice."}
            )
        if items_data is not None and instance.items.filter(pharmacy_sale__isnull=False).exists():
            raise serializers.ValidationError(
                {"items_data": "Medicine lines come from the pharmacy; return the medicine there to change them."}
            )
        if items_data is not None and instance.items.exclude(charge_key="").exists():
            raise serializers.ValidationError(
                {"items_data": "This bill holds charges captured from the price list; cancel it instead."}
            )
        waived = InvoiceWaiver.objects.filter(invoice=instance).exists()
        if waived and "discount" in validated_data:
            raise serializers.ValidationError({"discount": "This bill was waived; its discount cannot change."})
        if waived and items_data is not None:
            raise serializers.ValidationError({"items_data": "This bill was waived; its items cannot change."})
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            if items_data is not None:
                instance.items.all().delete()
                self._add_lines(instance, items_data)
            recalculate(instance)
            refuse_unexplained_zero(instance)
        return instance


class AdvanceTransactionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True, default="")

    class Meta:
        model = AdvanceTransaction
        fields = ["id", "kind", "amount", "balance_after", "payment_method", "receipt_number", "reference",
                  "invoice", "invoice_number", "created_by", "created_by_name", "created_at"]
        read_only_fields = fields

    def get_created_by_name(self, obj) -> str:
        user = obj.created_by
        return (user.get_full_name() or user.username) if user else ""


class AdvanceAccountSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    transactions = serializers.SerializerMethodField()

    # The latest movements; the full history is in the transactions list.
    RECENT = 50

    class Meta:
        model = AdvanceAccount
        fields = ["id", "hospital", "patient", "patient_name", "balance", "updated_at", "transactions"]
        read_only_fields = fields

    def get_transactions(self, obj) -> list:
        return AdvanceTransactionSerializer(obj.transactions.select_related("invoice", "created_by")[: self.RECENT],
                                            many=True).data


class AdvanceDepositSerializer(serializers.Serializer):
    hospital = serializers.PrimaryKeyRelatedField(queryset=Hospital.objects.all(), required=False)
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.CharField(max_length=30, default="Cash")
    reference = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class AdvanceMoveSerializer(serializers.Serializer):
    """Amount plus what the action needs: a reason for refunds, a key against double submits."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    payment_method = serializers.CharField(max_length=30, required=False, default="Cash")
    idempotency_key = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
