from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from audit.services import record_audit
from .models import (
    AdvanceAccount,
    Invoice,
    InvoiceItem,
    InvoiceWaiver,
    Payment,
    InsuranceClaim,
    ServicePrice,
)

from .serializers import (
    AdvanceAccountSerializer,
    AdvanceDepositSerializer,
    AdvanceMoveSerializer,
    AdvanceTransactionSerializer,
    InvoiceSerializer,
    InvoiceItemSerializer,
    PaymentSerializer,
    InsuranceClaimSerializer,
    InvoiceWaiverSerializer,
    ServicePriceSerializer,
)
from . import advances, price_list
from .charges import release_charges
from .services import recalculate, record_payment, record_refund, refuse_unexplained_zero, waive_invoice
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsBillingStaff, IsReceptionist, IsPatientReadOnly

BILLING_ROLES = IsAdmin | IsHospitalManager | IsBillingStaff | IsReceptionist
# BUG-07: who sets prices and approves a waiver. Billing clerks cannot.
PRICING_ROLES = IsAdmin | IsHospitalManager


class InvoiceViewSet(HospitalScopedViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [BILLING_ROLES | IsPatientReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("patient", "hospital", "waiver__approved_by").prefetch_related(
            "items", "payments", "patient__hospital_memberships"
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
        if instance.items.filter(pharmacy_sale__isnull=False).exists():
            raise ValidationError("This bill holds dispensed medicine; cancel it instead of deleting it.")
        if instance.items.exclude(charge_key="").exists() or InvoiceWaiver.objects.filter(invoice=instance).exists():
            # BUG-07: captured charges and waivers are financial history.
            raise ValidationError("This bill holds captured charges or a waiver; cancel it instead of deleting it.")
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin | IsHospitalManager | IsBillingStaff])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.payments.exists():
            raise ValidationError("Refund the payments before cancelling this invoice.")
        reason = str(request.data.get("reason") or "").strip()
        if invoice.is_final or invoice.items.exclude(charge_key="").exists():
            # BUG-07 review: cancelling a bill of captured charges is a way to make
            # work free, so only an Admin or Hospital Manager may, with a reason.
            if not PRICING_ROLES().has_permission(request, self):
                return Response({"detail": "This bill holds charges captured from the work. Only an Admin or "
                                           "Hospital Manager can cancel it."}, status=status.HTTP_403_FORBIDDEN)
            if len(reason) < 10:
                raise ValidationError({"reason": "Say why this bill is cancelled (at least 10 characters)."})
        with transaction.atomic():
            invoice.status = Invoice.Status.CANCELLED
            invoice.save(update_fields=["status"])
            # BUG-07: the services on a cancelled bill may be charged again on its replacement.
            release_charges(invoice)
        record_audit(request, "billing.invoice.cancel", invoice, details={"reason": request.data.get("reason", "")})
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["post"], permission_classes=[PRICING_ROLES])
    def waive(self, request, pk=None):
        """{reason}: an Admin or Hospital Manager waives what is due on this bill (BUG-07)."""
        invoice = self.get_object()
        waiver = waive_invoice(invoice, request.data.get("reason", ""), request.user)
        record_audit(request, "billing.invoice.waived", invoice,
                     details={"amount": str(waiver.amount), "reason": waiver.reason})
        invoice.refresh_from_db()
        return Response({"waiver": InvoiceWaiverSerializer(waiver).data, "invoice": self.get_serializer(invoice).data},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="apply-advance", permission_classes=[BILLING_ROLES])
    def apply_advance(self, request, pk=None):
        """{amount, idempotency_key}: pay this invoice from the patient's advance (H4)."""
        invoice = self.get_object()
        body = AdvanceMoveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        key = body.validated_data["idempotency_key"] or request.headers.get("Idempotency-Key", "")
        move, created = advances.apply_to_invoice(invoice, body.validated_data["amount"], user=request.user,
                                                  idempotency_key=key[:80])
        if created:
            record_audit(request, "billing.advance.applied", invoice,
                         details={"amount": str(move.amount), "advance_receipt": move.receipt_number,
                                  "balance_after": str(move.balance_after)})
        invoice.refresh_from_db()
        return Response({"advance": AdvanceTransactionSerializer(move).data, "invoice": self.get_serializer(invoice).data},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin | IsHospitalManager | IsBillingStaff])
    def refund(self, request, pk=None):
        invoice = self.get_object()
        if str(request.data.get("payment_method", "")).strip().lower() == "advance":
            refund, move = advances.return_to_advance(invoice, request.data.get("amount"),
                                                      request.data.get("reason", ""), user=request.user)
            record_audit(request, "billing.advance.returned", invoice,
                         details={"amount": str(move.amount), "balance_after": str(move.balance_after)})
            return Response(PaymentSerializer(refund).data, status=status.HTTP_201_CREATED)
        key = str(request.data.get("idempotency_key") or request.headers.get("Idempotency-Key", ""))
        refund, created = record_refund(
            invoice,
            request.data.get("amount"),
            request.data.get("reason", ""),
            method=request.data.get("payment_method", "Cash"),
            user=request.user,
            idempotency_key=key[:80],
        )
        if created:
            record_audit(request, "billing.refund.create", refund, details={"amount": str(refund.amount)})
        return Response(PaymentSerializer(refund).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


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
        if InvoiceWaiver.objects.filter(invoice=invoice).exists():
            raise ValidationError("This bill was waived; its items cannot change.")

    def perform_create(self, serializer):
        self._editable(serializer.validated_data.get("invoice"))
        with transaction.atomic():
            super().perform_create(serializer)
            refuse_unexplained_zero(recalculate(serializer.instance.invoice))

    @staticmethod
    def _not_pharmacy_line(item):
        # F9: a medicine line mirrors a pharmacy sale; it changes only through a pharmacy return.
        if item.pharmacy_sale_id:
            raise ValidationError("Medicine lines come from the pharmacy; return the medicine there to change them.")
        # BUG-07: a captured charge mirrors the work done; cancel the bill to undo it.
        if item.charge_key:
            raise ValidationError("This charge was captured from the price list; cancel the bill to undo it.")

    def perform_update(self, serializer):
        self._editable(serializer.instance.invoice)
        self._not_pharmacy_line(serializer.instance)
        with transaction.atomic():
            super().perform_update(serializer)
            refuse_unexplained_zero(recalculate(serializer.instance.invoice))

    def perform_destroy(self, instance):
        self._editable(instance.invoice)
        self._not_pharmacy_line(instance)
        invoice = instance.invoice
        if invoice.items.count() <= 1:
            # An empty bill would read as ₹0 "Paid"; cancel it instead.
            raise ValidationError("This is the bill's only line. Cancel the bill instead.")
        with transaction.atomic():
            super().perform_destroy(instance)
            refuse_unexplained_zero(recalculate(invoice))


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


class AdvanceAccountViewSet(HospitalScopedViewSet):
    """
    Patients' advance balances (H4), read-only; money moves only through the
    deposit and refund actions here and the invoice apply-advance action.
    """

    queryset = AdvanceAccount.objects.select_related("patient", "hospital")
    serializer_class = AdvanceAccountSerializer
    permission_classes = [BILLING_ROLES]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Use deposit/ to receive an advance."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=["post"])
    def deposit(self, request):
        """{patient, amount, payment_method, reference, idempotency_key} for the selected hospital."""
        body = AdvanceDepositSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        extra = self._check_tenancy(data)
        hospital = data.get("hospital") or extra.get("hospital")
        if hospital is None:
            raise ValidationError({"hospital": "Select a hospital."})
        key = data["idempotency_key"] or request.headers.get("Idempotency-Key", "")
        move, created = advances.record_deposit(
            hospital.pk, data["patient"].pk, data["amount"], method=data["payment_method"], user=request.user,
            idempotency_key=key[:80], reference=data["reference"],
        )
        if created:
            record_audit(request, "billing.advance.deposit", move.account, hospital=hospital.pk,
                         details={"amount": str(move.amount), "receipt": move.receipt_number,
                                  "balance_after": str(move.balance_after)})
        return Response(AdvanceAccountSerializer(move.account).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin | IsHospitalManager | IsBillingStaff])
    def refund(self, request, pk=None):
        """{amount, reason, payment_method}: pay unused advance back to the patient."""
        account = self.get_object()
        body = AdvanceMoveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        key = body.validated_data["idempotency_key"] or request.headers.get("Idempotency-Key", "")
        move, created = advances.refund_to_patient(account, body.validated_data["amount"],
                                                   body.validated_data["reason"],
                                                   method=body.validated_data["payment_method"], user=request.user,
                                                   idempotency_key=key[:80])
        if created:
            record_audit(request, "billing.advance.refund", account,
                         details={"amount": str(move.amount), "reason": move.reference,
                                  "balance_after": str(move.balance_after)})
        account.refresh_from_db()
        return Response(self.get_serializer(account).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ServicePriceViewSet(HospitalScopedViewSet):
    """
    BUG-07: the hospital price list. Billing reads it; an Admin or Hospital
    Manager adds prices and retires them. Rows are never edited or deleted:
    a new price for a service closes the old one (billing/price_list.py).

    ?category=, ?current=1 (in force today), ?q= (code, name or applies_to).
    """

    queryset = ServicePrice.objects.select_related("doctor")
    serializer_class = ServicePriceSerializer
    permission_classes = [BILLING_ROLES]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if getattr(self, "action", None) in ("create", "retire", "charge_unbilled"):
            return [PRICING_ROLES()]
        return super().get_permissions()

    def get_queryset(self):
        from django.db.models import Q

        from config.hospital_time import hospital_today

        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        if self.request.query_params.get("current") in ("1", "true", "yes"):
            queryset = price_list.effective_on(queryset, hospital_today())
        query = (self.request.query_params.get("q") or "").strip()
        if query:
            queryset = queryset.filter(Q(code__icontains=query) | Q(name__icontains=query) | Q(applies_to__icontains=query))
        return queryset

    def create(self, request, *args, **kwargs):
        from config.hospital_time import hospital_today

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        extra = self._check_tenancy(data)
        hospital = data.pop("hospital", None) or extra.get("hospital")
        if hospital is None:
            raise ValidationError({"hospital": "Select a hospital."})
        doctor = data.get("doctor")
        if doctor is not None and doctor.hospital_id != hospital.pk:
            raise ValidationError({"doctor": "This doctor is not at this hospital."})
        data.setdefault("effective_from", hospital_today())
        price = price_list.add_price(hospital, user=request.user, **data)
        record_audit(request, "billing.price.create", price, hospital=hospital.pk,
                     details={"code": price.code, "unit_price": str(price.unit_price), "tax_rate": str(price.tax_rate),
                              "effective_from": str(price.effective_from)})
        return Response(self.get_serializer(price).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        """{effective_to}: the last day this price is charged (default today)."""
        from django.utils.dateparse import parse_date

        from config.hospital_time import hospital_today

        price = self.get_object()
        raw = request.data.get("effective_to")
        end = parse_date(str(raw)) if raw else hospital_today()
        if end is None:
            raise ValidationError({"effective_to": "Give a date as YYYY-MM-DD."})
        price = price_list.retire(price, end)
        record_audit(request, "billing.price.retire", price, details={"effective_to": str(end)})
        return Response(self.get_serializer(price).data)

    def _sweep_scope(self, request):
        """B-2: the one acting hospital and the first day swept."""
        from django.utils.dateparse import parse_date

        from . import unbilled

        hospitals = self.get_acting_hospital_ids()
        if len(hospitals) != 1:
            raise ValidationError({"hospital": "Choose one hospital."})
        raw = request.query_params.get("since") or request.data.get("since")
        day = parse_date(str(raw)) if raw else None
        if raw and day is None:
            raise ValidationError({"since": "Give a date as YYYY-MM-DD."})
        try:
            return hospitals[0], unbilled.since_day(day)
        except ValueError as exc:
            raise ValidationError({"since": str(exc)}) from exc

    @action(detail=False, methods=["get"])
    def unbilled(self, request):
        """
        B-2: consultations and laboratory tests the capture skipped for want
        of a price, and charges left on cancelled bills, since ?since=
        (default 30 days, at most 90). Each row says its source and whether
        it has a price today.
        """
        from . import unbilled

        hospital_id, since = self._sweep_scope(request)
        rows = unbilled.find_unbilled(hospital_id, since)
        return Response({"since": str(since), "count": len(rows), "results": rows})

    @action(detail=False, methods=["post"], url_path="charge-unbilled")
    def charge_unbilled(self, request):
        """
        B-2: charge unbilled work (Admin or Hospital Manager). Without
        ``items`` only priced work that was skipped for want of a price;
        with ``items`` [{kind, id}] exactly those, including work from a
        cancelled bill. Each service is charged once only.
        """
        from . import unbilled

        hospital_id, since = self._sweep_scope(request)
        selected = self._selected_rows(request.data.get("items"))
        charged, left = unbilled.charge_unbilled(hospital_id, since, selected)
        record_audit(request, "billing.charge.unbilled_swept", None, hospital=hospital_id,
                     details={"since": str(since), "charged": len(charged), "left": len(left),
                              "picked": selected is not None,
                              "keys": [f"{r['kind']}:{r['id']}" for r in charged]})
        return Response({"since": str(since), "charged": charged, "left": left})

    @staticmethod
    def _selected_rows(items):
        """{items: [{kind, id}]} picks rows (needed for work from a cancelled bill); none means the bulk sweep."""
        if items is None:
            return None
        if not isinstance(items, list):
            raise ValidationError({"items": "Send a list of {kind, id}."})
        picked = set()
        for item in items:
            kind = item.get("kind") if isinstance(item, dict) else None
            pk = item.get("id") if isinstance(item, dict) else None
            if kind not in ("consultation", "laboratory", "imaging") or not isinstance(pk, int):
                raise ValidationError(
                    {"items": "Each item needs kind (consultation, laboratory or imaging) and a numeric id."})
            picked.add((kind, pk))
        return picked

    @action(detail=False, methods=["get"])
    def medicines(self, request):
        """
        Pharmacy prices: the selling price of each stocked batch (capped by its
        MRP), as dispensing charges them. Managed in pharmacy stock, read here.
        """
        from pharmacy.models import Medicine

        rows = Medicine.objects.filter(hospital_id__in=self.get_acting_hospital_ids()).order_by("name", "batch")
        query = (request.query_params.get("q") or "").strip()
        if query:
            rows = rows.filter(name__icontains=query)
        return Response([
            {"id": row.pk, "hospital": row.hospital_id, "name": row.name, "batch": row.batch,
             "unit_price": str(row.price), "mrp": str(row.mrp) if row.mrp is not None else None,
             "tax_rate": str(row.tax_rate), "hsn_code": row.hsn_code, "currency": ServicePrice.INR,
             "in_stock": row.quantity}
            for row in rows[:500]
        ])


class InsuranceClaimViewSet(HospitalScopedViewSet):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsBillingStaff]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("patient", "invoice")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
