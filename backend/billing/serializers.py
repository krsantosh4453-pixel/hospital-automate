from rest_framework import serializers
from .models import (
    Invoice,
    InvoiceItem,
    Payment,
    InsuranceClaim,
)
from django.db import transaction

from .services import line_subtotal, new_reference, recalculate


class InvoiceItemSerializer(serializers.ModelSerializer):
    """Line subtotal is always quantity x unit price, computed on the server."""

    class Meta:
        model = InvoiceItem
        fields = ["id", "invoice", "description", "quantity", "unit_price", "subtotal", "tax_rate"]
        extra_kwargs = {"invoice": {"required": False}}
        read_only_fields = ["id", "subtotal"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate_tax_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Tax rate must be between 0 and 100.")
        return value

    def create(self, validated_data):
        validated_data["subtotal"] = line_subtotal(validated_data.get("quantity", 1), validated_data["unit_price"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
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


class InvoiceSerializer(serializers.ModelSerializer):
    # Read-only display helpers
    patient_name = serializers.CharField(source="patient.name", read_only=True)
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

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "patient",
            "patient_name",
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
            "id", "created_at", "total_paid", "balance_due", "is_paid", "hospital", "invoice_number",
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

    def get_total_paid(self, obj):
        return obj.total_paid

    def get_balance_due(self, obj):
        return obj.balance_due

    def get_is_paid(self, obj):
        return obj.is_paid

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_tax_amount(self, obj):
        return obj.tax_amount

    def get_total_amount(self, obj):
        return obj.total_amount

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def create(self, validated_data):
        if "hospital" not in validated_data:
            scoped_hospital = self.context.get("scoped_hospital")
            if scoped_hospital:
                validated_data["hospital"] = scoped_hospital
        validated_data["invoice_number"] = new_reference("INV")
        items_data = validated_data.pop("items_data", [])
        with transaction.atomic():
            invoice = Invoice.objects.create(**validated_data)
            for item_data in items_data:
                item_data.pop("invoice", None)
                item_data["subtotal"] = line_subtotal(item_data.get("quantity", 1), item_data["unit_price"])
                InvoiceItem.objects.create(invoice=invoice, **item_data)
            recalculate(invoice)
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items_data", None)
        if items_data is not None and instance.payments.exists():
            raise serializers.ValidationError(
                {"items_data": "Items cannot be replaced after a payment; issue a refund or a new invoice."}
            )
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            if items_data is not None:
                instance.items.all().delete()
                for item_data in items_data:
                    item_data.pop("invoice", None)
                    item_data["subtotal"] = line_subtotal(item_data.get("quantity", 1), item_data["unit_price"])
                    InvoiceItem.objects.create(invoice=instance, **item_data)
            recalculate(instance)
        return instance
