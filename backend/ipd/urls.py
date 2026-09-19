from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AdmissionViewSet,
    BedAllocationViewSet,
    DischargePlanViewSet,
    DischargeSummaryViewSet,
    DischargeNoteViewSet,
)

router = DefaultRouter()

router.register(r"admissions", AdmissionViewSet, basename="admission")
router.register(r"bed-allocations", BedAllocationViewSet, basename="bed-allocation")
router.register(r"discharge-plans", DischargePlanViewSet, basename="discharge-plan")
router.register(r"discharge-summaries", DischargeSummaryViewSet, basename="discharge-summary")
router.register(r"discharge-notes", DischargeNoteViewSet, basename="discharge-note")

urlpatterns = [
    path("", include(router.urls)),
]