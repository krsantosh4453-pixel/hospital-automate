from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NurseViewSet,
    NursingAssessmentViewSet,
    NursingNoteViewSet,
    CareTaskViewSet,
    MARViewSet,
    MARAdministrationViewSet,
    PatientAssignmentViewSet,
)

router = DefaultRouter()
router.register(r"nurses", NurseViewSet, basename="nurse")
router.register(r"assessments", NursingAssessmentViewSet, basename="nursing-assessment")
router.register(r"notes", NursingNoteViewSet, basename="nursing-note")
router.register(r"care-tasks", CareTaskViewSet, basename="care-task")
router.register(r"mar", MARViewSet, basename="mar")
router.register(r"mar-administrations", MARAdministrationViewSet, basename="mar-administration")
router.register(r"patient-assignments", PatientAssignmentViewSet, basename="patient-assignment")

urlpatterns = [
    path("", include(router.urls)),
]