from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    ConsentViewSet,
    OTPVerificationViewSet,
    NotificationDeliveryViewSet,
    VoiceCallFallbackViewSet,
    TwilioStatusView,
)

router = DefaultRouter()

router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"consents", ConsentViewSet, basename="consent")
router.register(r"deliveries", NotificationDeliveryViewSet, basename="notification-delivery")
router.register(r"voice-calls", VoiceCallFallbackViewSet, basename="voice-call-fallback")
router.register(r"otp-verifications", OTPVerificationViewSet, basename="otp-verification")

urlpatterns = [
    # P1-09: Twilio message status callback (signed, no login).
    path("twilio/status/", TwilioStatusView.as_view(), name="twilio-status"),
    path("", include(router.urls)),
]