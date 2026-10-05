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
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsBillingStaff, IsReceptionist, IsPatientReadOnly


class InvoiceViewSet(HospitalScopedViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsBillingStaff | IsReceptionist | IsPatientReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        return queryset


class InvoiceItemViewSet(HospitalScopedViewSet):
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsBillingStaff | IsReceptionist]

    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.select_related("invoice")

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(invoice__hospital_id=hospital_id)

        invoice_id = self.request.query_params.get("invoice")
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)

        return queryset


class PaymentViewSet(HospitalScopedViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsBillingStaff | IsReceptionist]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            queryset = queryset.filter(invoice__hospital_id=hospital_id)

        return queryset


class InsuranceClaimViewSet(HospitalScopedViewSet):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsBillingStaff]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            queryset = queryset.filter(patient__hospital_id=hospital_id)

        return queryset