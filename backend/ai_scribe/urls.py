from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConsultationSessionViewSet,
    ConversationTranscriptViewSet,
    AIConsultationDraftViewSet,
    DoctorReviewViewSet,
    ClinicalExtractionSchemaViewSet,
    AIPromptTemplateViewSet,
    AICapabilitiesView,
)

router = DefaultRouter()

router.register(
    r"consultation-sessions",
    ConsultationSessionViewSet,
    basename="consultation-session",
)
router.register(
    r"transcripts",
    ConversationTranscriptViewSet,
    basename="transcript",
)
router.register(
    r"drafts",
    AIConsultationDraftViewSet,
    basename="ai-draft",
)
router.register(
    r"reviews",
    DoctorReviewViewSet,
    basename="doctor-review",
)
router.register(
    r"schemas",
    ClinicalExtractionSchemaViewSet,
    basename="extraction-schema",
)
router.register(
    r"prompts",
    AIPromptTemplateViewSet,
    basename="prompt-template",
)

urlpatterns = [
    path("capabilities/", AICapabilitiesView.as_view(), name="ai-capabilities"),
    path("", include(router.urls)),
]