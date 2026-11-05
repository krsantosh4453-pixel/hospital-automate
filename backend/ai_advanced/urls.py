"""Advanced AI API URLs (mounted at /api/ai/discharge/)."""

from rest_framework.routers import SimpleRouter

from .views import DischargeDraftViewSet

router = SimpleRouter()
router.register("admissions", DischargeDraftViewSet, basename="ai-discharge-draft")

urlpatterns = router.urls
