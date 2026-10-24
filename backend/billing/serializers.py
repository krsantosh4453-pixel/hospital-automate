from rest_framework import serializers
from .models import (
    Invoice,
    InvoiceItem,
    Payment,
    InsuranceClaim,
)
import uuid


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "description", "quantity", "unit_price", "subtotal", "tax_rate"]
        extra_kwargs = {
            "invoice": {"required": False},
            "subtotal": {"required": False},
        }
        read_only_fields = ["id"]

    def create(self, validated_data):
        # Calculate subtotal from quantity and unit_price
        if "subtotal" not in validated_data:
            quantity = validated_data.get("quantity", 1)
            unit_price = validated_data.get("unit_price", 0)
            validated_data["subtotal"] = quantity * unit_price
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "amount",
            "payment_method",
            "paid_at",
        ]
        read_only_fields = ["id", "paid_at"]


class InsuranceClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceClaim
        fields = [
            "id",
            "patient",
            "invoice",
            "insurance_company",
            "claim_number",
            "status",
            "amount",
        ]
        read_only_fields = ["id"]


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
        read_only_fields = ["id", "created_at", "total_paid", "balance_due", "is_paid", "hospital", "invoice_number", "subtotal", "tax_amount", "total_amount"]

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

    def create(self, validated_data):
        # Set hospital from context if not provided
        if "hospital" not in validated_data:
            scoped_hospital = self.context.get("scoped_hospital")
            if scoped_hospital:
                validated_data["hospital"] = scoped_hospital
        
        # Generate invoice number
        if "invoice_number" not in validated_data:
            validated_data["invoice_number"] = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        items_data = validated_data.pop("items_data", [])
        
        # Calculate totals from items
        subtotal = 0
        tax_total = 0
        for item_data in items_data:
            quantity = item_data.get("quantity", 1)
            unit_price = float(item_data.get("unit_price", 0))
            tax_rate = float(item_data.get("tax_rate", 0))
            item_subtotal = quantity * unit_price
            item_tax = item_subtotal * tax_rate / 100
            subtotal += item_subtotal
            tax_total += item_tax
        
        validated_data["total"] = subtotal + tax_total - float(validated_data.get("discount", 0))
        validated_data["tax"] = tax_total
        
        invoice = Invoice.objects.create(**validated_data)
        for item_data in items_data:
            # Calculate subtotal for item
            quantity = item_data.get("quantity", 1)
            unit_price = float(item_data.get("unit_price", 0))
            item_data["subtotal"] = quantity * unit_price
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items_data", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                quantity = item_data.get("quantity", 1)
                unit_price = float(item_data.get("unit_price", 0))
                item_data["subtotal"] = quantity * unit_price
                InvoiceItem.objects.create(invoice=instance, **item_data)
        return instance