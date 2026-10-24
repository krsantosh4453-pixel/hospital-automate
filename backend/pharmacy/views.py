from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework import serializers, viewsets

from hospital.models import Hospital

from .models import Medicine, Sale
from .serializers import MedicineSerializer, SaleSerializer
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsPharmacist


class MedicineViewSet(HospitalScopedViewSet):
    queryset = Medicine.objects.select_related("hospital")
    serializer_class = MedicineSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsPharmacist]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        # Search filter
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Category filter
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        # Status filter
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            context["scoped_hospital"] = (
                Hospital.objects.filter(pk=hospital_id).first()
            )

        return context


class SaleViewSet(HospitalScopedViewSet):
    """Pharmacy sales.

    Sales are append-only: only list/create/retrieve are exposed
    because existing workflows never mutate a completed sale.
    """

    queryset = Sale.objects.select_related(
        "medicine",
        "hospital",
        "prescription",
    )
    serializer_class = SaleSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsPharmacist]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        prescription_id = self.request.query_params.get("prescription")
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)

        # Date range filter
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

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