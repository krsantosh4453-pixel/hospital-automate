from rest_framework import viewsets
from django.db.models import Sum, F, DecimalField, ExpressionWrapper

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

        # Annotate with aggregated values to avoid N+1 queries
        # Use different names to avoid conflict with model properties
        queryset = queryset.annotate(
            total_paid_annotated=Sum("payments__amount"),
            subtotal_annotated=Sum("items__subtotal"),
            tax_amount_annotated=Sum(
                ExpressionWrapper(
                    F("items__subtotal") * F("items__tax_rate") / 100,
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        ).select_related("patient", "hospital")

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