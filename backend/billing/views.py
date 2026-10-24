from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from audit.services import record_audit
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
from .services import recalculate, record_payment, record_refund
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsBillingStaff, IsReceptionist, IsPatientReadOnly

BILLING_ROLES = IsAdmin | IsHospitalManager | IsBillingStaff | IsReceptionist


class InvoiceViewSet(HospitalScopedViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [BILLING_ROLES | IsPatientReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("patient", "hospital").prefetch_related(
            "items", "payments"
        )
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_destroy(self, instance):
        if instance.payments.exists():
            raise ValidationError("An invoice with payments cannot be deleted; cancel or refund it instead.")
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin | IsHospitalManager | IsBillingStaff])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.payments.exists():
            raise ValidationError("Refund the payments before cancelling this invoice.")
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status"])
        record_audit(request, "billing.invoice.cancel", invoice, details={"reason": request.data.get("reason", "")})
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin | IsHospitalManager | IsBillingStaff])
    def refund(self, request, pk=None):
        invoice = self.get_object()
        refund = record_refund(
            invoice,
            request.data.get("amount"),
            request.data.get("reason", ""),
            method=request.data.get("payment_method", "Cash"),
            user=request.user,
        )
        record_audit(request, "billing.refund.create", refund, details={"amount": str(refund.amount)})
        return Response(PaymentSerializer(refund).data, status=status.HTTP_201_CREATED)


class InvoiceItemViewSet(HospitalScopedViewSet):
    serializer_class = InvoiceItemSerializer
    permission_classes = [BILLING_ROLES]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("invoice")
        invoice_id = self.request.query_params.get("invoice")
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        return queryset

    def _editable(self, invoice):
        if invoice is None:
            raise ValidationError({"invoice": "Invoice is required."})
        if invoice.payments.exists() or invoice.status == Invoice.Status.CANCELLED:
            raise ValidationError("Items of a paid or cancelled invoice cannot change.")

    def perform_create(self, serializer):
        self._editable(serializer.validated_data.get("invoice"))
        with transaction.atomic():
            super().perform_create(serializer)
            recalculate(serializer.instance.invoice)

    def perform_update(self, serializer):
        self._editable(serializer.instance.invoice)
        with transaction.atomic():
            super().perform_update(serializer)
            recalculate(serializer.instance.invoice)

    def perform_destroy(self, instance):
        self._editable(instance.invoice)
        invoice = instance.invoice
        with transaction.atomic():
            super().perform_destroy(instance)
            recalculate(invoice)


class PaymentViewSet(HospitalScopedViewSet):
    """Payments are append-only financial records: list, read and create."""

    serializer_class = PaymentSerializer
    permission_classes = [BILLING_ROLES]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("invoice")
        invoice_id = self.request.query_params.get("invoice")
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._check_tenancy(serializer.validated_data)
        data = serializer.validated_data
        key = data.get("idempotency_key") or request.headers.get("Idempotency-Key", "")
        payment, created = record_payment(
            data["invoice"],
            data["amount"],
            method=data.get("payment_method", "Cash"),
            user=request.user,
            idempotency_key=key[:80],
            reference=data.get("reference", ""),
        )
        if created:
            record_audit(request, "billing.payment.create", payment, details={"amount": str(payment.amount)})
        return Response(
            self.get_serializer(payment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class InsuranceClaimViewSet(HospitalScopedViewSet):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsBillingStaff]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("patient", "invoice")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
