from decimal import Decimal

from django.db import transaction

from rest_framework import serializers

from hospital.models import Hospital
from .models import (
    Supplier,
    PurchaseOrder,
    PurchaseItem,
    GoodsReceipt,
    GoodsReceiptItem,
    StockTransaction,
)


def _money(value):
    """Quantize a numeric value to 2 decimal places safely."""
    return Decimal(value).quantize(Decimal("0.01"))


def _resolve_scoped_hospital(serializer, attrs, model_hospital_field="hospital"):
    """Apply the project-wide ``?hospital=`` scoping rule.

    When the request is scoped with ``?hospital=<id>`` (exposed to
    the serializer as ``scoped_hospital``) the record may only belong
    to that hospital and may not be moved elsewhere. Returns the
    resolved hospital instance (or ``None`` when unscoped).
    """
    scoped = serializer.context.get("scoped_hospital")
    instance = serializer.instance

    hospital = attrs.get(model_hospital_field)
    if hospital is None and instance is not None:
        hospital = getattr(instance, model_hospital_field, None)

    if scoped is not None:
        if hospital is not None and hospital.pk != scoped.pk:
            raise serializers.ValidationError(
                {
                    model_hospital_field: (
                        "Record does not belong to the "
                        "selected hospital."
                    )
                }
            )
        if hospital is None:
            attrs[model_hospital_field] = scoped
            hospital = scoped

    # A hospital must always be resolvable, either from the scoped
    # ``?hospital=`` query param or from an explicit payload value.
    # Failing fast here yields a clean 400 instead of a DB error.
    if hospital is None:
        raise serializers.ValidationError(
            {model_hospital_field: "Hospital is required."}
        )

    return hospital


class SupplierSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )
    hospital = serializers.PrimaryKeyRelatedField(
        queryset=Hospital.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "hospital",
            "hospital_name",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
        validators = []  # Remove auto-generated UniqueTogetherValidator; DB constraint handles it

    

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Supplier name is required."
            )
        return value.strip()

    def validate(self, attrs):
        _resolve_scoped_hospital(self, attrs)
        return attrs

    


