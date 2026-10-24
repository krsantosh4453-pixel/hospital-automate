from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

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
    StockAdjustmentSerializer,
)
from .services import receive_purchase, adjust_stock
from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    IsAdmin, IsHospitalManager, IsInventoryStaff, 
    get_user_hospital_ids, get_user_staff_profile, get_user_roles
)
from users.models import StaffRole


class ReadOnlyScopePermission(BasePermission):
    """
    Permission for read-only viewsets that only allow safe methods.
    All write methods (POST, PUT, PATCH, DELETE) are denied with 405.
    """

    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return False
        # For safe methods, delegate to RequiresHospitalScope logic
        return RequiresHospitalScope().has_permission(request, view)


class RequiresHospitalScope(BasePermission):
    """
    Permission that requires explicit hospital scoping via ?hospital= query param
    for detail views and write operations (except list-create). List views are 
    allowed without scoping (they return empty results via queryset filtering).
    
    Anonymous users are always rejected.
    
    For authenticated users, requires one of: Admin, HospitalManager, InventoryStaff
    """

    def has_permission(self, request, view):
        # Check if this is a detail view (has pk in URL)
        is_detail = view.kwargs.get("pk") is not None
        is_write = request.method not in SAFE_METHODS
        is_list_create = not is_detail and request.method == "POST"

        # Procurement data is never public.
        if not request.user or not request.user.is_authenticated:
            return False

        # Authenticated users: check role
        staff_profile = get_user_staff_profile(request.user)
        if not staff_profile or not staff_profile.is_active_staff:
            return False

        user_roles = get_user_roles(request.user)
        allowed_roles = {StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER, StaffRole.INVENTORY_STAFF}
        if not any(role in user_roles for role in allowed_roles):
            return False

        # For detail views and write operations (except list-create), require hospital param
        if is_detail or (is_write and not is_list_create):
            hospital_id = request.query_params.get("hospital")
            if not hospital_id:
                return False
            # Check if user has access to the requested hospital
            try:
                hospital_id = int(hospital_id)
            except (ValueError, TypeError):
                return False
            return hospital_id in get_user_hospital_ids(request.user)

        # List views (safe methods) and list-create (POST to list) are allowed without explicit scoping
        # Serializer validation will handle hospital scoping for create
        return True


class SupplierViewSet(HospitalScopedViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [RequiresHospitalScope]

    def get_queryset(self):
        # Anonymous users get empty queryset
        if not self.request.user or not self.request.user.is_authenticated:
            return Supplier.objects.none()
        
        # Require explicit hospital scoping via ?hospital= param
        hospital_id = self.request.query_params.get("hospital")
        if not hospital_id:
            return Supplier.objects.none()
        
        qs = super().get_queryset()
        qs = qs.filter(hospital_id=hospital_id)
        return qs.select_related("hospital")

    def get_object(self):
        # For detail views, get object without hospital filter to allow proper permission checks
        queryset = self.filter_queryset(self.get_queryset().model.objects.all())
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(queryset, pk=pk)
        
        # Check if the object's hospital matches the scoped hospital (if provided)
        scoped_hospital_id = self.request.query_params.get("hospital")
        if scoped_hospital_id and obj.hospital_id != int(scoped_hospital_id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Object does not belong to the selected hospital.")
        
        # Check object-level permissions
        self.check_object_permissions(self.request, obj)
        return obj


class PurchaseOrderViewSet(HospitalScopedViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [RequiresHospitalScope]

    def get_queryset(self):
        # Anonymous users get empty queryset
        if not self.request.user or not self.request.user.is_authenticated:
            return PurchaseOrder.objects.none()
        
        # Require explicit hospital scoping via ?hospital= param
        hospital_id = self.request.query_params.get("hospital")
        if not hospital_id:
            return PurchaseOrder.objects.none()
        
        qs = super().get_queryset()

        qs = qs.select_related(
            "hospital",
            "supplier",
        ).prefetch_related("items__medicine")

        qs = qs.filter(hospital_id=hospital_id)

        return qs

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset().model.objects.all())
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(queryset, pk=pk)
        
        scoped_hospital_id = self.request.query_params.get("hospital")
        if scoped_hospital_id and obj.hospital_id != int(scoped_hospital_id):
            raise PermissionDenied("Object does not belong to the selected hospital.")
        
        self.check_object_permissions(self.request, obj)
        return obj

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
    permission_classes = [RequiresHospitalScope]

    def get_queryset(self):
        # Anonymous users get empty queryset
        if not self.request.user or not self.request.user.is_authenticated:
            return PurchaseItem.objects.none()
        
        # Require explicit hospital scoping via ?hospital= param
        hospital_id = self.request.query_params.get("hospital")
        if not hospital_id:
            return PurchaseItem.objects.none()
        
        qs = super().get_queryset()

        qs = qs.select_related(
            "purchase",
            "medicine",
        )

        qs = qs.filter(purchase__hospital_id=hospital_id)

        purchase_id = self.request.query_params.get("purchase")
        if purchase_id:
            qs = qs.filter(purchase_id=purchase_id)

        return qs

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset().model.objects.all())
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(queryset.select_related("purchase"), pk=pk)
        
        scoped_hospital_id = self.request.query_params.get("hospital")
        if scoped_hospital_id and obj.purchase.hospital_id != int(scoped_hospital_id):
            raise PermissionDenied("Object does not belong to the selected hospital.")
        
        self.check_object_permissions(self.request, obj)
        return obj


class GoodsReceiptViewSet(
    viewsets.ReadOnlyModelViewSet, HospitalScopedViewSet
):
    """GRNs are append-only: only list/retrieve are exposed."""

    queryset = GoodsReceipt.objects.all()
    serializer_class = GoodsReceiptSerializer
    permission_classes = [ReadOnlyScopePermission]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        # Anonymous users get empty queryset
        if not self.request.user or not self.request.user.is_authenticated:
            return GoodsReceipt.objects.none()
        
        # Require explicit hospital scoping via ?hospital= param
        hospital_id = self.request.query_params.get("hospital")
        if not hospital_id:
            return GoodsReceipt.objects.none()
        
        qs = super().get_queryset()

        qs = qs.select_related(
            "hospital",
            "supplier",
            "purchase",
        ).prefetch_related("items__medicine")

        qs = qs.filter(hospital_id=hospital_id)

        purchase_id = self.request.query_params.get("purchase")
        if purchase_id:
            qs = qs.filter(purchase_id=purchase_id)

        return qs

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset().model.objects.all())
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(queryset, pk=pk)
        
        scoped_hospital_id = self.request.query_params.get("hospital")
        if scoped_hospital_id and obj.hospital_id != int(scoped_hospital_id):
            raise PermissionDenied("Object does not belong to the selected hospital.")
        
        self.check_object_permissions(self.request, obj)
        return obj

    # Explicitly disable create - GRNs are append-only via receive action
    create = None


