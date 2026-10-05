from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LabTestViewSet,
    SampleCollectionViewSet,
    SampleDispatchViewSet,
    LabResultViewSet,
    ResultVerificationViewSet,
)

router = DefaultRouter()
router.register(r"laboratory", LabTestViewSet, basename="laboratory")
router.register(r"sample-collections", SampleCollectionViewSet, basename="sample-collection")
router.register(r"sample-dispatches", SampleDispatchViewSet, basename="sample-dispatch")
router.register(r"lab-results", LabResultViewSet, basename="lab-result")
router.register(r"result-verifications", ResultVerificationViewSet, basename="result-verification")

urlpatterns = [
    path("", include(router.urls)),
]