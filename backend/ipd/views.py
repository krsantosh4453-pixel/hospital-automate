import logging

from rest_framework import viewsets, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from audit.services import record_audit
from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    IsAdmin,
    IsBillingStaff,
    IsDoctor,
    IsHospitalManager,
    IsHospitalManagerReadOnly,
    IsNurse,
    IsReceptionist,
)
from config.hospital_time import hospital_today
from encounters.services.visit_lifecycle import close_open_tokens, recalculate_queue_of
from . import discharge
from .models import (
    Admission,
    BedAllocation,
    DischargePlan,
    DischargeSummary,
    DischargeNote,
)
logger = logging.getLogger(__name__)


class AdmissionConflict(APIException):
    """The patient is already in this hospital: one active stay at a time."""

    status_code = 409
    default_detail = "This patient already has an active admission at this hospital."
    default_code = "active_admission"

from .serializers import (
    AdmissionSerializer,
    BedAllocationSerializer,
    DischargePlanSerializer,
    DischargeSummarySerializer,
    DischargeNoteSerializer,
)


# Who issues the final bill of a stay: the same roles that create invoices.
BILLING_ROLES = IsAdmin | IsHospitalManager | IsBillingStaff | IsReceptionist


class AdmissionViewSet(HospitalScopedViewSet):
    queryset = Admission.objects.select_related("hospital", "patient", "admitting_doctor").prefetch_related("bed_allocations__bed__room__ward")
    serializer_class = AdmissionSerializer
    permission_classes = [IsDoctor | IsNurse | IsHospitalManagerReadOnly]

    # A stay still in the hospital (one at a time per patient and hospital).
    ACTIVE_STATUSES = ("Admitted", "Discharge Initiated")

    def get_permissions(self):
        # Prompt 3: only a doctor admits. Nurses keep reading and moving beds.
        if getattr(self, "action", None) == "create":
            return [IsDoctor()]
        return super().get_permissions()

    def perform_create(self, serializer):
        from doctors.models import Doctor
        from patients.models import Patient

        from users.permissions import get_request_hospital_id

        hospital_id = getattr(serializer.validated_data.get("hospital"), "pk", None) or get_request_hospital_id(
            self.request, self)
        doctor = Doctor.objects.filter(user=self.request.user, hospital_id=hospital_id).first()
        if doctor is None:
            raise ValidationError({"admitting_doctor": "Only a doctor of this hospital, linked to your login, can admit."})
        # The admitting doctor is the signed-in doctor, which puts the patient
        # in their care for the tenancy check (users/care_scope.py).
        extra = self._check_tenancy({**serializer.validated_data, "admitting_doctor": doctor})
        hospital = serializer.validated_data.get("hospital") or extra.get("hospital") or doctor.hospital
        patient = serializer.validated_data["patient"]
        with transaction.atomic():
            # The patient row is the lock: two admissions at the same moment wait here.
            Patient.objects.select_for_update().filter(pk=patient.pk).first()
            if Admission.objects.filter(patient=patient, hospital=hospital, status__in=self.ACTIVE_STATUSES).exists():
                raise AdmissionConflict()
            serializer.save(status="Admitted", admitting_doctor=doctor, **extra)
        record_audit(self.request, "ipd.admission.create", serializer.instance, hospital=hospital.pk)

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        admission_status = self.request.query_params.get("status")
        if admission_status:
            qs = qs.filter(status=admission_status)
        return qs

    @action(detail=True, methods=["post"])
    def allocate_bed(self, request, pk=None):
        """Allocate an available bed to this admission."""
        admission = self.get_object()

        if admission.status != "Admitted":
            return Response(
                {"detail": "Can only allocate bed for admitted patients."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bed_id = request.data.get("bed_id")
        if not bed_id:
            return Response(
                {"detail": "bed_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Lock the admission before checking for an active bed, so
                # parallel requests for different beds cannot all pass the check.
                type(admission).objects.select_for_update().filter(pk=admission.pk).first()
                active_allocation = admission.bed_allocations.filter(is_active=True).select_related("bed").first()
                if active_allocation:
                    return Response(
                        {"detail": f"Patient already allocated to bed {active_allocation.bed}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                bed = BedAllocation._meta.get_field("bed").related_model.objects.select_for_update().get(
                    id=bed_id, room__ward__hospital=admission.hospital
                )

                if bed.status != "Available":
                    return Response(
                        {"detail": f"Bed {bed} is not available (status: {bed.status})."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                bed.status = "Occupied"
                bed.save()

                allocation = BedAllocation.objects.create(
                    admission=admission,
                    bed=bed,
                    is_active=True,
                )

        except BedAllocation._meta.get_field("bed").related_model.DoesNotExist:
            return Response(
                {"detail": "Bed not found in this hospital."},
                status=status.HTTP_404_NOT_FOUND,
            )

        record_audit(request, "ipd.bed.allocated", admission, details={"bed": allocation.bed_id})
        return Response(BedAllocationSerializer(allocation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def release_bed(self, request, pk=None):
        """Release the current bed allocation."""
        admission = self.get_object()

        active_allocation = admission.bed_allocations.filter(is_active=True).first()
        if not active_allocation:
            return Response(
                {"detail": "No active bed allocation found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                bed = active_allocation.bed
                bed.status = "Available"
                bed.save()

                active_allocation.is_active = False
                active_allocation.released_at = timezone.now()
                active_allocation.save()

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record_audit(request, "ipd.bed.released", admission)
        return Response({"detail": "Bed released successfully"})

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """Transfer patient to a different bed."""
        admission = self.get_object()
        new_bed_id = request.data.get("bed_id")

        if not new_bed_id:
            return Response(
                {"detail": "bed_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Lock the admission so parallel transfers cannot each move the
                # patient into a bed, then check the new bed before releasing
                # the old one: a refused transfer must leave the patient in place.
                type(admission).objects.select_for_update().filter(pk=admission.pk).first()
                active_allocation = admission.bed_allocations.filter(is_active=True).select_related("bed").first()
                if not active_allocation:
                    return Response(
                        {"detail": "No active bed allocation to transfer from."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                new_bed = BedAllocation._meta.get_field("bed").related_model.objects.select_for_update().get(
                    id=new_bed_id, room__ward__hospital=admission.hospital
                )
                if new_bed.status != "Available":
                    return Response(
                        {"detail": f"Bed {new_bed} is not available."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                old_bed = active_allocation.bed
                old_bed.status = "Available"
                old_bed.save()

                active_allocation.is_active = False
                active_allocation.released_at = timezone.now()
                active_allocation.save()

                new_bed.status = "Occupied"
                new_bed.save()

                new_allocation = BedAllocation.objects.create(
                    admission=admission,
                    bed=new_bed,
                    is_active=True,
                )

        except BedAllocation._meta.get_field("bed").related_model.DoesNotExist:
            return Response(
                {"detail": "New bed not found in this hospital."},
                status=status.HTTP_404_NOT_FOUND,
            )

        record_audit(request, "ipd.bed.transferred", admission, details={"bed": new_allocation.bed_id})
        return Response(BedAllocationSerializer(new_allocation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def initiate_discharge(self, request, pk=None):
        """Initiate discharge process."""
        admission = self.get_object()

        if admission.status not in ["Admitted", "Discharge Initiated"]:
            return Response(
                {"detail": "Can only initiate discharge for admitted patients."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admission.status = "Discharge Initiated"
        admission.save()
        record_audit(request, "ipd.admission.discharge_initiated", admission)

        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=["post"])
    def complete_discharge(self, request, pk=None):
        """Complete discharge - release bed and mark as discharged."""
        admission = self.get_object()

        if admission.status != "Discharge Initiated":
            return Response(
                {"detail": "Discharge must be initiated first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        state = discharge.readiness(admission)
        if not state["ready"]:
            return Response(
                {"detail": " ".join(state["blockers"]), "blockers": state["blockers"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Release bed if allocated
                active_allocation = admission.bed_allocations.filter(is_active=True).first()
                if active_allocation:
                    bed = active_allocation.bed
                    bed.status = "Available"
                    bed.save()

                    active_allocation.is_active = False
                    active_allocation.released_at = timezone.now()
                    active_allocation.save()

                admission.status = "Discharged"
                admission.discharge_date = timezone.now()
                admission.save()

                # The stay's ward medication orders end with it; otherwise their
                # later doses kept showing as due to nurses for a patient who
                # had left. Recorded doses are kept as they are.
                from nurses.models import MAR

                stopped_orders = MAR.objects.filter(admission=admission, is_active=True).update(
                    is_active=False, end_date=hospital_today(),
                )

                # BUG-02: a discharged patient leaves every outpatient queue of
                # this hospital (today's and older tokens; later follow-ups stay).
                close_open_tokens(
                    admission.patient_id, admission.hospital_id, hospital_today(),
                    after_commit=recalculate_queue_of,
                )

        except Exception:
            logger.exception("Discharge completion failed")
            return Response(
                {"detail": "Discharge could not be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record_audit(request, "ipd.admission.discharged", admission,
                     details={"medication_orders_stopped": stopped_orders})
        return Response(AdmissionSerializer(admission).data)

    @action(detail=True, methods=["get"])
    def readiness(self, request, pk=None):
        """Checklist, summary and final-bill state of this discharge (E7)."""
        return Response(discharge.readiness(self.get_object()))

    @action(detail=False, methods=["get"], permission_classes=[BILLING_ROLES])
    def awaiting_final_bill(self, request):
        """Stays being discharged, with only what billing needs (E12, H8)."""
        rows = (
            self.get_queryset()
            .filter(status="Discharge Initiated")
            .select_related("patient")
            .prefetch_related("invoices__payments", "invoices__items")
        )
        return Response([
            {
                "admission": admission.pk,
                "patient": admission.patient_id,
                "patient_name": admission.patient.name,
                "admission_date": admission.admission_date,
                "days": discharge.billable_days(admission),
                "final_invoice": discharge.invoice_brief(discharge.final_invoice(admission)),
                # BUG-07: the bed days priced from the price list, before the bill exists.
                "bed_charges": discharge.bed_charge_preview(admission),
            }
            for admission in rows
        ])

    @action(detail=True, methods=["post"], permission_classes=[BILLING_ROLES])
    def final_bill(self, request, pk=None):
        """Create the final invoice of this stay: its charges, bed days from the price list, plus ``items``."""
        admission = self.get_object()
        items = request.data.get("items") or []
        if not isinstance(items, list):
            raise ValidationError({"items": "Send a list of bill lines."})
        invoice = discharge.create_final_bill(admission, request.data.get("daily_rate"), items)
        record_audit(request, "billing.invoice.final_bill", invoice, hospital=admission.hospital_id)
        return Response(discharge.invoice_brief(invoice), status=status.HTTP_201_CREATED)


class BedAllocationViewSet(HospitalScopedViewSet):
    queryset = BedAllocation.objects.select_related("admission__hospital", "admission__patient", "bed__room__ward")
    serializer_class = BedAllocationSerializer
    permission_classes = [IsNurse | IsDoctor | IsHospitalManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(admission__hospital_id=hospital_id)
        return qs

    @action(detail=False, methods=["get"])
    def available_beds(self, request):
        """Get list of available beds for a hospital."""
        hospital_id = request.query_params.get("hospital")
        if not hospital_id:
            return Response(
                {"detail": "hospital query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from hospital.models import Bed
        beds = Bed.objects.filter(
            room__ward__hospital_id=hospital_id,
            status="Available"
        ).select_related("room__ward")

        data = [
            {
                "id": bed.id,
                "bed_number": bed.bed_number,
                "room": bed.room.room_number,
                "ward": bed.room.ward.name,
                "room_type": bed.room.room_type,
            }
            for bed in beds
        ]
        return Response(data)


class DischargePlanViewSet(HospitalScopedViewSet):
    queryset = DischargePlan.objects.select_related(
        "admission__hospital", "admission__patient", "created_by"
    ).order_by("-created_at", "-id")
    serializer_class = DischargePlanSerializer
    permission_classes = [IsDoctor | IsNurse | IsHospitalManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(admission__hospital_id=hospital_id)
        return qs


class DischargeSummaryViewSet(HospitalScopedViewSet):
    """A summary is editable until a doctor finalizes it; then it is locked
    and later information goes into discharge notes (addenda)."""

    queryset = DischargeSummary.objects.select_related("admission__hospital", "admission__patient", "authorized_doctor")
    serializer_class = DischargeSummarySerializer
    permission_classes = [IsDoctor | IsHospitalManagerReadOnly]

    def perform_update(self, serializer):
        if serializer.instance.finalized:
            raise ValidationError("A finalized discharge summary cannot be changed; add a discharge note.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.finalized:
            raise ValidationError("A finalized discharge summary cannot be deleted.")
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        from doctors.models import Doctor

        summary = self.get_object()
        if summary.finalized:
            return Response({"detail": "Already finalized."}, status=status.HTTP_400_BAD_REQUEST)
        doctor = Doctor.objects.filter(user=request.user, hospital_id=summary.admission.hospital_id).first()
        if doctor is None:
            return Response(
                {"detail": "Only a doctor of this hospital, linked to your login, can finalize."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not summary.summary.strip():
            return Response({"detail": "The summary is empty."}, status=status.HTTP_400_BAD_REQUEST)
        summary.authorized_doctor = doctor
        summary.finalized = True
        summary.finalized_at = timezone.now()
        summary.save(update_fields=["authorized_doctor", "finalized", "finalized_at"])
        record_audit(request, "ipd.discharge_summary.finalize", summary, hospital=summary.admission.hospital_id)
        return Response(self.get_serializer(summary).data)


class DischargeNoteViewSet(HospitalScopedViewSet):
    queryset = DischargeNote.objects.select_related("admission__hospital", "admission__patient", "created_by")
    serializer_class = DischargeNoteSerializer
    permission_classes = [IsDoctor | IsNurse | IsHospitalManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(admission__hospital_id=hospital_id)
        return qs