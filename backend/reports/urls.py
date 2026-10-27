from django.urls import path, include
from rest_framework.routers import DefaultRouter

from reports.views import (
    AnalyticsViewSet,
    ReportTemplateViewSet,
    SavedReportViewSet,
    ScheduledReportViewSet,
    KPISnapshotViewSet,
)

router = DefaultRouter()
router.register(r"analytics", AnalyticsViewSet, basename="analytics")
router.register(r"templates", ReportTemplateViewSet, basename="report-template")
router.register(r"saved", SavedReportViewSet, basename="saved-report")
router.register(r"scheduled", ScheduledReportViewSet, basename="scheduled-report")
router.register(r"snapshots", KPISnapshotViewSet, basename="kpi-snapshot")

urlpatterns = [
    path("", include(router.urls)),
]