from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicineViewSet, SaleViewSet

router = DefaultRouter()
router.register(r"pharmacy", MedicineViewSet, basename="pharmacy")
router.register(r"sales", SaleViewSet, basename="pharmacy-sale")

urlpatterns = [
    path("", include(router.urls)),
]