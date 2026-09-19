from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogViewSet,
    AIInteractionViewSet,
)

router = DefaultRouter()

router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")
router.register(r"ai-interactions", AIInteractionViewSet, basename="ai-interaction")

urlpatterns = [
    path("", include(router.urls)),
]