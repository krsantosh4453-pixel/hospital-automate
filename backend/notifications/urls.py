from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    ConsentViewSet,
    OTPVerificationViewSet,
    NotificationDeliveryViewSet,
)

router = DefaultRouter()

router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"consents", ConsentViewSet, basename="consent")
router.register(r"deliveries", NotificationDeliveryViewSet, basename="notification-delivery")
router.register(r"otp-verifications", OTPVerificationViewSet, basename="otp-verification")

urlpatterns = [
    path("", include(router.urls)),
]