from rest_framework import viewsets

from .models import (
    Invoice,
    InvoiceItem,
    Payment,
    InsuranceClaim,
)

from .serializers import (
    InvoiceSerializer,
    InvoiceItemSerializer,
    PaymentSerializer,
    InsuranceClaimSerializer,
)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer


class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer


class InsuranceClaimViewSet(viewsets.ModelViewSet):
    queryset = InsuranceClaim.objects.all()
    serializer_class = InsuranceClaimSerializer