from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompounderViewSet

router = DefaultRouter()
router.register(r"compounder", CompounderViewSet, basename="compounder")

urlpatterns = [
    path("", include(router.urls)),
]