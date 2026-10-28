from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from doctors.models import Doctor

from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    get_linked_patient, get_user_roles, is_active_staff, IsDoctor, IsHospitalManagerReadOnly, IsLabStaff, IsNurse,
    IsPatientReadOnly,
)
from .models import (
    LabTest,
    SampleCollection,
    SampleDispatch,
    LabResult,
    ResultVerification,
    ImagingStudy,
)
from .serializers import (
    LabTestSerializer,
    LabTestCreateSerializer,
    SampleCollectionSerializer,
    SampleDispatchSerializer,
    LabResultSerializer,
    ResultVerificationSerializer,
    ImagingStudySerializer,
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

    @action(detail=False, methods=["get"], permission_classes=[IsLabStaff | IsNurse])
    def by_sample(self, request):
        """Barcode scan (F6): the order whose sample carries ?sample_id=, in this hospital only."""
        sample_id = (request.query_params.get("sample_id") or "").strip()
        if not sample_id:
            return Response({"detail": "Scan or type a sample number."}, status=status.HTTP_400_BAD_REQUEST)
        lab_test = self.get_queryset().filter(sample_collection__sample_id__iexact=sample_id).first()
        if lab_test is None:
            return Response({"detail": "No sample with this number at this hospital."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LabTestSerializer(lab_test).data)

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

class ImagingStudyViewSet(HospitalScopedViewSet):
    """
    Radiology / imaging (G4): Doctor orders, Lab Staff (technician) schedules and
    performs, a Doctor reports and signs. Rows are never edited or deleted; a
    study is cancelled instead. Patients see only signed reports.
    """

    queryset = ImagingStudy.objects.select_related("hospital", "patient", "ordered_by", "reported_by")
    serializer_class = ImagingStudySerializer
    permission_classes = [IsDoctor | IsLabStaff | IsNurse | IsPatientReadOnly | IsHospitalManagerReadOnly]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsDoctor()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if get_linked_patient(self.request.user) and not is_active_staff(self.request.user):
            return qs.filter(status=ImagingStudy.Status.REPORTED)
        visible = Q(pk__in=qs.values("pk")) | Q(pk__in=self._reporting_worklist().values("pk"))
        qs = ImagingStudy.objects.select_related(
            "hospital", "patient", "ordered_by", "reported_by"
        ).filter(visible)
        for param, field in (("patient", "patient_id"), ("status", "status"), ("modality", "modality")):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    def _reporting_worklist(self):
        # The reporting radiologist is rarely the treating doctor, so studies
        # awaiting a report (and the ones they signed) stay visible to doctors.
        doctor_ids = Doctor.objects.filter(user=self.request.user).values("pk")
        # The doctor role must be held in that hospital, never the union of roles.
        hospital_ids = [
            h for h in self.get_acting_hospital_ids()
            if set(get_user_roles(self.request.user, h)) & set(IsDoctor.required_roles)
        ]
        if not hospital_ids:
            return ImagingStudy.objects.none()
        return ImagingStudy.objects.filter(hospital_id__in=hospital_ids).filter(
            Q(status=ImagingStudy.Status.PERFORMED) | Q(reported_by__in=doctor_ids)
        )

    def _doctor_at(self, hospital):
        doctor = Doctor.objects.filter(user=self.request.user, hospital=hospital).first()
        if doctor is None:
            raise ValidationError("Only a doctor of this hospital can do this; your account has no doctor profile here.")
        return doctor

    def perform_create(self, serializer):
        from billing.services import new_reference

        extra = self._check_tenancy(serializer.validated_data)
        hospital = serializer.validated_data.get("hospital") or extra.get("hospital")
        if hospital is None:
            raise ValidationError({"hospital": "Choose the hospital."})
        extra["ordered_by"] = self._doctor_at(hospital)
        study = serializer.save(accession_number=new_reference("RAD"), **extra)
        self._audit("create", study)

    def _move(self, request, allowed_from, to, **fields):
        study = self.get_object()
        if study.status not in allowed_from:
            return Response(
                {"detail": f"A study that is {study.status.lower()} cannot be {to.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        study.status = to
        for name, value in fields.items():
            setattr(study, name, value)
        study.save()
        self._audit(to.lower(), study)
        return Response(self.get_serializer(study).data)

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def schedule(self, request, pk=None):
        when = parse_datetime(str(request.data.get("scheduled_for") or ""))
        if when is None:
            raise ValidationError({"scheduled_for": "Give the date and time of the appointment."})
        return self._move(request, [ImagingStudy.Status.ORDERED, ImagingStudy.Status.SCHEDULED],
                          ImagingStudy.Status.SCHEDULED, scheduled_for=when)

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def perform(self, request, pk=None):
        return self._move(request, [ImagingStudy.Status.ORDERED, ImagingStudy.Status.SCHEDULED],
                          ImagingStudy.Status.PERFORMED, performed_at=timezone.now(), performed_by=request.user,
                          technician_notes=str(request.data.get("technician_notes", "")).strip())

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def report(self, request, pk=None):
        """Sign the report. Findings and impression are required; the study then locks."""
        study = self.get_object()
        findings = str(request.data.get("findings", "")).strip()
        impression = str(request.data.get("impression", "")).strip()
        if not findings or not impression:
            raise ValidationError({"impression": "Write both the findings and the impression."})
        return self._move(request, [ImagingStudy.Status.PERFORMED], ImagingStudy.Status.REPORTED,
                          findings=findings, impression=impression,
                          reported_by=self._doctor_at(study.hospital), reported_at=timezone.now())

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def cancel(self, request, pk=None):
        return self._move(request, [ImagingStudy.Status.ORDERED, ImagingStudy.Status.SCHEDULED],
                          ImagingStudy.Status.CANCELLED)
