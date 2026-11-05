from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from audit.services import record_audit
from billing import pharmacy_charges
from procurement.models import StockTransaction
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from clinical.models import Prescription

from hospital.models import Hospital

from . import dispensing
from .models import Medicine, Sale
from .serializers import (
    DispensePrescriptionSerializer,
    MedicineSerializer,
    SaleReturnRequestSerializer,
    SaleReturnSerializer,
    SaleSerializer,
)
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
        "invoice_item__invoice",
    )
    serializer_class = SaleSerializer
    # Dispensing: pharmacist and compounder.
    permission_classes = [IsAdmin | IsHospitalManager | IsPharmacist | IsCompounder]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset().annotate(returned_total=Coalesce(Sum("returns__quantity"), 0))

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
        if prescription is not None:
            dispensing.check_dispensable(prescription)

        # Deduct stock first: rolled back automatically if the
        # sale insert below fails.
        unit_price, total = self._deduct_stock(medicine, quantity)
        sale = serializer.save(
            hospital=hospital,
            unit_price=unit_price,
            total=total,
            dispensed_by=self.request.user,
        )
        self._record_sale(sale)
        # A sale against a prescription means it has been dispensed. Items are
        # free text, so the first sale marks the whole prescription.
        if prescription is not None and prescription.dispensed_at is None:
            self._mark_dispensed(prescription)
        if prescription is not None:
            self._bill(prescription, [sale])

    def _bill(self, prescription, sales):
        """F9: put the sales on the patient's medicine bill, in this transaction."""
        invoice = pharmacy_charges.post_sales(prescription, sales)
        if invoice is not None:
            record_audit(self.request, "billing.invoice.pharmacy_charges", invoice, hospital=invoice.hospital_id,
                         details={"prescription": prescription.pk, "sales": [sale.pk for sale in sales],
                                  "total": str(invoice.total)})
        return invoice

    @action(detail=False, methods=["post"], url_path="dispense-prescription")
    @transaction.atomic
    def dispense_prescription(self, request):
        """Dispenses a prescription in one transaction: every line, or none.

        Each line names a prescription item and the stock batch to issue it
        from. By default every medicine still owed is issued in full. With
        ``partial: true`` some lines, or smaller quantities, can be issued now
        and the rest later (F5/partial). A same-salt brand may replace the
        prescribed one with a reason, by a pharmacist only (F8). The
        prescription row is locked, so two counters cannot issue the same
        medicine twice.
        """
        payload = DispensePrescriptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        prescription = get_object_or_404(
            Prescription.objects.select_for_update().filter(hospital_id__in=get_user_hospital_ids(request.user)),
            pk=payload.validated_data["prescription"],
        )
        if prescription.dispensed_at is not None:
            return Response({"detail": "This prescription has already been dispensed."},
                            status=status.HTTP_409_CONFLICT)
        dispensing.check_dispensable(prescription)
        lines = payload.validated_data["lines"]
        partial = payload.validated_data["partial"]
        items = {item.pk: item for item in prescription.items.all()}
        if not items:
            raise serializers.ValidationError({"prescription": "This prescription has no medicines to dispense."})
        remaining = dispensing.remaining_quantities(prescription, items)
        self._check_lines(lines, items, remaining, partial)

        medicines = Medicine.objects.in_bulk([line["medicine"] for line in lines])
        hospital = prescription.hospital
        may_substitute = IsPharmacist().has_permission(request, self)
        sales = []
        for line in lines:
            item = items[line["item"]]
            medicine = medicines.get(line["medicine"])
            if medicine is None:
                raise serializers.ValidationError({"lines": f"Stock for {item.name} was not found."})
            self._check_batch(medicine, hospital)
            substituted_for = dispensing.substitution_for(item, medicine, line["substitute_reason"], may_substitute)
            quantity = line.get("quantity") if partial else remaining[item.pk]
            unit_price, total = self._deduct_stock(medicine, quantity)
            sale = Sale.objects.create(
                medicine=medicine, hospital=hospital, patient_name=prescription.patient.name, quantity=quantity,
                unit_price=unit_price, total=total, prescription=prescription, prescription_item=item,
                substituted_for=substituted_for, substitution_reason=line["substitute_reason"].strip() if substituted_for else "",
                dispensed_by=request.user,
            )
            self._record_sale(sale)
            if substituted_for:
                record_audit(request, "pharmacy.sale.substituted", sale, hospital=hospital.pk,
                             details={"prescribed": substituted_for, "given": medicine.name,
                                      "reason": sale.substitution_reason})
            sales.append(sale)

        left = dispensing.remaining_quantities(prescription, items)
        if any(left.values()):
            prescription.status = dispensing.PARTIALLY_DISPENSED
            prescription.save(update_fields=["status"])
        else:
            prescription.status, prescription.dispensed_at = "Dispensed", timezone.now()
            prescription.save(update_fields=["status", "dispensed_at"])
        invoice = self._bill(prescription, sales)

        return Response(
            {"prescription": prescription.pk, "status": prescription.status,
             "remaining": {str(pk): qty for pk, qty in left.items()},
             "sales": SaleSerializer(sales, many=True).data,
             "invoice": pharmacy_charges.bill_summary(invoice)},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _check_lines(lines, items, remaining, partial):
        line_items = [line["item"] for line in lines]
        if len(set(line_items)) != len(line_items) or not set(line_items) <= set(items):
            raise serializers.ValidationError({"lines": "Each line must be a different medicine on this prescription."})
        owed = {pk for pk, qty in remaining.items() if qty > 0}
        if not partial:
            if set(line_items) != owed:
                raise serializers.ValidationError(
                    {"lines": "Give exactly one stock batch for every medicine still to dispense."})
            return
        if not lines:
            raise serializers.ValidationError({"lines": "Choose at least one medicine to dispense."})
        for line in lines:
            item = items[line["item"]]
            quantity = line.get("quantity")
            if quantity is None:
                raise serializers.ValidationError({"lines": f"Give the quantity of {item.name} to dispense now."})
            if quantity > remaining[item.pk]:
                raise serializers.ValidationError(
                    {"lines": f"Only {remaining[item.pk]} of {item.name} is still to be dispensed."})

    @action(detail=True, methods=["post"], url_path="return", permission_classes=[IsAdmin | IsHospitalManager | IsPharmacist])
    @transaction.atomic
    def return_sale(self, request, pk=None):
        """
        {quantity, reason, restock}: medicine handed back by the patient (F5).
        A billed sale is also taken off its bill, refunding any over-payment (F9).
        """
        sale = self.get_object()
        body = SaleReturnRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        returned = dispensing.record_return(sale, body.validated_data["quantity"], body.validated_data["reason"],
                                            body.validated_data["restock"], user=request.user)
        record_audit(request, "pharmacy.sale.returned", sale, hospital=sale.hospital_id,
                     details={"quantity": returned.quantity, "restocked": returned.restocked,
                              "refund": str(returned.refund_amount), "reason": returned.reason})
        billed = pharmacy_charges.apply_return(returned, user=request.user)
        data = SaleReturnSerializer(returned).data
        data["invoice"] = None
        data["invoice_refund"] = None
        if billed is not None:
            invoice, refund = billed["invoice"], billed["refund"]
            record_audit(request, "billing.invoice.pharmacy_return", invoice, hospital=invoice.hospital_id,
                         details={"return": returned.pk, "sale": sale.pk, "quantity": returned.quantity,
                                  "refund": str(refund.amount) if refund else "0.00",
                                  "discount_capped": billed["discount_capped"]})
            data["invoice"] = pharmacy_charges.bill_summary(invoice)
            data["invoice_refund"] = str(refund.amount) if refund else None
        return Response(data, status=status.HTTP_201_CREATED)
