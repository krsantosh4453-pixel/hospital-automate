from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    HospitalViewSet,
    DepartmentViewSet,
    WardViewSet,
    RoomViewSet,
    BedViewSet,
    HospitalDirectoryView,
)

router = DefaultRouter()

router.register(r"hospitals", HospitalViewSet, basename="hospital")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"wards", WardViewSet, basename="ward")
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"beds", BedViewSet, basename="bed")

urlpatterns = [
    path("directory/", HospitalDirectoryView.as_view(), name="hospital-directory"),
    path("", include(router.urls)),
]