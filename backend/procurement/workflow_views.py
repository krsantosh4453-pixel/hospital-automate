"""
API for the store workflows (procurement/workflows.py), under /api/procurement/:

requisitions/          raise (store, pharmacy, nursing); approve/reject (admin,
                       manager, not the requester); order (store)
quotations/            supplier prices for an approved requisition; accept
stock-issues/          issue to a department
supplier-returns/      return received stock to its supplier
consignment-settlements/  consignment stock reported as used and payable
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from users.permissions import IsAdmin, IsHospitalManager, IsInventoryStaff, IsNurse, IsPharmacist
from users.viewsets import HospitalScopedViewSet

from . import workflows
from .models import ConsignmentSettlement, PurchaseRequisition, StockIssue, SupplierQuotation, SupplierReturn
from .serializers import PurchaseOrderSerializer
from .workflow_serializers import (
    ConsignmentSettlementSerializer,
    DecisionSerializer,
    OrderRequisitionSerializer,
    QuotationSerializer,
    RequisitionSerializer,
    StockIssueSerializer,
    SupplierReturnSerializer,
)

STORE = IsAdmin | IsHospitalManager | IsInventoryStaff
APPROVERS = IsAdmin | IsHospitalManager
REQUESTERS = STORE | IsPharmacist | IsNurse


class _AppendOnly(HospitalScopedViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def _hospital_for_create(self, data):
        extra = self._check_tenancy(data)
        hospital = data.get("hospital") or extra.get("hospital")
        if hospital is None:
            raise ValidationError({"hospital": "Select a hospital."})
        return hospital


class RequisitionViewSet(_AppendOnly):
    queryset = PurchaseRequisition.objects.select_related(
        "department", "requested_by", "decided_by", "purchase_order").prefetch_related("items__medicine")
    serializer_class = RequisitionSerializer
    permission_classes = [REQUESTERS]

    def get_queryset(self):
        queryset = super().get_queryset()
        wanted = self.request.query_params.get("status")
        return queryset.filter(status=wanted) if wanted else queryset

    def perform_create(self, serializer):
        hospital = self._hospital_for_create(serializer.validated_data)
        requisition = serializer.save(hospital=hospital, requested_by=self.request.user,
                                      reference=workflows.new_reference("REQ"))
        self._audit("create", requisition, details={"items": requisition.items.count()})

    def _decide(self, request, approve):
        requisition = self.get_object()
        body = DecisionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        requisition = workflows.decide_requisition(requisition, request.user, approve, body.validated_data["note"])
        self._audit("approved" if approve else "rejected", requisition, details={"note": requisition.decision_note})
        return Response(self.get_serializer(requisition).data)

    @action(detail=True, methods=["post"], permission_classes=[APPROVERS])
    def approve(self, request, pk=None):
        return self._decide(request, True)

    @action(detail=True, methods=["post"], permission_classes=[APPROVERS])
    def reject(self, request, pk=None):
        return self._decide(request, False)

    @action(detail=True, methods=["post"], permission_classes=[STORE])
    def order(self, request, pk=None):
        """{supplier, unit_costs: [{item, unit_cost}], reference?}: place the purchase order."""
        requisition = self.get_object()
        body = OrderRequisitionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        purchase = workflows.order_requisition(requisition, body.validated_data["supplier"],
                                               body.validated_data["unit_costs"], user=request.user,
                                               reference=body.validated_data["reference"])
        self._audit("ordered", requisition, details={"purchase_order": purchase.reference})
        return Response(PurchaseOrderSerializer(purchase).data, status=status.HTTP_201_CREATED)


class QuotationViewSet(_AppendOnly):
    queryset = SupplierQuotation.objects.select_related("supplier", "requisition").prefetch_related(
        "items__requisition_item__medicine")
    serializer_class = QuotationSerializer
    permission_classes = [STORE]

    def get_queryset(self):
        queryset = super().get_queryset()
        requisition = self.request.query_params.get("requisition")
        return queryset.filter(requisition_id=requisition) if requisition else queryset

    def perform_create(self, serializer):
        hospital = self._hospital_for_create(serializer.validated_data)
        quotation = serializer.save(hospital=hospital, created_by=self.request.user)
        self._audit("create", quotation, details={"supplier": quotation.supplier_id})

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        quotation = self.get_object()
        purchase = workflows.accept_quotation(quotation, user=request.user)
        self._audit("accepted", quotation, details={"purchase_order": purchase.reference})
        return Response(PurchaseOrderSerializer(purchase).data, status=status.HTTP_201_CREATED)


class StockIssueViewSet(_AppendOnly):
    queryset = StockIssue.objects.select_related("department", "medicine", "issued_by")
    serializer_class = StockIssueSerializer
    permission_classes = [STORE]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        hospital = self._hospital_for_create(data)
        issue, created = workflows.issue_stock(
            hospital, data["department"], data["medicine"], data["quantity"], user=request.user,
            received_by_name=data.get("received_by_name", ""), note=data.get("note", ""),
            idempotency_key=(data.get("idempotency_key") or request.headers.get("Idempotency-Key", ""))[:80],
        )
        if created:
            self._audit("create", issue, details={"medicine": issue.medicine_id, "quantity": issue.quantity,
                                                  "department": issue.department.name})
        return Response(self.get_serializer(issue).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class _ReceiptLineViewSet(_AppendOnly):
    permission_classes = [STORE]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._check_tenancy(serializer.validated_data)
        row = self.record(serializer.validated_data, request.user)
        self._audit("create", row, details={"receipt_item": row.receipt_item_id, "quantity": row.quantity})
        return Response(self.get_serializer(row).data, status=status.HTTP_201_CREATED)


class SupplierReturnViewSet(_ReceiptLineViewSet):
    queryset = SupplierReturn.objects.select_related("receipt_item__medicine", "receipt_item__goods_receipt__supplier")
    serializer_class = SupplierReturnSerializer

    def record(self, data, user):
        return workflows.return_to_supplier(data["receipt_item"], data["quantity"], data["reason"], user=user)


class ConsignmentSettlementViewSet(_ReceiptLineViewSet):
    queryset = ConsignmentSettlement.objects.select_related("receipt_item__medicine",
                                                            "receipt_item__goods_receipt__supplier")
    serializer_class = ConsignmentSettlementSerializer

    def record(self, data, user):
        return workflows.settle_consignment(data["receipt_item"], data["quantity"], user=user,
                                            reference=data.get("reference", ""))
