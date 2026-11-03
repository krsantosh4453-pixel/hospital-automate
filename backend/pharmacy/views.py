from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from audit.services import record_audit
from procurement.models import StockTransaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from clinical.models import Prescription

from hospital.models import Hospital

from .models import Medicine, Sale
from .serializers import DispensePrescriptionSerializer, MedicineSerializer, SaleSerializer
from users.viewsets import HospitalScopedViewSet
from users.permissions import get_user_hospital_ids, IsAdmin, IsCompounder, IsHospitalManager, IsInventoryStaff, IsPharmacist
from config.hospital_time import hospital_today


class MedicineViewSet(HospitalScopedViewSet):
    queryset = Medicine.objects.select_related("hospital")
    serializer_class = MedicineSerializer
    # Medicine stock: pharmacy (pharmacist, compounder) and the store.
    permission_classes = [IsAdmin | IsHospitalManager | IsPharmacist | IsCompounder | IsInventoryStaff]

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

    def _ledger(self, medicine, kind, quantity, reason):
        if quantity:
            StockTransaction.objects.create(
                medicine=medicine,
                hospital_id=medicine.hospital_id,
                transaction_type=kind,
                quantity=quantity,
                reason=reason,
                reference=f"MED-{medicine.pk}",
            )

    @transaction.atomic
    def perform_create(self, serializer):
        super().perform_create(serializer)
        medicine = serializer.instance
        if medicine.hospital_id:
            self._ledger(medicine, StockTransaction.TYPE_IN, medicine.quantity, "Opening stock")

    @transaction.atomic
    def perform_update(self, serializer):
        before = Medicine.objects.select_for_update().get(pk=serializer.instance.pk).quantity
        super().perform_update(serializer)
        medicine = serializer.instance
        delta = medicine.quantity - before
        if delta and medicine.hospital_id:
            reason = self.request.data.get("adjustment_reason") or "Manual stock correction"
            self._ledger(medicine, StockTransaction.TYPE_ADJUST, abs(delta),
                         f"{reason} ({'+' if delta > 0 else '-'}{abs(delta)})")

    def perform_destroy(self, instance):
        if instance.sales.exists() or instance.stock_transactions.exists():
            raise serializers.ValidationError(
                "This medicine has stock history and cannot be deleted; set its status to Discontinued."
            )
        super().perform_destroy(instance)


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
    # Dispensing: pharmacist and compounder.
    permission_classes = [IsAdmin | IsHospitalManager | IsPharmacist | IsCompounder]
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

    @staticmethod
    def _check_batch(medicine, hospital):
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

        if medicine.expiry_date and medicine.expiry_date < hospital_today():
            raise serializers.ValidationError(
                {"medicine": f"This batch expired on {medicine.expiry_date}; it cannot be dispensed."}
            )

    @staticmethod
    def _deduct_stock(medicine, quantity):
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
                        f"Insufficient stock of {medicine.name}. "
                        f"Available: {medicine.quantity}."
                    )
                }
            )

        medicine.refresh_from_db(fields=["quantity"])
        return (
            Decimal(medicine.price),
            (Decimal(quantity) * Decimal(medicine.price)).quantize(Decimal("0.01")),
        )

    def _record_sale(self, sale):
        # Every stock change is mirrored in the append-only ledger.
        StockTransaction.objects.create(
            medicine=sale.medicine,
            hospital=sale.hospital,
            transaction_type=StockTransaction.TYPE_OUT,
            quantity=sale.quantity,
            reason="Pharmacy sale",
            reference=f"SALE-{sale.pk}",
        )
        record_audit(self.request, "pharmacy.sale.create", sale, hospital=sale.hospital_id,
                     details={"medicine": sale.medicine_id, "quantity": sale.quantity})

    @staticmethod
    def _mark_dispensed(prescription):
        """Marks the prescription dispensed; False if it already was."""
        return bool(
            type(prescription).objects.filter(pk=prescription.pk, dispensed_at__isnull=True).update(
                status="Dispensed", dispensed_at=timezone.now()
            )
        )

    @transaction.atomic
    def perform_create(self, serializer):
        self._check_tenancy(serializer.validated_data)
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

        self._check_batch(medicine, hospital)
        prescription = serializer.validated_data.get("prescription")
        if prescription is not None and prescription.hospital_id != hospital.pk:
            raise serializers.ValidationError({"prescription": "Prescription is from another hospital."})

        # Deduct stock first: rolled back automatically if the
        # sale insert below fails.
        unit_price, total = self._deduct_stock(medicine, quantity)
        sale = serializer.save(
            hospital=hospital,
            unit_price=unit_price,
            total=total,
        )
        self._record_sale(sale)
        # A sale against a prescription means it has been dispensed. Items are
        # free text, so the first sale marks the whole prescription.
        if prescription is not None and prescription.dispensed_at is None:
            self._mark_dispensed(prescription)

    @action(detail=False, methods=["post"], url_path="dispense-prescription")
    @transaction.atomic
    def dispense_prescription(self, request):
        """Dispenses every medicine on a prescription, or none of them.

        Each line names a prescription item and the stock batch to issue it
        from; the quantity is the prescribed one. Any failing line rolls back
        the stock already deducted for the others.
        """
        payload = DispensePrescriptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        prescription = get_object_or_404(
            Prescription.objects.filter(hospital_id__in=get_user_hospital_ids(request.user)),
            pk=payload.validated_data["prescription"],
        )
        lines = payload.validated_data["lines"]
        items = {item.pk: item for item in prescription.items.all()}
        if not items:
            raise serializers.ValidationError({"prescription": "This prescription has no medicines to dispense."})
        line_items = [line["item"] for line in lines]
        if sorted(line_items) != sorted(items):
            raise serializers.ValidationError(
                {"lines": "Give exactly one stock batch for every medicine on the prescription."}
            )

        medicines = Medicine.objects.in_bulk([line["medicine"] for line in lines])
        hospital = prescription.hospital
        # Marked first so a second, parallel dispense stops here; rolled back
        # with everything else if a line fails.
        if not self._mark_dispensed(prescription):
            return Response(
                {"detail": "This prescription has already been dispensed."},
                status=status.HTTP_409_CONFLICT,
            )

        sales = []
        for line in lines:
            item = items[line["item"]]
            medicine = medicines.get(line["medicine"])
            if medicine is None:
                raise serializers.ValidationError({"lines": f"Stock for {item.name} was not found."})
            if medicine.name.strip().lower() != item.name.strip().lower():
                raise serializers.ValidationError(
                    {"lines": f"{medicine.name} is not the prescribed medicine ({item.name})."}
                )
            self._check_batch(medicine, hospital)
            unit_price, total = self._deduct_stock(medicine, item.quantity)
            sale = Sale.objects.create(
                medicine=medicine,
                hospital=hospital,
                patient_name=prescription.patient.name,
                quantity=item.quantity,
                unit_price=unit_price,
                total=total,
                prescription=prescription,
            )
            self._record_sale(sale)
            sales.append(sale)

        return Response(
            {"prescription": prescription.pk, "sales": SaleSerializer(sales, many=True).data},
            status=status.HTTP_201_CREATED,
        )