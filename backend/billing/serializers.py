from rest_framework import serializers
from .models import (
    Invoice,
    InvoiceItem,
    Payment,
    InsuranceClaim,
)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = "__all__"
        extra_kwargs = {
            "invoice": {"required": False}
        }


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class InsuranceClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceClaim
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    # Read-only display helpers
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    
    # Write-only for creating invoice with items
    items_data = InvoiceItemSerializer(many=True, write_only=True, required=False)
    
    # Calculated fields
    total_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()

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
        ]
        read_only_fields = ["id", "created_at", "total_paid", "balance_due", "is_paid"]

    def get_total_paid(self, obj):
        return sum(p.amount for p in obj.payments.all())

    def get_balance_due(self, obj):
        total_paid = sum(p.amount for p in obj.payments.all())
        return float(obj.total) - float(total_paid)

    def get_is_paid(self, obj):
        total_paid = sum(p.amount for p in obj.payments.all())
        return float(total_paid) >= float(obj.total)

    def create(self, validated_data):
        items_data = validated_data.pop("items_data", [])
        invoice = Invoice.objects.create(**validated_data)
        for item_data in items_data:
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
                InvoiceItem.objects.create(invoice=instance, **item_data)
        return instance