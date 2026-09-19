from rest_framework import viewsets

from .models import Notification, Consent, OTPVerification
from .serializers import (
    NotificationSerializer,
    ConsentSerializer,
    OTPVerificationSerializer,
)


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer


class ConsentViewSet(viewsets.ModelViewSet):
    queryset = Consent.objects.all()
    serializer_class = ConsentSerializer


class OTPVerificationViewSet(viewsets.ModelViewSet):
    queryset = OTPVerification.objects.all()
    serializer_class = OTPVerificationSerializer
