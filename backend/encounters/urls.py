from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    VisitViewSet,
    QueueTokenViewSet,
    DoctorScheduleViewSet,
)

router = DefaultRouter()

router.register(r"visits", VisitViewSet, basename="visit")
router.register(r"queue-tokens", QueueTokenViewSet, basename="queue-token")
router.register(r"doctor-schedules", DoctorScheduleViewSet, basename="doctor-schedule")

urlpatterns = [
    path("", include(router.urls)),
]