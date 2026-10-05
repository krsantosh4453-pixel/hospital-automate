from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from hospital.models import Hospital

from .models import (
    Supplier,
    PurchaseOrder,
    PurchaseItem,
    GoodsReceipt,
    GoodsReceiptItem,
    StockTransaction,
)
from .serializers import (
    SupplierSerializer,
    PurchaseOrderSerializer,
    PurchaseItemSerializer,
    GoodsReceiptSerializer,
    GoodsReceiptItemSerializer,
    StockTransactionSerializer,
    GoodsReceiptReceiveSerializer,
)
from .services import receive_purchase
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsInventoryStaff


class SupplierViewSet(HospitalScopedViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsInventoryStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        return qs.select_related("hospital")


class PurchaseOrderViewSet(HospitalScopedViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsInventoryStaff]

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.select_related(
            "hospital",
            "supplier",
        ).prefetch_related("items__medicine")

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        return qs

    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request, pk=None):
        """Atomically receive stock against this purchase order (GRN).

        ``reference`` is REQUIRED: it is the idempotency key that stops a
        replayed receipt from incrementing stock twice.

        Body::

            {
              "reference": "INV-001",        # required (idempotency key)
              "receipt_date": "2026-09-14",  # optional
              "received_by": "Store Keeper", # optional
              "note": "",                    # optional
              "items": [
                {"purchase_item": 1, "quantity_received": 10,
                 "unit_cost": "5.00", "batch": "B1"}
              ]
            }
        """
        purchase = self.get_object()

        serializer = GoodsReceiptReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receipt = receive_purchase(
            purchase=purchase,
            payload=serializer.validated_data,
            scoped_hospital=purchase.hospital,
        )

        return Response(
            GoodsReceiptSerializer(receipt).data,
            status=status.HTTP_201_CREATED,
        )


class PurchaseItemViewSet(HospitalScopedViewSet):
    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsInventoryStaff]

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.select_related(
            "purchase",
            "medicine",
        )

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(purchase__hospital_id=hospital_id)

        purchase_id = self.request.query_params.get("purchase")
        if purchase_id:
            qs = qs.filter(purchase_id=purchase_id)

        return qs


class GoodsReceiptViewSet(HospitalScopedViewSet):
    """GRNs are append-only: only list/retrieve are exposed."""

    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsInventoryStaff]

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.select_related(
            "hospital",
            "supplier",
            "purchase",
        ).prefetch_related("items__medicine")

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        purchase_id = self.request.query_params.get("purchase")
        if purchase_id:
            qs = qs.filter(purchase_id=purchase_id)

        return qs


class GoodsReceiptItemViewSet(
    HospitalScopedViewSet, viewsets.ReadOnlyModelViewSet
):
    """Individual GRN lines are append-only: read-only access."""

    queryset = GoodsReceiptItem.objects.all()
    serializer_class = GoodsReceiptItemSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsInventoryStaff]

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.select_related(
            "medicine",
            "goods_receipt",
        )

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(goods_receipt__hospital_id=hospital_id)

        goods_receipt_id = self.request.query_params.get("goods_receipt")
        if goods_receipt_id:
            qs = qs.filter(goods_receipt_id=goods_receipt_id)

        return qs


class StockTransactionViewSet(
    HospitalScopedViewSet, viewsets.ReadOnlyModelViewSet
):
    """The stock ledger is append-only: read-only access."""

    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsInventoryStaff]

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.select_related(
            "medicine",
            "hospital",
        )

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            qs = qs.filter(medicine_id=medicine_id)

        return qs