class PurchaseItemNestedSerializer(serializers.ModelSerializer):
    """Item used when creating a PurchaseOrder with nested lines.

    ``purchase`` is injected by the parent serializer, and
    ``quantity_received`` / ``line_total`` are always server-side.
    """

    class Meta:
        model = PurchaseItem
        fields = [
            "medicine",
            "batch",
            "expiry_date",
            "quantity_ordered",
            "unit_cost",
        ]

    def validate_quantity_ordered(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "Quantity ordered must be greater than 0."
            )
        return value

    def validate_unit_cost(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError(
                "Unit cost cannot be negative."
            )
        return value


class PurchaseItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True
    )
    quantity_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            "id",
            "purchase",
            "medicine",
            "medicine_name",
            "batch",
            "expiry_date",
            "quantity_ordered",
            "quantity_received",
            "unit_cost",
            "line_total",
            "quantity_remaining",
        ]
        read_only_fields = [
            "id",
            "line_total",
            "quantity_received",
            "quantity_remaining",
        ]

    def validate_quantity_ordered(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "Quantity ordered must be greater than 0."
            )
        return value

    def validate_unit_cost(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError(
                "Unit cost cannot be negative."
            )
        return value

    def validate(self, attrs):
        purchase = attrs.get("purchase")
        if purchase is None and self.instance is not None:
            purchase = self.instance.purchase

        medicine = attrs.get("medicine")
        if medicine is None and self.instance is not None:
            medicine = self.instance.medicine

        # When the request is hospital-scoped, a line can only be attached
        # to a purchase order that belongs to that same hospital. This
        # blocks cross-tenant writes via a guessed purchase ID.
        scoped = self.context.get("scoped_hospital")
        if (
            scoped is not None
            and purchase is not None
            and purchase.hospital_id != scoped.pk
        ):
            raise serializers.ValidationError(
                {
                    "purchase": (
                        "Purchase order does not belong to the "
                        "selected hospital."
                    )
                }
            )

        if purchase is not None and medicine is not None:
            # The medicine must belong to exactly the order's hospital.
            # A medicine with no hospital (``None``) is also rejected,
            # because it cannot be safely stocked under a hospital.
            if medicine.hospital_id != purchase.hospital_id:
                raise serializers.ValidationError(
                    {
                        "medicine": (
                            "Medicine does not belong to the "
                            "purchase order's hospital."
                        )
                    }
                )
        return attrs

    def create(self, validated_data):
        validated_data["line_total"] = _money(
            validated_data["quantity_ordered"]
            * validated_data["unit_cost"]
        )
        return super().create(validated_data)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True
    )
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )
    items = PurchaseItemNestedSerializer(many=True, required=False)
    hospital = serializers.PrimaryKeyRelatedField(
        queryset=Hospital.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "hospital",
            "hospital_name",
            "supplier",
            "supplier_name",
            "reference",
            "purchase_date",
            "status",
            "created_at",
            "items",
        ]
        read_only_fields = ["id", "created_at"]
        validators = []  # Remove auto-generated UniqueTogetherValidator; DB constraint handles it

    def validate_reference(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Reference is required."
            )
        return value.strip()

    def validate(self, attrs):
        hospital = _resolve_scoped_hospital(self, attrs)

        supplier = attrs.get("supplier")
        if supplier is None and self.instance is not None:
            supplier = self.instance.supplier

        # Supplier must belong to the same hospital as the order.
        if supplier is not None and hospital is not None:
            if supplier.hospital_id != hospital.pk:
                raise serializers.ValidationError(
                    {
                        "supplier": (
                            "Supplier does not belong to the "
                            "selected hospital."
                        )
                    }
                )

        # Every nested item's medicine must belong to the hospital.
        items = attrs.get("items") or []
        for item in items:
            medicine = item.get("medicine")
            if (
                hospital is not None
                and medicine is not None
                and medicine.hospital_id != hospital.pk
            ):
                raise serializers.ValidationError(
                    {
                        "items": (
                            "Medicine does not belong to the "
                            "selected hospital."
                        )
                    }
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # Atomic: the header and every nested line are created in a
        # single transaction. If any line fails, the whole purchase
        # creation rolls back and no partial order is left behind.
        items_data = validated_data.pop("items", [])
        order = PurchaseOrder.objects.create(**validated_data)
        for item in items_data:
            PurchaseItem.objects.create(
                purchase=order,
                line_total=_money(
                    item["quantity_ordered"] * item["unit_cost"]
                ),
                **item,
            )
        return order


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True
    )

    class Meta:
        model = GoodsReceiptItem
        fields = [
            "id",
            "goods_receipt",
            "medicine",
            "medicine_name",
            "batch",
            "expiry_date",
            "quantity_received",
            "unit_cost",
        ]
        read_only_fields = ["id"]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True
    )
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )
    purchase_reference = serializers.CharField(
        source="purchase.reference",
        read_only=True
    )
    items = GoodsReceiptItemSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id",
            "hospital",
            "hospital_name",
            "purchase",
            "purchase_reference",
            "supplier",
            "supplier_name",
            "reference",
            "receipt_date",
            "received_by",
            "note",
            "created_at",
            "items",
        ]
        read_only_fields = fields


class StockTransactionSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True
    )
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )

    class Meta:
        model = StockTransaction
        fields = [
            "id",
            "medicine",
            "medicine_name",
            "hospital",
            "hospital_name",
            "transaction_type",
            "quantity",
            "reason",
            "reference",
            "created_at",
        ]
        read_only_fields = fields


# =========================================================
# RECEIVE (GRN) INPUT SERIALIZERS
# =========================================================

class GoodsReceiptItemReceiveSerializer(serializers.Serializer):
    """One received line submitted to the atomic receive action."""

    purchase_item = serializers.IntegerField()
    quantity_received = serializers.IntegerField()
    unit_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
    )
    batch = serializers.CharField(required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)

    def validate_quantity_received(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "Received quantity must be greater than 0."
            )
        return value

    def validate_unit_cost(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Unit cost cannot be negative."
            )
        return value


class GoodsReceiptReceiveSerializer(serializers.Serializer):
    """Payload accepted by ``POST /purchases/{id}/receive/``."""

    # Required idempotency key. ``reference`` is unique per hospital, so
    # requiring it (instead of generating one) is what stops a replayed
    # request from being treated as new and double-incrementing stock.
    reference = serializers.CharField()
    receipt_date = serializers.DateField(required=False)
    received_by = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    items = GoodsReceiptItemReceiveSerializer(many=True)

    def validate_reference(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError(
                "A unique receipt reference is required."
            )
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one received item is required."
            )
        return value


class StockAdjustmentSerializer(serializers.Serializer):
    """Payload for manual stock adjustment."""

    medicine = serializers.IntegerField()
    type = serializers.ChoiceField(choices=["add", "remove"])
    quantity = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)
    reference = serializers.CharField(required=False, allow_blank=True)

    def validate_quantity(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0."
            )
        return value

    def validate_medicine(self, value):
        from pharmacy.models import Medicine
        try:
            medicine = Medicine.objects.get(pk=value)
        except Medicine.DoesNotExist:
            raise serializers.ValidationError("Medicine not found.")
        return medicine
