"""
/api/services/: OT, ambulance, mortuary, CSSD, laundry (J5, I6), staff leave,
patient feedback and text templates (J6). Every viewset is hospital-scoped;
writes are limited per role below and audited by HospitalScopedViewSet.
"""

from django.db import IntegrityError, transaction
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from hospital.models import Department
from users.permissions import (
    IsAdmin,
    IsDoctor,
    IsHospitalManager,
    IsHospitalMember,
    IsInventoryStaff,
    IsNurse,
    IsReceptionist,
    IsStaffUser,
    get_user_roles,
)
from users.viewsets import HospitalScopedViewSet
from users.models import StaffRole

from . import workflows
from .models import (
    Ambulance,
    AmbulanceTrip,
    LaundryBatch,
    LeaveRequest,
    MortuaryRecord,
    OperatingTheatre,
    OTBooking,
    PatientFeedback,
    SterileSet,
    SterilizationCycle,
    TextTemplate,
)
from .serializers import (
    AmbulanceSerializer,
    AmbulanceTripSerializer,
    LaundryBatchSerializer,
    LeaveRequestSerializer,
    MortuaryRecordSerializer,
    OperatingTheatreSerializer,
    OTBookingSerializer,
    PatientFeedbackSerializer,
    SterileSetSerializer,
    SterilizationCycleSerializer,
    TextTemplateSerializer,
)

MANAGERS = IsAdmin | IsHospitalManager


class _ServiceViewSet(HospitalScopedViewSet):
    """Reads by ``read``; writes and actions by ``write`` unless ``action_permissions`` names the action."""

    read = MANAGERS
    write = MANAGERS
    action_permissions = {}
    http_method_names = ["get", "post", "patch", "head", "options"]
    # Hospital-wide desks (theatre list, ambulance calls, mortuary register)
    # set this False: their staff handle cases outside their own patients, and
    # rows without a registered patient must not vanish from doctors and nurses.
    # Writes still check that the patient belongs to the hospital.
    care_scoped = True

    def get_queryset(self):
        if self.care_scoped:
            return super().get_queryset()
        hospital_ids = self.get_acting_hospital_ids()
        return self._base_queryset().filter(hospital_id__in=hospital_ids) if hospital_ids else self._base_queryset().none()

    def get_permissions(self):
        name = getattr(self, "action", None)
        if name in self.action_permissions:
            return [self.action_permissions[name]()]
        if name in ("list", "retrieve"):
            return [self.read()]
        return [self.write()]

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                super().perform_create(serializer)
        except IntegrityError:
            raise ValidationError("A record with this name or number already exists at this hospital.")

    def _run(self, request, func, verb, *args, **kwargs):
        obj = func(*args, **kwargs)
        self._audit(verb, obj, details={k: v for k, v in request.data.items() if k not in ("released_to_id_last4",)})
        return Response(self.get_serializer(obj).data)

    def _department(self, request, field="department"):
        try:
            return Department.objects.get(pk=int(request.data.get(field)), hospital_id__in=self.get_acting_hospital_ids())
        except (Department.DoesNotExist, TypeError, ValueError):
            raise ValidationError({field: "Choose a department of this hospital."})


class OperatingTheatreViewSet(_ServiceViewSet):
    queryset = OperatingTheatre.objects.all()
    serializer_class = OperatingTheatreSerializer
    read = MANAGERS | IsDoctor | IsNurse


class OTBookingViewSet(_ServiceViewSet):
    queryset = OTBooking.objects.select_related("theatre", "patient", "surgeon")
    serializer_class = OTBookingSerializer
    read = MANAGERS | IsDoctor | IsNurse
    write = MANAGERS | IsDoctor
    action_permissions = {"start": MANAGERS | IsDoctor | IsNurse, "complete": MANAGERS | IsDoctor | IsNurse}
    http_method_names = ["get", "post", "head", "options"]
    care_scoped = False

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        booking = workflows.book_theatre(serializer, created_by=self.request.user, **extra)
        self._audit("create", booking)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._run(request, workflows.move_booking, "started", self.get_object(), "start")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._run(request, workflows.move_booking, "completed", self.get_object(), "complete")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._run(request, workflows.move_booking, "cancelled", self.get_object(), "cancel",
                         reason=request.data.get("reason", ""))


AMBULANCE_DESK = MANAGERS | IsReceptionist | IsNurse


class AmbulanceViewSet(_ServiceViewSet):
    queryset = Ambulance.objects.all()
    serializer_class = AmbulanceSerializer
    read = AMBULANCE_DESK


class AmbulanceTripViewSet(_ServiceViewSet):
    queryset = AmbulanceTrip.objects.select_related("ambulance", "patient")
    serializer_class = AmbulanceTripSerializer
    read = write = AMBULANCE_DESK
    http_method_names = ["get", "post", "head", "options"]
    care_scoped = False

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        self._audit("create", serializer.save(created_by=self.request.user, **extra))

    @action(detail=True, methods=["post"])
    def dispatch_trip(self, request, pk=None):
        trip = self.get_object()
        try:
            ambulance = Ambulance.objects.get(pk=int(request.data.get("ambulance")), hospital_id=trip.hospital_id)
        except (Ambulance.DoesNotExist, TypeError, ValueError):
            raise ValidationError({"ambulance": "Choose an ambulance of this hospital."})
        return self._run(request, workflows.dispatch_trip, "dispatched", trip, ambulance, request.data.get("crew", ""))

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._run(request, workflows.close_trip, "completed", self.get_object(), "complete")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._run(request, workflows.close_trip, "cancelled", self.get_object(), "cancel")


