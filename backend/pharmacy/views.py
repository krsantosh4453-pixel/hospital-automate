from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework import serializers, viewsets

from hospital.models import Hospital

from .models import Medicine, Sale
from .serializers import MedicineSerializer, SaleSerializer


class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer

    def get_queryset(self):
        queryset = Medicine.objects.select_related("hospital")

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            context["scoped_hospital"] = (
                Hospital.objects.filter(pk=hospital_id).first()
            )

        return context


class SaleViewSet(viewsets.ModelViewSet):
    """Pharmacy sales.

    Sales are append-only: only list/create/retrieve are exposed
    because existing workflows never mutate a completed sale.
    """

    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = Sale.objects.select_related(
            "medicine",
            "hospital",
            "prescription",
        )

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        prescription_id = self.request.query_params.get("prescription")
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)

        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        medicine = serializer.validated_data["medicine"]
        quantity = serializer.validated_data["quantity"]

        hospital = (
            serializer.validated_data.get("hospital")
            or medicine.hospital
        )

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

        # Atomic, DB-level guard: the UPDATE only matches while
        # enough stock exists, so concurrent sales can never
        # oversell or drive quantity negative. Works on SQLite.
        updated = Medicine.objects.filter(
            pk=medicine.pk,
            quantity__gte=quantity,
        ).update(quantity=F("quantity") - quantity)

        if not updated:
            medicine.refresh_from_db(fields=["quantity"])
            raise serializers.ValidationError(
                {
                    "quantity": (
                        "Insufficient stock. "
                        f"Available: {medicine.quantity}."
                    )
                }
            )

        medicine.refresh_from_db(fields=["quantity"])

        unit_price = serializer.validated_data.get("unit_price")
        if unit_price is None:
            unit_price = medicine.price

        total = (
            Decimal(quantity) * Decimal(unit_price)
        ).quantize(Decimal("0.01"))

        # Deduct stock first: rolled back automatically if the
        # sale insert below fails.
        serializer.save(
            hospital=hospital,
            unit_price=unit_price,
            total=total,
        )