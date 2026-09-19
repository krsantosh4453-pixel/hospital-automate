from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LabTestViewSet

router = DefaultRouter()
router.register(r"laboratory", LabTestViewSet, basename="laboratory")

urlpatterns = [
    path("", include(router.urls)),
]