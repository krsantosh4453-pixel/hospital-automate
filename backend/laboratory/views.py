from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from doctors.models import Doctor

from audit.services import record_audit
from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    get_linked_patient, get_user_roles, is_active_staff, IsAdmin, IsDoctor, IsHospitalManagerReadOnly, IsLabStaff,
    IsNurse, IsPatientReadOnly,
)
from . import flags
from .models import (
    LabReferenceRange,
    LabResultRejection,
    LabTest,
    LabVerificationPolicy,
    SampleCollection,
    SampleDispatch,
    LabResult,
    ResultVerification,
    ImagingStudy,
)
from .serializers import (
    LabTestSerializer,
    LabTestCreateSerializer,
    LabReferenceRangeSerializer,
    SampleCollectionSerializer,
    SampleDispatchSerializer,
    LabResultSerializer,
    ResultVerificationSerializer,
    ImagingStudySerializer,
)


class LabTestViewSet(HospitalScopedViewSet):
    queryset = LabTest.objects.select_related("hospital", "patient", "doctor", "visit").prefetch_related(
        "sample_collection", "sample_dispatch", "lab_result"
    ).annotate(
        # L-1, in the same query (no prefetch): see LabTestSerializer.
        rejection_total=Count("rejections", distinct=True),
        latest_rejection_reason=Subquery(
            LabResultRejection.objects.filter(lab_test=OuterRef("pk")).order_by("-rejected_at", "-pk")
            .values("reason")[:1]
        ),
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

    def _locked(self, lab_test):
        # Lock the test row only: PostgreSQL cannot lock the nullable side of a join.
        return LabTest.objects.select_for_update(of=("self",)).select_related("visit").get(pk=lab_test.pk)

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def enter_result(self, request, pk=None):
        """
        Enter the result once (BUG-06). It then waits for verification by a
        different user; nobody can overwrite it, and a retry is refused.
        """
        lab_test = self.get_object()
        result_text = str(request.data.get("result_text") or "").strip()
        result_data = request.data.get("result_data") or {}
        if not isinstance(result_data, dict):
            return Response({"detail": "result_data must be an object."}, status=status.HTTP_400_BAD_REQUEST)
        if not result_text and not result_data:
            return Response({"detail": "Enter the result before saving."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            lab_test = self._locked(lab_test)
            if LabResult.objects.filter(lab_test=lab_test).exists():
                return Response(
                    {"detail": "A result is already entered for this test. It cannot be overwritten."},
                    status=status.HTTP_409_CONFLICT,
                )
            if lab_test.status != "Processing":
                return Response(
                    {"detail": "Result can only be entered for tests being processed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # H-14: the server flags the values against the hospital's ranges.
            evaluation = flags.evaluate(
                lab_test.hospital_id, lab_test.name, getattr(lab_test.patient, "gender", ""), result_data,
                client_ranges=request.data.get("reference_ranges"),
                client_flags=request.data.get("abnormal_flags"),
            )
            lab_result = LabResult.objects.create(
                lab_test=lab_test,
                result_data=result_data,
                result_text=result_text,
                reference_ranges=evaluation.reference_ranges,
                abnormal_flags=evaluation.abnormal_flags,
                flag_details=evaluation.details,
                has_critical=evaluation.has_critical,
                entered_by=request.user,
            )
            lab_test.status = "Result Entered"
            lab_test.result = result_text
            lab_test.save(update_fields=["status", "result"])
        record_audit(request, "lab.result.entered", lab_result, hospital=lab_test.hospital_id,
                     details={"abnormal": lab_result.abnormal_flags, "critical": lab_result.has_critical})

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "lab_result": LabResultSerializer(lab_result).data},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _self_verification_policy(hospital_id):
        """The hospital's exception policy when it allows self-verification, else None."""
        return LabVerificationPolicy.objects.filter(hospital_id=hospital_id, allow_self_verification=True).first()

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def verify_result(self, request, pk=None):
        """
        Verify a result (BUG-06): a different authorised user from the one who
        entered it, unless the hospital's policy allows otherwise (then marked
        and audited). The verifier and time are recorded, and the test is
        charged from the price list in the same transaction (BUG-07).
        """
        from billing.charges import capture_lab_test

        lab_test = self.get_object()
        with transaction.atomic():
            lab_test = self._locked(lab_test)
            if lab_test.status != "Result Entered":
                return Response(
                    {"detail": "Result must be entered before verification."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            lab_result = LabResult.objects.select_for_update().get(lab_test=lab_test)
            self_verified = lab_result.entered_by_id is not None and lab_result.entered_by_id == request.user.pk
            policy = self._self_verification_policy(lab_test.hospital_id) if self_verified else None
            if self_verified and policy is None:
                return Response(
                    {"detail": "You entered this result, so a different authorised user must verify it.",
                     "same_user": True},
                    status=status.HTTP_403_FORBIDDEN,
                )
            now = timezone.now()
            lab_result.is_verified = True
            lab_result.verified_by = request.user
            lab_result.verified_at = now
            lab_result.save(update_fields=["is_verified", "verified_by", "verified_at"])
            ResultVerification.objects.create(
                lab_result=lab_result,
                verified_by=request.user,
                action="Verified",
                comments=str(request.data.get("comments") or "").strip(),
                self_verified=self_verified,
            )
            lab_test.status = "Verified"
            lab_test.verified_at = now
            lab_test.save(update_fields=["status", "verified_at"])
            charge = capture_lab_test(lab_test)

        details = {"entered_by": lab_result.entered_by_id, "charged": charge is not None}
        if self_verified:
            details["policy_reason"] = policy.reason
        record_audit(request, "lab.result.self_verified" if self_verified else "lab.result.verified", lab_result,
                     hospital=lab_test.hospital_id, details=details)
        if lab_result.has_critical:
            # H-14: a verified critical value waits on the critical-results
            # worklist until a doctor records that it was acted on.
            record_audit(request, "lab.result.critical", lab_result, hospital=lab_test.hospital_id,
                         details={"doctor": lab_test.doctor_id, "patient": lab_test.patient_id,
                                  "parameters": [d["parameter"] for d in lab_result.flag_details
                                                 if d["flag"] in flags.CRITICAL_FLAGS]})
        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "lab_result": LabResultSerializer(lab_result).data}
        )

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def release_result(self, request, pk=None):
        """Release a verified result to the doctor and the patient."""
        lab_test = self.get_object()
        with transaction.atomic():
            lab_test = self._locked(lab_test)
            lab_result = LabResult.objects.select_for_update().filter(lab_test=lab_test).first()
            if lab_test.status != "Verified" or lab_result is None or not lab_result.is_verified:
                return Response(
                    {"detail": "Result must be verified before release."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            now = timezone.now()
            lab_result.is_released = True
            lab_result.released_at = now
            lab_result.save(update_fields=["is_released", "released_at"])
            lab_test.status = "Released"
            lab_test.released_at = now
            lab_test.save(update_fields=["status", "released_at"])
        record_audit(request, "lab.result.released", lab_result, hospital=lab_test.hospital_id)

        return Response(
            {"lab_test": LabTestSerializer(lab_test).data, "lab_result": LabResultSerializer(lab_result).data}
        )

    @action(detail=True, methods=["post"], permission_classes=[IsLabStaff])
    def reject_result(self, request, pk=None):
        """
        L-1: send a wrong result back before release ({reason}, required).
        The values as entered are kept in LabResultRejection, the result is
        removed and the test returns to Processing so it can be entered
        again (and verified again by a different person). A released result
        cannot be rejected here. Audited.
        """
        reason = str(request.data.get("reason") or "").strip()
        if len(reason) < 5:
            return Response({"reason": "Say why the result is rejected (at least 5 characters)."},
                            status=status.HTTP_400_BAD_REQUEST)
        lab_test = self.get_object()
        with transaction.atomic():
            lab_test = self._locked(lab_test)
            lab_result = LabResult.objects.select_for_update().filter(lab_test=lab_test).first()
            if lab_result is None or lab_test.status not in ("Result Entered", "Verified"):
                return Response({"detail": "Only an entered or verified result that is not released can be rejected."},
                                status=status.HTTP_400_BAD_REQUEST)
            rejection = LabResultRejection.objects.create(
                lab_test=lab_test, result_data=lab_result.result_data, result_text=lab_result.result_text,
                reference_ranges=lab_result.reference_ranges, abnormal_flags=lab_result.abnormal_flags,
                flag_details=lab_result.flag_details, entered_by=lab_result.entered_by,
                entered_at=lab_result.entered_at, was_verified=lab_result.is_verified,
                rejected_by=request.user, reason=reason,
            )
            lab_result.delete()
            lab_test.status = "Processing"
            lab_test.result = ""
            lab_test.verified_at = None
            lab_test.save(update_fields=["status", "result", "verified_at"])
        record_audit(request, "lab.result.rejected", lab_test, hospital=lab_test.hospital_id,
                     details={"reason": reason, "rejection": rejection.pk, "was_verified": rejection.was_verified,
                              "entered_by": rejection.entered_by_id})
        return Response({"lab_test": LabTestSerializer(lab_test).data, "rejection": rejection.pk})

    @action(detail=False, methods=["get"], url_path="critical-results",
            permission_classes=[IsLabStaff | IsDoctor | IsNurse | IsHospitalManagerReadOnly])
    def critical_results(self, request):
        """
        H-14: verified results with a critical value that no doctor has
        acknowledged yet, oldest first. Doctors and nurses see only patients in
        their care (the usual scope); ?mine=1 limits a doctor to tests they ordered.
        """
        qs = (self.get_queryset()
              .filter(status__in=LabTest.DONE_STATUSES, lab_result__has_critical=True,
                      lab_result__critical_acknowledged_at__isnull=True)
              .order_by("verified_at"))
        if request.query_params.get("mine") in ("1", "true", "yes"):
            qs = qs.filter(doctor__user=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(LabTestSerializer(page, many=True).data)
        return Response(LabTestSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDoctor])
    def acknowledge_critical(self, request, pk=None):
        """
        H-14: a doctor records that a critical value was received and what was
        done ({note}, required). Once only; the acknowledgement is audited.
        """
        note = str(request.data.get("note") or "").strip()
        if len(note) < 3:
            return Response({"note": "Write what was done about this critical value."},
                            status=status.HTTP_400_BAD_REQUEST)
        lab_test = self.get_object()
        with transaction.atomic():
            lab_test = self._locked(lab_test)
            lab_result = LabResult.objects.select_for_update().filter(lab_test=lab_test).first()
            if (lab_result is None or not lab_result.has_critical
                    or lab_test.status not in LabTest.DONE_STATUSES):
                return Response({"detail": "This test has no verified critical value."},
                                status=status.HTTP_400_BAD_REQUEST)
            if lab_result.critical_acknowledged_at is not None:
                return Response({"detail": "This critical value is already acknowledged."},
                                status=status.HTTP_409_CONFLICT)
            lab_result.critical_acknowledged_by = request.user
            lab_result.critical_acknowledged_at = timezone.now()
            lab_result.critical_acknowledgement_note = note
            lab_result.save(update_fields=["critical_acknowledged_by", "critical_acknowledged_at",
                                           "critical_acknowledgement_note"])
        record_audit(request, "lab.result.critical_acknowledged", lab_result, hospital=lab_test.hospital_id,
                     details={"note": note})
        return Response({"lab_test": LabTestSerializer(lab_test).data,
                         "lab_result": LabResultSerializer(lab_result).data})

    @action(detail=False, methods=["get", "post"], url_path="verification-policy",
            permission_classes=[IsLabStaff | IsHospitalManagerReadOnly])
    def verification_policy(self, request):
        """
        BUG-06: the selected hospital's exception to maker-checker. Anyone in
        the lab may read it; only an Admin changes it, with a reason.
        POST {allow_self_verification, reason}.
        """
        hospital_ids = self.get_acting_hospital_ids()
        if len(hospital_ids) != 1:
            raise ValidationError({"hospital": "Select one hospital."})
        hospital_id = hospital_ids[0]
        policy = LabVerificationPolicy.objects.filter(hospital_id=hospital_id).first()
        if request.method == "POST":
            if not IsAdmin().has_permission(request, self):
                return Response({"detail": "Only an Admin can change the verification policy."},
                                status=status.HTTP_403_FORBIDDEN)
            allow = str(request.data.get("allow_self_verification", "")).lower() in ("true", "1", "yes")
            reason = str(request.data.get("reason") or "").strip()
            if allow and len(reason) < 10:
                raise ValidationError({"reason": "Say why one person may enter and verify results (at least 10 characters)."})
            policy, _ = LabVerificationPolicy.objects.update_or_create(
                hospital_id=hospital_id,
                defaults={"allow_self_verification": allow, "reason": reason, "updated_by": request.user},
            )
            record_audit(request, "lab.verification_policy.update", policy, hospital=hospital_id,
                         details={"allow_self_verification": allow, "reason": reason})
        return Response({
            "hospital": hospital_id,
            "allow_self_verification": bool(policy and policy.allow_self_verification),
            "reason": policy.reason if policy else "",
            "updated_by": policy.updated_by_id if policy else None,
            "updated_at": policy.updated_at if policy else None,
        })

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


class LabReferenceRangeViewSet(HospitalScopedViewSet):
    """
    H-14: the hospital's reference and critical limits. Clinical staff read
    them; an Admin sets them. A range is never deleted: retiring it
    (is_active=false) keeps results that copied it explainable.

    ?test= (exact name, any case), ?active=1.
    """

    queryset = LabReferenceRange.objects.all()
    serializer_class = LabReferenceRangeSerializer
    permission_classes = [IsLabStaff | IsDoctor | IsNurse | IsHospitalManagerReadOnly]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if getattr(self, "action", None) in ("create", "partial_update"):
            return [IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        test_name = (self.request.query_params.get("test") or "").strip()
        if test_name:
            qs = qs.filter(test_name__iexact=test_name)
        if self.request.query_params.get("active") in ("1", "true", "yes"):
            qs = qs.filter(is_active=True)
        return qs

    def _save(self, save):
        from django.db import IntegrityError

        try:
            with transaction.atomic():
                return save()
        except IntegrityError:
            raise ValidationError(
                "An active range for this test, parameter and sex already exists. Retire it first.")

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        instance = self._save(lambda: serializer.save(created_by=self.request.user, **extra))
        self._audit("create", instance)

    def perform_update(self, serializer):
        self._save(lambda: super(LabReferenceRangeViewSet, self).perform_update(serializer))


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
    """
    Read only (BUG-06): a result is written once by enter_result and changed
    only by verify/release, never by a direct PUT, PATCH or DELETE here.
    """

    queryset = LabResult.objects.all()
    serializer_class = LabResultSerializer
    permission_classes = [IsLabStaff | IsDoctor]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(lab_test__hospital_id=hospital_id)
        return qs.select_related("lab_test__hospital", "lab_test__patient", "entered_by", "verified_by")


class ResultVerificationViewSet(HospitalScopedViewSet):
    """Read only (BUG-06): verifications are recorded by verify_result."""

    queryset = ResultVerification.objects.all()
    serializer_class = ResultVerificationSerializer
    permission_classes = [IsLabStaff]
    http_method_names = ["get", "head", "options"]

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
