from rest_framework import viewsets

from .models import (
    BloodInventory,
    BloodRequest,
    BloodTransaction,
)

from .serializers import (
    BloodInventorySerializer,
    BloodRequestSerializer,
    BloodTransactionSerializer,
)


class BloodInventoryViewSet(viewsets.ModelViewSet):
    queryset = BloodInventory.objects.all()
    serializer_class = BloodInventorySerializer


class BloodRequestViewSet(viewsets.ModelViewSet):
    queryset = BloodRequest.objects.all()
    serializer_class = BloodRequestSerializer


class BloodTransactionViewSet(viewsets.ModelViewSet):
    queryset = BloodTransaction.objects.all()
    serializer_class = BloodTransactionSerializer
