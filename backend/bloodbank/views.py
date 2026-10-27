from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Sum, F

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
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsDoctor, IsNurse, IsBloodBankStaff


class BloodInventoryViewSet(HospitalScopedViewSet):
    queryset = BloodInventory.objects.all()
    serializer_class = BloodInventorySerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse | IsBloodBankStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        return qs.select_related("hospital")


class BloodRequestViewSet(HospitalScopedViewSet):
    queryset = BloodRequest.objects.all()
    serializer_class = BloodRequestSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse | IsBloodBankStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related("hospital", "patient", "requested_by", "approved_by")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        blood_request = self.get_object()

        if blood_request.status != "Requested":
            return Response(
                {"detail": "Only requested blood can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inventory = BloodInventory.objects.filter(
            hospital=blood_request.hospital,
            blood_group=blood_request.blood_group,
            component=blood_request.component,
        ).first()

        if not inventory or inventory.units < blood_request.units:
            return Response(
                {"detail": "Insufficient blood inventory for this request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blood_request.status = "Approved"
        blood_request.approved_by = None  # Doctor FK not linked to User
        blood_request.save()

        return Response(BloodRequestSerializer(blood_request).data)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        blood_request = self.get_object()

        if blood_request.status != "Approved":
            return Response(
                {"detail": "Only approved blood requests can be issued."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                inventory = BloodInventory.objects.select_for_update().get(
                    hospital=blood_request.hospital,
                    blood_group=blood_request.blood_group,
                    component=blood_request.component,
                )

                if inventory.units < blood_request.units:
                    return Response(
                        {"detail": "Insufficient inventory at time of issue."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                inventory.units = F("units") - blood_request.units
                inventory.save()

                inventory.refresh_from_db()

                BloodTransaction.objects.create(
                    hospital=blood_request.hospital,
                    request=blood_request,
                    inventory=inventory,
                    transaction_type="Issue",
                    units=blood_request.units,
                    performed_by=request.user,
                    remarks=f"Issued for patient {blood_request.patient.name}",
                )

                blood_request.status = "Issued"
                blood_request.save()

        except BloodInventory.DoesNotExist:
            return Response(
                {"detail": "Blood inventory not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(BloodRequestSerializer(blood_request).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        blood_request = self.get_object()

        if blood_request.status != "Requested":
            return Response(
                {"detail": "Only requested blood can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blood_request.status = "Rejected"
        blood_request.save()

        return Response(BloodRequestSerializer(blood_request).data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        qs = self.get_queryset().filter(status="Requested")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class BloodTransactionViewSet(HospitalScopedViewSet):
    queryset = BloodTransaction.objects.all()
    serializer_class = BloodTransactionSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsDoctor | IsNurse | IsBloodBankStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        transaction_type = self.request.query_params.get("type")
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)
        return qs.select_related("hospital", "request", "inventory", "performed_by", "request__patient")

    @action(detail=False, methods=["post"])
    def receive(self, request):
        """Receive blood into inventory."""
        hospital_id = request.data.get("hospital")
        blood_group = request.data.get("blood_group")
        component = request.data.get("component")
        units = request.data.get("units")
        expiry_date = request.data.get("expiry_date")
        remarks = request.data.get("remarks", "")

        if not all([hospital_id, blood_group, component, units]):
            return Response(
                {"detail": "hospital, blood_group, component, and units are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                inventory, created = BloodInventory.objects.select_for_update().get_or_create(
                    hospital_id=hospital_id,
                    blood_group=blood_group,
                    component=component,
                    defaults={"units": 0, "expiry_date": expiry_date},
                )

                if expiry_date and inventory.expiry_date != expiry_date:
                    inventory.expiry_date = expiry_date

                inventory.units = F("units") + int(units)
                inventory.save()
                inventory.refresh_from_db()

                BloodTransaction.objects.create(
                    hospital_id=hospital_id,
                    inventory=inventory,
                    transaction_type="Receive",
                    units=int(units),
                    performed_by=request.user,
                    remarks=remarks,
                )

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Blood received successfully", "inventory": BloodInventorySerializer(inventory).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def adjust(self, request):
        """Adjust inventory (positive or negative)."""
        inventory_id = request.data.get("inventory_id")
        units = request.data.get("units")
        remarks = request.data.get("remarks", "")

        if not all([inventory_id, units]):
            return Response(
                {"detail": "inventory_id and units are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                inventory = BloodInventory.objects.select_for_update().get(id=inventory_id)

                new_units = inventory.units + int(units)
                if new_units < 0:
                    return Response(
                        {"detail": "Cannot adjust inventory below zero."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                inventory.units = new_units
                inventory.save()

                BloodTransaction.objects.create(
                    hospital=inventory.hospital,
                    inventory=inventory,
                    transaction_type="Adjustment",
                    units=abs(int(units)),
                    performed_by=request.user,
                    remarks=remarks,
                )

        except BloodInventory.DoesNotExist:
            return Response(
                {"detail": "Inventory not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"detail": "Inventory adjusted successfully", "inventory": BloodInventorySerializer(inventory).data}
        )

    @action(detail=False, methods=["get"])
    def stock_summary(self, request):
        """Get current stock levels grouped by blood group."""
        hospital_id = request.query_params.get("hospital")
        qs = self.get_queryset().filter(hospital_id=hospital_id) if hospital_id else self.get_queryset()

        inventory = qs.filter(transaction_type__in=["Receive", "Issue", "Return", "Adjustment", "Expiry"]).values(
            "inventory__blood_group", "inventory__component"
        ).annotate(
            total_received=Sum("units", filter=Q(transaction_type="Receive")),
            total_issued=Sum("units", filter=Q(transaction_type="Issue")),
            total_returned=Sum("units", filter=Q(transaction_type="Return")),
            total_adjusted=Sum("units", filter=Q(transaction_type="Adjustment")),
            total_expired=Sum("units", filter=Q(transaction_type="Expiry")),
        )

        return Response(inventory)