class GoodsReceiptItemViewSet(
    viewsets.ReadOnlyModelViewSet, HospitalScopedViewSet
):
    """Individual GRN lines are append-only: read-only access."""

    queryset = GoodsReceiptItem.objects.all()
    serializer_class = GoodsReceiptItemSerializer
    permission_classes = [ReadOnlyScopePermission]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        # Anonymous users get empty queryset
        if not self.request.user or not self.request.user.is_authenticated:
            return GoodsReceiptItem.objects.none()
        
        # Require explicit hospital scoping via ?hospital= param
        hospital_id = self.request.query_params.get("hospital")
        if not hospital_id:
            return GoodsReceiptItem.objects.none()
        
        qs = super().get_queryset()

        qs = qs.select_related(
            "medicine",
            "goods_receipt",
        )

        qs = qs.filter(goods_receipt__hospital_id=hospital_id)

        goods_receipt_id = self.request.query_params.get("goods_receipt")
        if goods_receipt_id:
            qs = qs.filter(goods_receipt_id=goods_receipt_id)

        return qs

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset().model.objects.all())
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(queryset.select_related("goods_receipt"), pk=pk)
        
        scoped_hospital_id = self.request.query_params.get("hospital")
        if scoped_hospital_id and obj.goods_receipt.hospital_id != int(scoped_hospital_id):
            raise PermissionDenied("Object does not belong to the selected hospital.")
        
        self.check_object_permissions(self.request, obj)
        return obj

    # Explicitly disable create
    create = None


class StockTransactionViewSet(
    viewsets.ReadOnlyModelViewSet, HospitalScopedViewSet
):
    """The stock ledger is append-only: read-only access."""

    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [ReadOnlyScopePermission]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        # Anonymous users get empty queryset
        if not self.request.user or not self.request.user.is_authenticated:
            return StockTransaction.objects.none()
        
        # Require explicit hospital scoping via ?hospital= param
        hospital_id = self.request.query_params.get("hospital")
        if not hospital_id:
            return StockTransaction.objects.none()
        
        qs = super().get_queryset()

        qs = qs.select_related(
            "medicine",
            "hospital",
        )

        qs = qs.filter(hospital_id=hospital_id)

        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            qs = qs.filter(medicine_id=medicine_id)

        return qs

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset().model.objects.all())
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(queryset, pk=pk)
        
        scoped_hospital_id = self.request.query_params.get("hospital")
        if scoped_hospital_id and obj.hospital_id != int(scoped_hospital_id):
            raise PermissionDenied("Object does not belong to the selected hospital.")
        
        self.check_object_permissions(self.request, obj)
        return obj

    # Explicitly disable create
    create = None

    @action(detail=False, methods=["post"], url_path="adjust")
    def adjust(self, request):
        """Manual stock adjustment (add/remove).

        Body::
            {
              "medicine": 1,
              "type": "add",           # "add" or "remove"
              "quantity": 10,
              "reason": "Stock correction",
              "reference": "ADJ-001"   # optional
            }
        """
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        medicine = serializer.validated_data["medicine"]
        hospital = medicine.hospital

        scoped_hospital = request.query_params.get("hospital")
        if scoped_hospital:
            from hospital.models import Hospital
            scoped_hospital = Hospital.objects.filter(pk=scoped_hospital).first()

        try:
            updated_medicine = adjust_stock(
                medicine=medicine,
                hospital=hospital,
                payload=serializer.validated_data,
                scoped_hospital=scoped_hospital,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            StockTransactionSerializer(
                updated_medicine.stock_transactions.first()
            ).data,
            status=status.HTTP_201_CREATED,
        )
