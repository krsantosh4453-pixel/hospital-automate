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
from .permissions import IsProcurementWriteAuthenticated
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


class HospitalScopedMixin:
    """Object-level ``?hospital=<id>`` scoping with deny-by-default.

    Reads are only ever returned for a hospital the caller explicitly
    scopes to via ``?hospital=``. When the parameter is missing (or does
    not resolve to a real hospital) every list is empty and every detail
    lookup returns 404, so knowing a numeric ID alone can never expose
    another hospital's procurement record.

    Writes additionally require an authenticated user (see
    :class:`~procurement.permissions.IsProcurementWriteAuthenticated`).
    """

    permission_classes = [IsProcurementWriteAuthenticated]

    def get_scoped_hospital(self):
        hospital_id = self.request.query_params.get("hospital")
        if not hospital_id:
            return None
        return Hospital.objects.filter(pk=hospital_id).first()

    def scope_queryset(self, queryset, hospital_lookup="hospital_id"):
        """Filter ``queryset`` to the scoped hospital (deny by default)."""
        hospital = self.get_scoped_hospital()
        if hospital is None:
            return queryset.none()
        return queryset.filter(**{hospital_lookup: hospital.pk})

    def get_serializer_context(self):
        context = super().get_serializer_context()
        scoped = self.get_scoped_hospital()
        if scoped is not None:
            context["scoped_hospital"] = scoped
        return context


class SupplierViewSet(HospitalScopedMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

    def get_queryset(self):
        queryset = Supplier.objects.select_related("hospital")
        return self.scope_queryset(queryset, "hospital_id")


class PurchaseOrderViewSet(HospitalScopedMixin, viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer

    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related(
            "hospital",
            "supplier",
        ).prefetch_related("items__medicine")

        return self.scope_queryset(queryset, "hospital_id")

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
            scoped_hospital=self.get_scoped_hospital(),
        )

        return Response(
            GoodsReceiptSerializer(receipt).data,
            status=status.HTTP_201_CREATED,
        )


class PurchaseItemViewSet(HospitalScopedMixin, viewsets.ModelViewSet):
    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer

    def get_queryset(self):
        queryset = PurchaseItem.objects.select_related(
            "purchase",
            "medicine",
        )

        queryset = self.scope_queryset(queryset, "purchase__hospital_id")

        purchase_id = self.request.query_params.get("purchase")
        if purchase_id:
            queryset = queryset.filter(purchase_id=purchase_id)

        return queryset


class GoodsReceiptViewSet(HospitalScopedMixin, viewsets.ReadOnlyModelViewSet):
    """GRNs are append-only: only list/retrieve are exposed."""

    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer

    def get_queryset(self):
        queryset = GoodsReceipt.objects.select_related(
            "hospital",
            "supplier",
            "purchase",
        ).prefetch_related("items__medicine")

        queryset = self.scope_queryset(queryset, "hospital_id")

        purchase_id = self.request.query_params.get("purchase")
        if purchase_id:
            queryset = queryset.filter(purchase_id=purchase_id)

        return queryset


class GoodsReceiptItemViewSet(
    HospitalScopedMixin, viewsets.ReadOnlyModelViewSet
):
    """Individual GRN lines are append-only: read-only access."""

    queryset = GoodsReceiptItem.objects.all()
    serializer_class = GoodsReceiptItemSerializer

    def get_queryset(self):
        queryset = GoodsReceiptItem.objects.select_related(
            "medicine",
            "goods_receipt",
        )

        queryset = self.scope_queryset(
            queryset, "goods_receipt__hospital_id"
        )

        goods_receipt_id = self.request.query_params.get("goods_receipt")
        if goods_receipt_id:
            queryset = queryset.filter(goods_receipt_id=goods_receipt_id)

        return queryset


class StockTransactionViewSet(
    HospitalScopedMixin, viewsets.ReadOnlyModelViewSet
):
    """The stock ledger is append-only: read-only access."""

    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer

    def get_queryset(self):
        queryset = StockTransaction.objects.select_related(
            "medicine",
            "hospital",
        )

        queryset = self.scope_queryset(queryset, "hospital_id")

        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)

        return queryset
