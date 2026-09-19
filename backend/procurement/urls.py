from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GoodsReceiptItemViewSet,
    GoodsReceiptViewSet,
    PurchaseItemViewSet,
    PurchaseOrderViewSet,
    StockTransactionViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register(r"suppliers", SupplierViewSet, basename="supplier")
router.register(r"purchases", PurchaseOrderViewSet, basename="purchase")
router.register(r"purchase-items", PurchaseItemViewSet, basename="purchase-item")
router.register(r"grns", GoodsReceiptViewSet, basename="grn")
router.register(r"grn-items", GoodsReceiptItemViewSet, basename="grn-item")
router.register(
    r"stock-transactions",
    StockTransactionViewSet,
    basename="stock-transaction",
)

urlpatterns = [
    path("", include(router.urls)),
]
