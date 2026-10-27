from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    SampleCollectionViewSet,
    SampleDispatchViewSet,
    LabResultViewSet,
    ResultVerificationViewSet,
)

# Lab tests themselves are served by the root router at /api/laboratory/.
# This include is mounted *before* the root router (config/urls.py) so these
# sub-resources are not swallowed as /api/laboratory/<pk>/; SimpleRouter has no
# index view, so /api/laboratory/ itself still falls through to the test list.
router = SimpleRouter()
router.register(r"sample-collections", SampleCollectionViewSet, basename="sample-collection")
router.register(r"sample-dispatches", SampleDispatchViewSet, basename="sample-dispatch")
router.register(r"lab-results", LabResultViewSet, basename="lab-result")
router.register(r"result-verifications", ResultVerificationViewSet, basename="result-verification")

urlpatterns = [
    path("", include(router.urls)),
]