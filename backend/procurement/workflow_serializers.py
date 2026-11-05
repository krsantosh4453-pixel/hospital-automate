"""Serializers for the store workflows in procurement/workflows.py."""

from rest_framework import serializers

from hospital.models import Department
from pharmacy.models import Medicine

from .models import (
    ConsignmentSettlement,
    GoodsReceiptItem,
    PurchaseRequisition,
    QuotationItem,
    RequisitionItem,
    StockIssue,
    Supplier,
    SupplierQuotation,
    SupplierReturn,
)


def _name(user):
    return (user.get_full_name() or user.username) if user else ""


class RequisitionItemSerializer(serializers.ModelSerializer):
    medicine = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.all())
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)

    class Meta:
        model = RequisitionItem
        fields = ["id", "medicine", "medicine_name", "quantity", "note"]
        extra_kwargs = {"quantity": {"min_value": 1}}


class RequisitionSerializer(serializers.ModelSerializer):
    items = RequisitionItemSerializer(many=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    requested_by_name = serializers.SerializerMethodField()
    decided_by_name = serializers.SerializerMethodField()
    purchase_reference = serializers.CharField(source="purchase_order.reference", read_only=True, default="")

    class Meta:
        model = PurchaseRequisition
        fields = ["id", "hospital", "department", "department_name", "reference", "reason", "status", "items",
                  "requested_by", "requested_by_name", "decided_by", "decided_by_name", "decided_at", "decision_note",
                  "purchase_order", "purchase_reference", "created_at"]
        read_only_fields = ["id", "reference", "status", "requested_by", "decided_by", "decided_at", "decision_note",
                            "purchase_order", "created_at"]
        extra_kwargs = {"hospital": {"required": False}}

    def get_requested_by_name(self, obj) -> str:
        return _name(obj.requested_by)

    def get_decided_by_name(self, obj) -> str:
        return _name(obj.decided_by)

    def validate(self, attrs):
        items = attrs.get("items") or []
        if not items:
            raise serializers.ValidationError({"items": "Add at least one medicine."})
        medicines = [item["medicine"] for item in items]
        if len(set(m.pk for m in medicines)) != len(medicines):
            raise serializers.ValidationError({"items": "Each medicine once per requisition."})
        hospital = attrs.get("hospital") or self.context.get("scoped_hospital")
        hospital_id = getattr(hospital, "pk", hospital)
        if hospital_id and any(m.hospital_id != hospital_id for m in medicines):
            raise serializers.ValidationError({"items": "Every medicine must be stock of this hospital."})
        department = attrs.get("department")
        if department is not None and hospital_id and department.hospital_id != hospital_id:
            raise serializers.ValidationError({"department": "Department of another hospital."})
        return attrs

    def create(self, validated_data):
        items = validated_data.pop("items")
        requisition = PurchaseRequisition.objects.create(**validated_data)
        RequisitionItem.objects.bulk_create(RequisitionItem(requisition=requisition, **item) for item in items)
        return requisition


class DecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class OrderRequisitionSerializer(serializers.Serializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    # [{item: requisition item id, unit_cost}]
    unit_costs = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate_unit_costs(self, rows):
        try:
            return {int(row["item"]): serializers.DecimalField(max_digits=10, decimal_places=2).to_internal_value(
                row["unit_cost"]) for row in rows}
        except (KeyError, TypeError, ValueError):
            raise serializers.ValidationError("Each row needs item and unit_cost.")


class QuotationItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="requisition_item.medicine.name", read_only=True)
    quantity = serializers.IntegerField(source="requisition_item.quantity", read_only=True)

    class Meta:
        model = QuotationItem
        fields = ["id", "requisition_item", "medicine_name", "quantity", "unit_cost"]
        extra_kwargs = {"unit_cost": {"min_value": 0}}


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    requisition_reference = serializers.CharField(source="requisition.reference", read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = SupplierQuotation
        fields = ["id", "hospital", "requisition", "requisition_reference", "supplier", "supplier_name", "reference",
                  "valid_until", "status", "items", "total", "created_at"]
        read_only_fields = ["id", "status", "created_at"]
        extra_kwargs = {"hospital": {"required": False}}

    def get_total(self, obj) -> str:
        return str(sum((line.unit_cost * line.requisition_item.quantity for line in obj.items.all()), 0))

    def validate(self, attrs):
        requisition, supplier = attrs["requisition"], attrs["supplier"]
        if requisition.status != PurchaseRequisition.APPROVED:
            raise serializers.ValidationError({"requisition": "Quotations are taken for approved requisitions only."})
        if supplier.hospital_id != requisition.hospital_id:
            raise serializers.ValidationError({"supplier": "Supplier of another hospital."})
        lines = {line["requisition_item"].pk for line in attrs["items"]}
        wanted = set(requisition.items.values_list("pk", flat=True))
        if lines != wanted:
            raise serializers.ValidationError({"items": "Quote a price for every medicine on the requisition, once."})
        return attrs

    def create(self, validated_data):
        items = validated_data.pop("items")
        quotation = SupplierQuotation.objects.create(**validated_data)
        QuotationItem.objects.bulk_create(QuotationItem(quotation=quotation, **item) for item in items)
        return quotation


class StockIssueSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    medicine = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.all())
    department_name = serializers.CharField(source="department.name", read_only=True)
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    batch = serializers.CharField(source="medicine.batch", read_only=True)
    issued_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockIssue
        fields = ["id", "hospital", "department", "department_name", "medicine", "medicine_name", "batch", "quantity",
                  "received_by_name", "note", "idempotency_key", "issued_by", "issued_by_name", "created_at"]
        read_only_fields = ["id", "issued_by", "created_at"]
        extra_kwargs = {"hospital": {"required": False}, "quantity": {"min_value": 1},
                        "idempotency_key": {"required": False}}
        validators = []

    def get_issued_by_name(self, obj) -> str:
        return _name(obj.issued_by)


class _ReceiptLineSerializer(serializers.ModelSerializer):
    receipt_item = serializers.PrimaryKeyRelatedField(queryset=GoodsReceiptItem.objects.select_related("goods_receipt"))
    medicine_name = serializers.CharField(source="receipt_item.medicine.name", read_only=True)
    receipt_reference = serializers.CharField(source="receipt_item.goods_receipt.reference", read_only=True)
    supplier_name = serializers.CharField(source="receipt_item.goods_receipt.supplier.name", read_only=True)


class SupplierReturnSerializer(_ReceiptLineSerializer):
    class Meta:
        model = SupplierReturn
        fields = ["id", "hospital", "receipt_item", "medicine_name", "receipt_reference", "supplier_name", "quantity",
                  "reason", "credit_amount", "returned_by", "created_at"]
        read_only_fields = ["id", "hospital", "credit_amount", "returned_by", "created_at"]
        extra_kwargs = {"quantity": {"min_value": 1}}


class ConsignmentSettlementSerializer(_ReceiptLineSerializer):
    class Meta:
        model = ConsignmentSettlement
        fields = ["id", "hospital", "receipt_item", "medicine_name", "receipt_reference", "supplier_name", "quantity",
                  "amount", "reference", "settled_by", "created_at"]
        read_only_fields = ["id", "hospital", "amount", "settled_by", "created_at"]
        extra_kwargs = {"quantity": {"min_value": 1}}