class MortuaryRecordViewSet(_ServiceViewSet):
    queryset = MortuaryRecord.objects.select_related("release_authorised_by")
    serializer_class = MortuaryRecordSerializer
    read = write = MANAGERS | IsDoctor | IsNurse
    action_permissions = {"release": MANAGERS | IsDoctor}
    http_method_names = ["get", "post", "head", "options"]
    care_scoped = False

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        self._audit("create", serializer.save(received_by=self.request.user, **extra))

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        data = request.data
        return self._run(request, workflows.release_body, "released", self.get_object(), request.user,
                         data.get("released_to_name", ""), data.get("released_to_relation", ""),
                         data.get("released_to_id_last4", ""), data.get("police_reference", ""))


CSSD = MANAGERS | IsNurse | IsInventoryStaff


class SterileSetViewSet(_ServiceViewSet):
    queryset = SterileSet.objects.all()
    serializer_class = SterileSetSerializer
    read = write = CSSD


class SterilizationCycleViewSet(_ServiceViewSet):
    queryset = SterilizationCycle.objects.select_related("sterile_set", "issued_to")
    serializer_class = SterilizationCycleSerializer
    read = write = CSSD
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        workflows.check_new_cycle(serializer.validated_data["sterile_set"])
        self._audit("create", serializer.save(recorded_by=self.request.user, **extra))

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        return self._run(request, workflows.issue_set, "issued", self.get_object(), self._department(request, "issued_to"))

    @action(detail=True, methods=["post"], url_path="return")
    def return_set(self, request, pk=None):
        return self._run(request, workflows.return_set, "returned", self.get_object())


class LaundryBatchViewSet(_ServiceViewSet):
    queryset = LaundryBatch.objects.select_related("department")
    serializer_class = LaundryBatchSerializer
    read = write = CSSD
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        self._audit("create", serializer.save(recorded_by=self.request.user, **extra))

    @action(detail=True, methods=["post"], url_path="returned")
    def mark_returned(self, request, pk=None):
        return self._run(request, workflows.laundry_returned, "returned", self.get_object(),
                         request.data.get("quantity_returned"), request.data.get("note", ""))


ANY_STAFF = [IsAuthenticated, IsStaffUser, IsHospitalMember]


class LeaveRequestViewSet(_ServiceViewSet):
    """Everyone applies for their own leave; admins and managers see all and decide."""

    queryset = LeaveRequest.objects.select_related("staff", "decided_by")
    serializer_class = LeaveRequestSerializer
    action_permissions = {"approve": MANAGERS, "reject": MANAGERS}
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if getattr(self, "action", None) in self.action_permissions:
            return super().get_permissions()
        return [permission() for permission in ANY_STAFF]

    def _is_manager(self):
        roles = set()
        for hospital_id in self.get_acting_hospital_ids():
            roles |= set(get_user_roles(self.request.user, hospital_id))
        return bool(roles & {StaffRole.ADMIN, StaffRole.HOSPITAL_MANAGER})

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset if self._is_manager() else queryset.filter(staff=self.request.user)

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        hospital = serializer.validated_data.get("hospital") or extra.get("hospital")
        if hospital is None:
            raise ValidationError({"hospital": "Select a hospital."})
        data = serializer.validated_data
        workflows.check_leave_overlap(self.request.user, hospital.pk, data["start_date"], data["end_date"])
        self._audit("create", serializer.save(staff=self.request.user, **extra))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._run(request, workflows.decide_leave, "approved", self.get_object(), request.user, True,
                         request.data.get("note", ""))

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._run(request, workflows.decide_leave, "rejected", self.get_object(), request.user, False,
                         request.data.get("note", ""))


class PatientFeedbackViewSet(_ServiceViewSet):
    queryset = PatientFeedback.objects.select_related("patient", "department")
    serializer_class = PatientFeedbackSerializer
    write = MANAGERS | IsReceptionist | IsNurse | IsDoctor
    action_permissions = {"respond": MANAGERS}
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        self._audit("create", serializer.save(recorded_by=self.request.user, **extra))

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        close = str(request.data.get("close", "")).lower() in ("1", "true", "yes")
        return self._run(request, workflows.review_feedback, "reviewed", self.get_object(), request.user,
                         request.data.get("response", ""), close)


class TextTemplateViewSet(_ServiceViewSet):
    queryset = TextTemplate.objects.all()
    serializer_class = TextTemplateSerializer
    read = MANAGERS | IsDoctor | IsNurse
    write = MANAGERS | IsDoctor

    def get_queryset(self):
        queryset = super().get_queryset()
        kind = self.request.query_params.get("kind")
        queryset = queryset.filter(kind=kind) if kind else queryset
        return queryset.filter(is_active=True) if self.request.query_params.get("active") else queryset

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        self._audit("create", serializer.save(created_by=self.request.user, **extra))
