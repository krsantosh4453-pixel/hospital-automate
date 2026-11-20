from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AdvanceAccountViewSet,
    InvoiceViewSet,
    InvoiceItemViewSet,
    PaymentViewSet,
    InsuranceClaimViewSet,
    ServicePriceViewSet,
)

router = DefaultRouter()

router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"invoice-items", InvoiceItemViewSet, basename="invoice-item")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"advances", AdvanceAccountViewSet, basename="advance")
router.register(r"insurance-claims", InsuranceClaimViewSet, basename="insurance-claim")
router.register(r"price-list", ServicePriceViewSet, basename="service-price")

urlpatterns = [
    path("", include(router.urls)),
]