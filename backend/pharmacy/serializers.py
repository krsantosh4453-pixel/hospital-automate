from decimal import Decimal

from rest_framework import serializers

from .models import Medicine, Sale, SaleReturn


class MedicineSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)

    class Meta:
        model = Medicine
        fields = [
            "id",
            "name",
            "hospital",
            "hospital_name",
            "category",
            "batch",
            "quantity",
            "price",
            "tax_rate",
            "expiry_date",
            "status",
            "generic_name",
            "unit",
            "reorder_level",
            "supplier",
            "supplier_name",
            "drug_schedule",
            "hsn_code",
            "mrp",
            "manufacturer",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_hsn_code(self, value):
        value = (value or "").strip()
        if value and not (value.isdigit() and len(value) in (4, 6, 8)):
            raise serializers.ValidationError("HSN code is 4, 6 or 8 digits.")
        return value

    def validate_mrp(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("MRP cannot be negative.")
        return value

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Medicine name is required."
            )
        return value.strip()

    def validate_quantity(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError(
                "Quantity cannot be negative."
            )
        return value

    def validate_tax_rate(self, value):
        if value is None or value < 0 or value > 100:
            raise serializers.ValidationError("GST must be between 0 and 100 %.")
        return value

    def validate(self, attrs):
        """Enforce hospital scoping.

        When the request is scoped with ``?hospital=<id>`` the
        medicine may only be assigned to that hospital and may not
        be moved to a different one.
        """
        scoped = self.context.get("scoped_hospital")
        instance = self.instance

        hospital = attrs.get("hospital")
        if hospital is None and instance is not None:
            hospital = instance.hospital

        if scoped is not None:
            if hospital is not None and hospital.pk != scoped.pk:
                raise serializers.ValidationError(
                    {
                        "hospital": (
                            "Medicine does not belong to the "
                            "selected hospital."
                        )
                    }
                )
            if hospital is None:
                attrs["hospital"] = scoped
                hospital = scoped

        supplier = attrs.get("supplier")
        if supplier is not None and hospital is not None and supplier.hospital_id != hospital.pk:
            raise serializers.ValidationError(
                {"supplier": "Supplier does not belong to the selected hospital."}
            )

        # P1-10: a medicine is never sold above its printed MRP.
        price = attrs.get("price", getattr(instance, "price", None))
        mrp = attrs.get("mrp", getattr(instance, "mrp", None))
        if price is not None and mrp is not None and price > mrp:
            raise serializers.ValidationError({"price": f"Selling price cannot be above the MRP ({mrp})."})

        return attrs


class SaleSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True
    )
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )
    returned_quantity = serializers.SerializerMethodField()
    # F9: the patient bill this sale is charged on ("" for walk-in sales).
    invoice_number = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "medicine",
            "medicine_name",
            "hospital",
            "hospital_name",
            "patient_name",
            "quantity",
            "unit_price",
            "total",
            "prescription",
            "prescription_item",
            "substituted_for",
            "substitution_reason",
            "dispensed_by",
            "returned_quantity",
            "invoice_number",
            "created_at",
        ]
        # Price comes from the medicine record, never from the client.
        read_only_fields = ["id", "unit_price", "total", "prescription_item", "substituted_for",
                            "substitution_reason", "dispensed_by", "returned_quantity", "created_at"]
        extra_kwargs = {
            "hospital": {"required": False},
            "unit_price": {"required": False},
        }

    def get_invoice_number(self, obj) -> str:
        item = getattr(obj, "invoice_item", None) if obj.pk else None
        return item.invoice.invoice_number if item is not None else ""

    def validate_patient_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
                "Patient name is required."
            )
        return value.strip()

    def validate_quantity(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than 0."
            )
        return value

    def validate(self, attrs):
        instance = self.instance

        medicine = attrs.get("medicine")
        if medicine is None and instance is not None:
            medicine = instance.medicine

        if medicine is None:
            raise serializers.ValidationError(
                {"medicine": "A medicine is required."}
            )

        hospital = attrs.get("hospital")
        if hospital is None and instance is not None:
            hospital = instance.hospital
        if hospital is None and medicine.hospital_id:
            hospital = medicine.hospital
            attrs["hospital"] = hospital

        if hospital is None:
            raise serializers.ValidationError(
                {"hospital": "A hospital is required."}
            )

        # A sale can never draw stock from another hospital.
        if (
            medicine.hospital_id
            and medicine.hospital_id != hospital.pk
        ):
            raise serializers.ValidationError(
                {
                    "medicine": (
                        "Medicine does not belong to the "
                        "selected hospital."
                    )
                }
            )

        unit_price = attrs.get("unit_price")
        if unit_price is None:
            unit_price = medicine.price
        if unit_price < 0:
            raise serializers.ValidationError(
                {"unit_price": "Unit price cannot be negative."}
            )

        # Friendly pre-check. The authoritative, atomic stock
        # check runs server-side inside the view transaction.
        quantity = attrs.get("quantity")
        if (
            instance is None
            and quantity is not None
            and quantity > medicine.quantity
        ):
            raise serializers.ValidationError(
                {
                    "quantity": (
                        "Insufficient stock. "
                        f"Available: {medicine.quantity}."
                    )
                }
            )

        return attrs

    def get_returned_quantity(self, obj) -> int:
        # Views annotate this; fall back to a query for single objects.
        annotated = getattr(obj, "returned_total", None)
        if annotated is not None:
            return annotated
        return sum(r.quantity for r in obj.returns.all())

    def create(self, validated_data):
        medicine = validated_data["medicine"]
        unit_price = validated_data.get("unit_price")
        if unit_price is None:
            unit_price = medicine.price
        validated_data["unit_price"] = unit_price
        validated_data["total"] = (
            Decimal(validated_data["quantity"]) * Decimal(unit_price)
        ).quantize(Decimal("0.01"))
        return super().create(validated_data)

class SaleReturnSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="sale.medicine.name", read_only=True)
    patient_name = serializers.CharField(source="sale.patient_name", read_only=True)

    class Meta:
        model = SaleReturn
        fields = ["id", "sale", "medicine_name", "patient_name", "quantity", "restocked", "reason", "refund_amount",
                  "returned_by", "created_at"]
        read_only_fields = fields


class SaleReturnRequestSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=255)
    # True only when the pharmacist confirms the medicine is sealed and fit to reissue.
    restock = serializers.BooleanField(default=False)


class DispenseLineSerializer(serializers.Serializer):
    item = serializers.IntegerField(min_value=1)
    medicine = serializers.IntegerField(min_value=1)
    # Used only with partial=True; otherwise the whole remaining quantity is issued.
    quantity = serializers.IntegerField(min_value=1, required=False)
    # Required when ``medicine`` is a same-salt substitute for the prescribed brand.
    substitute_reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class DispensePrescriptionSerializer(serializers.Serializer):
    """Request body for dispensing a whole prescription at once."""

    prescription = serializers.IntegerField(min_value=1)
    lines = DispenseLineSerializer(many=True)
    # True to issue only some lines or smaller quantities now and the rest later.
    partial = serializers.BooleanField(required=False, default=False)
