from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BloodInventoryViewSet,
    BloodRequestViewSet,
    BloodTransactionViewSet,
)

router = DefaultRouter()

router.register(r"inventory", BloodInventoryViewSet, basename="blood-inventory")
router.register(r"requests", BloodRequestViewSet, basename="blood-request")
router.register(r"transactions", BloodTransactionViewSet, basename="blood-transaction")

urlpatterns = [
    path("", include(router.urls)),
]