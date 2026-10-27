from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    get_linked_patient, is_active_staff, IsDoctor, IsHospitalManagerReadOnly, IsLabStaff, IsNurse,
    IsPatientReadOnly,
)
from .models import (
    LabTest,
    SampleCollection,
    SampleDispatch,
    LabResult,
    ResultVerification,
)
from .serializers import (
    LabTestSerializer,
    LabTestCreateSerializer,
    SampleCollectionSerializer,
    SampleDispatchSerializer,
    LabResultSerializer,
    ResultVerificationSerializer,
)


class LabTestViewSet(HospitalScopedViewSet):
    queryset = LabTest.objects.select_related("hospital", "patient", "doctor", "visit").prefetch_related(
        "sample_collection", "sample_dispatch", "lab_result"
    )
    serializer_class = LabTestSerializer
    permission_classes = [IsLabStaff | IsDoctor | IsNurse | IsPatientReadOnly | IsHospitalManagerReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return LabTestCreateSerializer
        return LabTestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if get_linked_patient(self.request.user) and not is_active_staff(self.request.user):
            # Patients see a result only after the laboratory has verified and released it.
            return qs.filter(status="Released")
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        test_status = self.request.query_params.get("status")
        if test_status:
            qs = qs.filter(status=test_status)
        priority = self.request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)
        # Date range filter
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(test_date__gte=date_from)
        if date_to:
            qs = qs.filter(test_date__lte=date_to)
        return qs

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff | IsNurse])
    def collect_sample(self, request, pk=None):
        """Record sample collection."""
        lab_test = self.get_object()

        if lab_test.status not in ["Ordered", "Sample Pending"]:
            return Response(
                {"detail": "Sample can only be collected for ordered/pending tests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        collected_by = request.data.get("collected_by")
        if collected_by is not None:
            try:
                collected_by = int(collected_by)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "collected_by must be a valid Nurse ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        sample_collection = SampleCollection.objects.create(
            lab_test=lab_test,
            sample_type=request.data.get("sample_type", "Blood"),
            container_type=request.data.get("container_type", "EDTA"),
            # Lab number: the scanned/entered barcode, else one generated here.
            sample_id=(request.data.get("sample_id") or "").strip()[:50]
            or f"LAB{timezone.localdate():%Y%m%d}-{lab_test.hospital_id}-{lab_test.pk:06d}",
            collected_by_id=collected_by,
            collection_notes=request.data.get("collection_notes", ""),
            barcoded=request.data.get("barcoded", False),
        )

        lab_test.status = "Collected"
        lab_test.collected_at = timezone.now()
        lab_test.save()

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "sample_collection": SampleCollectionSerializer(sample_collection).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff | IsNurse])
    def dispatch_sample(self, request, pk=None):
        """Dispatch sample to lab."""
        lab_test = self.get_object()

        if lab_test.status != "Collected":
            return Response(
                {"detail": "Sample must be collected before dispatch."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_dispatch = SampleDispatch.objects.create(
            lab_test=lab_test,
            dispatched_by=request.user,
            dispatched_at=timezone.now(),
            status="Dispatched",
            dispatch_notes=request.data.get("dispatch_notes", ""),
            external_lab=request.data.get("external_lab", ""),
        )

        lab_test.status = "Dispatched"
        lab_test.dispatched_at = timezone.now()
        lab_test.save()

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "sample_dispatch": SampleDispatchSerializer(sample_dispatch).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def receive_sample(self, request, pk=None):
        """Receive sample in lab."""
        lab_test = self.get_object()

        if lab_test.status != "Dispatched":
            return Response(
                {"detail": "Sample must be dispatched before receiving."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_dispatch = lab_test.sample_dispatch
        sample_dispatch.received_by = request.user
        sample_dispatch.received_at = timezone.now()
        sample_dispatch.status = "Delivered"
        sample_dispatch.save()

        lab_test.status = "Received"
        lab_test.received_at = timezone.now()
        lab_test.save()

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "sample_dispatch": SampleDispatchSerializer(sample_dispatch).data}
        )

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def start_processing(self, request, pk=None):
        """Start processing the sample."""
        lab_test = self.get_object()

        if lab_test.status != "Received":
            return Response(
                {"detail": "Sample must be received before processing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lab_test.status = "Processing"
        lab_test.processed_at = timezone.now()
        lab_test.save()

        return Response(LabTestSerializer(lab_test).data)

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def enter_result(self, request, pk=None):
        """Enter lab result."""
        lab_test = self.get_object()

        if lab_test.status != "Processing":
            return Response(
                {"detail": "Result can only be entered for tests being processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lab_result = LabResult.objects.create(
            lab_test=lab_test,
            result_data=request.data.get("result_data", {}),
            result_text=request.data.get("result_text", ""),
            reference_ranges=request.data.get("reference_ranges", {}),
            abnormal_flags=request.data.get("abnormal_flags", []),
            entered_by=request.user,
            entered_at=timezone.now(),
        )

        lab_test.status = "Result Entered"
        lab_test.result = request.data.get("result_text", "")
        lab_test.save()

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "lab_result": LabResultSerializer(lab_result).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def verify_result(self, request, pk=None):
        """Verify lab result."""
        lab_test = self.get_object()

        if lab_test.status != "Result Entered":
            return Response(
                {"detail": "Result must be entered before verification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lab_result = lab_test.lab_result
        lab_result.is_verified = True
        lab_result.verified_by = request.user
        lab_result.verified_at = timezone.now()
        lab_result.save()

        ResultVerification.objects.create(
            lab_result=lab_result,
            verified_by=request.user,
            action="Verified",
            comments=request.data.get("comments", ""),
        )

        lab_test.status = "Verified"
        lab_test.verified_at = timezone.now()
        lab_test.save()

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "lab_result": LabResultSerializer(lab_result).data}
        )

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def release_result(self, request, pk=None):
        """Release result to doctor/patient."""
        lab_test = self.get_object()

        if lab_test.status != "Verified":
            return Response(
                {"detail": "Result must be verified before release."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lab_result = lab_test.lab_result
        lab_result.is_released = True
        lab_result.released_at = timezone.now()
        lab_result.save()

        lab_test.status = "Released"
        lab_test.released_at = timezone.now()
        lab_test.save()

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "lab_result": LabResultSerializer(lab_result).data}
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel lab test."""
        lab_test = self.get_object()

        if lab_test.status in ["Released", "Verified"]:
            return Response(
                {"detail": "Cannot cancel released or verified test."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lab_test.status = "Cancelled"
        lab_test.save()

        return Response(LabTestSerializer(lab_test).data)


class SampleCollectionViewSet(HospitalScopedViewSet):
    queryset = SampleCollection.objects.all()
    serializer_class = SampleCollectionSerializer
    permission_classes = [IsLabStaff | IsNurse]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(lab_test__hospital_id=hospital_id)
        return qs.select_related("lab_test__hospital", "lab_test__patient", "collected_by")


class SampleDispatchViewSet(HospitalScopedViewSet):
    queryset = SampleDispatch.objects.all()
    serializer_class = SampleDispatchSerializer
    permission_classes = [IsLabStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(lab_test__hospital_id=hospital_id)
        dispatch_status = self.request.query_params.get("status")
        if dispatch_status:
            qs = qs.filter(status=dispatch_status)
        return qs.select_related("lab_test__hospital", "lab_test__patient", "dispatched_by", "received_by")


class LabResultViewSet(HospitalScopedViewSet):
    queryset = LabResult.objects.all()
    serializer_class = LabResultSerializer
    permission_classes = [IsLabStaff | IsDoctor]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(lab_test__hospital_id=hospital_id)
        return qs.select_related("lab_test__hospital", "lab_test__patient", "entered_by", "verified_by")


class ResultVerificationViewSet(HospitalScopedViewSet):
    queryset = ResultVerification.objects.all()
    serializer_class = ResultVerificationSerializer
    permission_classes = [IsLabStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(lab_result__lab_test__hospital_id=hospital_id)
        return qs.select_related("lab_result__lab_test__hospital", "lab_result__lab_test__patient", "verified_by")