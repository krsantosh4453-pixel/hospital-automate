from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery

from doctors.models import Doctor
from django.utils import timezone
from datetime import datetime, timedelta

from audit.services import record_audit
from config.hospital_time import hospital_now, hospital_today
from users.viewsets import HospitalScopedViewSet
from .frequency import ONCE, PRN, FrequencyError, parse_frequency
from . import scheduling
from .scheduling import AT, ScheduleError
from users.permissions import IsAdmin, IsHospitalManager, IsNurse, IsDoctor
from .models import (
    Nurse,
    NursingAssessment,
    NursingNote,
    CareTask,
    MAR,
    MARAdministration,
    MedicationRound,
    NurseWardAssignment,
    PatientAssignment,
)
from .serializers import (
    NurseSerializer,
    NursingAssessmentSerializer,
    NursingNoteSerializer,
    CareTaskSerializer,
    MARSerializer,
    MARAdministrationSerializer,
    MedicationRoundSerializer,
    NurseWardAssignmentSerializer,
    PatientAssignmentSerializer,
)


NO_ORDER = "No active doctor's order for this medicine. Ask the doctor to order or restart it."
NOT_YOUR_PROFILE = "Recorded under your own nurse profile; another nurse cannot be named."
# H-02: how long before its scheduled time a dose may be recorded as given.
# Pending clinical sign-off of the value (CLINICAL_SAFETY_REVIEW_PACK.md section 1).
DEFAULT_EARLY_WINDOW_MINUTES = 60


def early_window():
    return timedelta(minutes=getattr(settings, "MAR_EARLY_ADMINISTRATION_MINUTES", DEFAULT_EARLY_WINDOW_MINUTES))


def is_prn(frequency_text):
    try:
        return parse_frequency(frequency_text).kind == PRN
    except FrequencyError:
        return False


def not_yet_due(admin, now, window):
    """A refusal when ``admin`` is more than ``window`` before its time, else None."""
    if admin.scheduled_time <= now + window:
        return None
    due = admin.scheduled_time.astimezone(hospital_now().tzinfo).strftime("%d %b %H:%M")
    return Response({"detail": f"This dose is due at {due}. It can be recorded from "
                               f"{int(window.total_seconds() // 60)} minutes before then; if it is needed "
                               f"earlier, the doctor changes the order."},
                    status=status.HTTP_400_BAD_REQUEST)


def own_nurse_profile(user, hospital_id):
    """The requester's own Nurse profile at ``hospital_id``, or None."""
    if hospital_id is None:
        return None
    return Nurse.objects.filter(user=user, hospital_id=hospital_id).first()


def recording_nurse(user, hospital_id, named, field):
    """
    The nurse a record is written under: always the requester's own profile
    (None for a doctor or an unlinked login). Naming any other nurse is
    refused, so a record never shows someone else as its author.
    """
    own = own_nurse_profile(user, hospital_id)
    named_id = getattr(named, "pk", named)
    if named_id not in (None, "") and (own is None or str(own.pk) != str(named_id)):
        raise ValidationError({field: NOT_YOUR_PROFILE})
    return own


class OwnNurseRecordMixin:
    """Nursing notes and assessments carry their author's own nurse profile."""

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        hospital = serializer.validated_data.get("hospital") or extra.get("hospital")
        nurse = recording_nurse(self.request.user, getattr(hospital, "pk", hospital),
                                serializer.validated_data.get("nurse"), "nurse")
        instance = serializer.save(nurse=nurse, **extra)
        self._audit("create", instance)

    def perform_update(self, serializer):
        named = serializer.validated_data.get("nurse", serializer.instance.nurse)
        if getattr(named, "pk", named) != serializer.instance.nurse_id:
            raise ValidationError({"nurse": "The author of a nursing record cannot be changed."})
        super().perform_update(serializer)


def audit_dose(request, admin):
    """Who recorded which outcome for which dose."""
    record_audit(request, f"nurses.maradministration.{admin.status.lower()}", admin,
                 hospital=admin.mar.hospital_id,
                 details={"mar": admin.mar_id, "medicine": admin.mar.medicine_name, "status": admin.status,
                          "dose_given": admin.dose_given, "notes": admin.notes})


class NurseViewSet(HospitalScopedViewSet):
    queryset = Nurse.objects.select_related("hospital")
    serializer_class = NurseSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsNurse]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "department", "shift", "qualification"]
    ordering_fields = ["name", "department", "shift", "status", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department=department)

        return queryset


class NursingAssessmentViewSet(OwnNurseRecordMixin, HospitalScopedViewSet):
    queryset = NursingAssessment.objects.select_related("hospital", "patient", "admission", "nurse")
    serializer_class = NursingAssessmentSerializer
    permission_classes = [IsNurse | IsDoctor]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        admission_id = self.request.query_params.get("admission")
        if admission_id:
            qs = qs.filter(admission_id=admission_id)
        return qs


class NursingNoteViewSet(OwnNurseRecordMixin, HospitalScopedViewSet):
    queryset = NursingNote.objects.select_related("hospital", "patient", "admission", "nurse")
    serializer_class = NursingNoteSerializer
    permission_classes = [IsNurse | IsDoctor]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        admission_id = self.request.query_params.get("admission")
        if admission_id:
            qs = qs.filter(admission_id=admission_id)
        return qs


class CareTaskViewSet(HospitalScopedViewSet):
    queryset = CareTask.objects.select_related("hospital", "patient", "admission", "assigned_nurse", "completed_by")
    serializer_class = CareTaskSerializer
    permission_classes = [IsNurse | IsDoctor]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        admission_id = self.request.query_params.get("admission")
        if admission_id:
            qs = qs.filter(admission_id=admission_id)
        assigned_nurse_id = self.request.query_params.get("assigned_nurse")
        if assigned_nurse_id:
            qs = qs.filter(assigned_nurse_id=assigned_nurse_id)
        task_status = self.request.query_params.get("status")
        if task_status:
            qs = qs.filter(status=task_status)
        # Filter by date range
        shift_date = self.request.query_params.get("shift_date")
        if shift_date:
            qs = qs.filter(scheduled_at__date=shift_date)
        return qs

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Mark task as in progress."""
        task = self.get_object()
        if task.status != "Pending":
            return Response(
                {"detail": "Only pending tasks can be started."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = "In Progress"
        task.started_at = timezone.now()
        task.save()
        return Response(CareTaskSerializer(task).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark task as completed."""
        task = self.get_object()
        if task.status not in ["Pending", "In Progress"]:
            return Response(
                {"detail": "Task cannot be completed from current status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = "Completed"
        task.completed_at = timezone.now()
        task.completed_by = recording_nurse(request.user, task.hospital_id,
                                            request.data.get("completed_by"), "completed_by")
        task.notes = request.data.get("notes", task.notes)
        task.save()
        return Response(CareTaskSerializer(task).data)

    @action(detail=False, methods=["get"])
    def my_tasks(self, request):
        """Get tasks assigned to current nurse for today."""
        nurse_id = request.query_params.get("nurse_id")
        if not nurse_id:
            return Response(
                {"detail": "nurse_id query parameter required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        qs = self.get_queryset().filter(
            assigned_nurse_id=nurse_id,
            scheduled_at__date=today,
            status__in=["Pending", "In Progress"]
        ).order_by("scheduled_at")

        return Response(CareTaskSerializer(qs, many=True).data)


class MARViewSet(HospitalScopedViewSet):
    """
    Medication orders. Only a doctor writes, changes, stops or schedules one;
    nurses read them and record doses given under them.
    """
    queryset = MAR.objects.select_related("hospital", "patient", "admission", "prescription", "prescription_item",
                                          "ordered_by").annotate(
        # The ordering doctor's profile name at this hospital (MAR "Ordered by").
        ordered_by_doctor_name=Subquery(
            Doctor.objects.filter(user=OuterRef("ordered_by"), hospital=OuterRef("hospital"))
            .values("name")[:1]
        ),
    )
    serializer_class = MARSerializer
    permission_classes = [IsNurse | IsDoctor]
    DOCTOR_ONLY_ACTIONS = {"create", "update", "partial_update", "destroy", "generate_schedule", "schedule_preview"}

    def get_permissions(self):
        if getattr(self, "action", None) in self.DOCTOR_ONLY_ACTIONS:
            return [IsDoctor()]
        return super().get_permissions()

    def perform_create(self, serializer):
        extra = self._check_tenancy(serializer.validated_data)
        # A first dose sent with the order is scheduled in the same
        # transaction: a refused time leaves no order without doses behind.
        wants_schedule = "first_dose" in self.request.data
        mode = serializer.validated_data.pop("first_dose", None)
        when = serializer.validated_data.pop("first_dose_at", None)
        with transaction.atomic():
            instance = serializer.save(ordered_by=self.request.user, **extra)
            self._audit("create", instance)
            if wants_schedule and parse_frequency(instance.frequency).kind != PRN:
                # A ScheduleError leaves the atomic block, so the order is rolled back;
                # create() turns it into the same 400 body as generate_schedule.
                self._schedule(instance, parse_frequency(instance.frequency), mode, when)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ScheduleError as exc:
            return Response({"first_dose": [str(exc)], "first_dose_required": exc.needs_choice},
                            status=status.HTTP_400_BAD_REQUEST)

    def _schedule(self, mar, frequency, mode, when, start_day=None):
        """Replace the order's future untouched doses with the schedule from its first dose."""
        first = scheduling.resolve_first_dose(
            frequency, mode, when, scheduling.round_times(mar.hospital_id),
            max(filter(None, [mar.start_date, start_day])) if (mar.start_date or start_day) else None,
            mar.end_date,
        )
        # Only future doses nobody has acted on are replaced; recorded outcomes stay.
        MARAdministration.objects.filter(mar=mar, is_prn=False, scheduled_time__gt=timezone.now(),
                                         status=MARAdministration.SCHEDULED).delete()
        times = scheduling.dose_times(frequency, first.at, mar.end_date)
        if frequency.kind == ONCE:
            # A single (STAT) dose: once anything is recorded for it, no second one is scheduled.
            times = [] if mar.administrations.exists() else times[:1]
        for when_ in times:
            MARAdministration.objects.get_or_create(
                mar=mar, scheduled_time=when_, is_prn=False,
                defaults={"status": MARAdministration.SCHEDULED},
            )
        record_audit(self.request, "nurses.mar.schedule_generated", mar,
                     details={"first_dose_mode": first.mode, "first_dose": first.at.isoformat(),
                              "doses": len(times)})
        return first, times

    @staticmethod
    def _first_dose_request(data):
        """(mode, time, earliest day) from the request; the old ``start_date`` still works."""
        mode = data.get("first_dose") or None
        when = data.get("first_dose_at") or None
        start_day = None
        legacy = data.get("start_date")
        if mode is None and legacy:
            text = str(legacy)
            if "T" in text or " " in text:
                mode, when = AT, text  # a full date-time is a chosen first dose
            else:
                # A bare date used to mean midnight (the overdue defect); it now
                # only says the doses start on that day.
                start_day = scheduling.as_day(text)
        return mode, when, start_day

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        admission_id = self.request.query_params.get("admission")
        if admission_id:
            qs = qs.filter(admission_id=admission_id)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def generate_schedule(self, request, pk=None):
        """
        Schedule the order's doses. Body: ``first_dose`` (now | at | next_round),
        ``first_dose_at`` for ``at``; without them the safe default applies (see
        nurses/scheduling.py). Never schedules a first dose in the past.
        """
        mar = self.get_object()
        # Serialise parallel schedule requests for one order.
        mar = MAR.objects.select_for_update().get(pk=mar.pk)
        if not mar.is_active or mar.entered_in_error_at is not None:
            return Response({"detail": NO_ORDER}, status=status.HTTP_400_BAD_REQUEST)
        # H-01: a frequency is understood exactly or refused, never guessed.
        try:
            frequency = parse_frequency(mar.frequency)
        except FrequencyError as exc:
            return Response({"detail": f"Frequency: {exc}"}, status=status.HTTP_400_BAD_REQUEST)
        if frequency.kind == PRN:
            return Response({"detail": "PRN medications do not have fixed schedules."})
        try:
            mode, when, start_day = self._first_dose_request(request.data)
            self._schedule(mar, frequency, mode, when, start_day=start_day)
        except (ScheduleError, ValueError) as exc:
            return Response({"first_dose": [str(exc)],
                             "first_dose_required": getattr(exc, "needs_choice", False)},
                            status=status.HTTP_400_BAD_REQUEST)

        # Return upcoming administrations
        upcoming = mar.administrations.filter(
            scheduled_time__gte=timezone.now(),
            scheduled_time__lte=timezone.now() + timedelta(days=1)
        ).order_by("scheduled_time")

        return Response(MARAdministrationSerializer(upcoming, many=True).data)

    @action(detail=False, methods=["post"], url_path="schedule-preview")
    def schedule_preview(self, request):
        """
        POST {hospital, frequency, start_date?, end_date?, first_dose?, first_dose_at?}:
        the first dose and the doses after it, without saving anything, so the
        doctor reviews the schedule before ordering.
        """
        data = request.data
        try:
            hospital_id = int(data.get("hospital"))
        except (TypeError, ValueError):
            return Response({"hospital": ["Required."]}, status=status.HTTP_400_BAD_REQUEST)
        if hospital_id not in set(self.get_acting_hospital_ids()):
            return Response({"detail": "You do not have access to this hospital."}, status=status.HTTP_403_FORBIDDEN)
        try:
            frequency = parse_frequency(data.get("frequency"))
        except FrequencyError as exc:
            return Response({"frequency": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        rounds = scheduling.round_times(hospital_id)
        base = {"rounds": [r.strftime("%H:%M") for r in rounds], "prn": frequency.kind == PRN}
        if frequency.kind == PRN:
            return Response({**base, "first_dose_mode": None, "first_dose_at": None, "doses": [], "dose_count": 0})
        try:
            start_day = scheduling.as_day(data.get("start_date"))
            end_day = scheduling.as_day(data.get("end_date"))
            first = scheduling.resolve_first_dose(frequency, data.get("first_dose") or None,
                                                  data.get("first_dose_at") or None, rounds, start_day, end_day)
        except (ScheduleError, ValueError) as exc:
            return Response({**base, "first_dose": [str(exc)],
                             "first_dose_required": getattr(exc, "needs_choice", False)},
                            status=status.HTTP_400_BAD_REQUEST)
        times = scheduling.dose_times(frequency, first.at, end_day)
        if frequency.kind == ONCE:
            times = times[:1]
        return Response({**base, "first_dose_mode": first.mode, "first_dose_at": first.at.isoformat(),
                         "doses": [t.isoformat() for t in times[:6]], "dose_count": len(times)})

    @action(detail=True, methods=["post"])
    def prn(self, request, pk=None):
        """Record an as-needed (PRN) dose given now."""
        from .prn_limits import prn_limit_refusal

        mar = self.get_object()
        if not is_prn(mar.frequency):
            return Response({"detail": "This order is not PRN; use the scheduled doses."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not mar.in_force(hospital_today()):
            return Response({"detail": NO_ORDER}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            # H-10: the order row is locked, so two nurses recording at the
            # same moment cannot both pass the interval or daily limit.
            mar = MAR.objects.select_for_update().get(pk=mar.pk)
            now = timezone.now()
            refusal = prn_limit_refusal(mar, now)
            if refusal is None:
                admin = MARAdministration.objects.create(
                    mar=mar, scheduled_time=now, administered_time=now, status=MARAdministration.ADMINISTERED,
                    is_prn=True, recorded_by=request.user,
                    dose_given=request.data.get("dose_given", mar.dose),
                    route_given=request.data.get("route_given", mar.route),
                    notes=request.data.get("notes", ""),
                )
        if refusal is not None:
            record_audit(request, "nurses.mar.prn_refused", mar, hospital=mar.hospital_id,
                         details={"medicine": mar.medicine_name, "reason": refusal["code"]})
            return Response(refusal, status=status.HTTP_409_CONFLICT)
        audit_dose(request, admin)
        return Response(MARAdministrationSerializer(admin).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def due_medications(self, request):
        """Get medications due for administration in the next hour."""
        hospital_id = request.query_params.get("hospital")
        if not hospital_id:
            return Response(
                {"detail": "hospital query parameter required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        window_end = now + timedelta(hours=1)

        # Everything still due up to an hour ahead, including overdue (delayed) doses.
        administrations = MARAdministration.objects.filter(
            mar__hospital_id__in=self.get_acting_hospital_ids(),
            mar__hospital_id=hospital_id,
            mar__is_active=True,
            scheduled_time__lte=window_end,
            status=MARAdministration.SCHEDULED,
        ).select_related(
            "mar__patient", "mar__admission", "administered_by"
        ).order_by("scheduled_time")

        return Response(MARAdministrationSerializer(administrations, many=True).data)


class MARAdministrationViewSet(HospitalScopedViewSet):
    queryset = MARAdministration.objects.select_related("mar__patient", "mar__admission", "administered_by")
    serializer_class = MARAdministrationSerializer
    permission_classes = [IsNurse | IsDoctor]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(mar__hospital_id=hospital_id)
        mar_id = self.request.query_params.get("mar")
        if mar_id:
            qs = qs.filter(mar_id=mar_id)
        admin_status = self.request.query_params.get("status")
        if admin_status:
            qs = qs.filter(status=admin_status)
        return qs

    def get_permissions(self):
        if getattr(self, "action", None) == "exclude":
            return [IsDoctor()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Doses come from MAR generate_schedule/ or prn/; outcomes from the dose actions."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _nurse(self, request, admin):
        """The requester's own nurse profile; naming another nurse is refused."""
        return recording_nurse(request.user, admin.mar.hospital_id,
                               request.data.get("administered_by"), "administered_by")

    def _locked_dose(self):
        """
        This URL's dose, row-locked until the request's transaction ends, so
        two nurses recording the same dose at once cannot both pass the
        "still Scheduled" check: the second sees the first one's outcome.
        """
        dose = self.get_object()
        return MARAdministration.objects.select_for_update(of=("self",)).select_related("mar").get(pk=dose.pk)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def exclude(self, request, pk=None):
        """Administration Excluded: a doctor's decision not to give this dose."""
        admin = self._locked_dose()
        if admin.status != MARAdministration.SCHEDULED:
            return Response({"detail": f"Already {admin.status.lower()}."}, status=status.HTTP_400_BAD_REQUEST)
        reason = str(request.data.get("reason") or "").strip()
        if not reason:
            return Response({"detail": "A reason is required."}, status=status.HTTP_400_BAD_REQUEST)
        admin.status = "Excluded"
        admin.notes = reason
        admin.administered_time = timezone.now()
        admin.recorded_by = request.user
        admin.save()
        audit_dose(request, admin)
        return Response(MARAdministrationSerializer(admin).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def administer(self, request, pk=None):
        """Record medication administration."""
        admin = self._locked_dose()

        if admin.status != MARAdministration.SCHEDULED:
            return Response(
                {"detail": f"Already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not admin.mar.in_force(hospital_today()):
            return Response({"detail": NO_ORDER}, status=status.HTTP_400_BAD_REQUEST)
        too_early = not_yet_due(admin, timezone.now(), early_window())
        if too_early:
            return too_early

        admin.administered_time = timezone.now()
        admin.administered_by = self._nurse(request, admin)
        admin.recorded_by = request.user
        admin.dose_given = request.data.get("dose_given", admin.mar.dose)
        admin.route_given = request.data.get("route_given", admin.mar.route)
        admin.site = request.data.get("site", "")
        admin.notes = request.data.get("notes", "")
        admin.status = "Administered"
        admin.save()
        audit_dose(request, admin)

        return Response(MARAdministrationSerializer(admin).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def hold(self, request, pk=None):
        """Hold medication."""
        admin = self._locked_dose()

        if admin.status != MARAdministration.SCHEDULED:
            return Response(
                {"detail": f"Cannot hold - already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin.status = "Held"
        admin.reason_held = request.data.get("reason", "")
        admin.notes = request.data.get("notes", "")
        admin.administered_by = self._nurse(request, admin)
        admin.recorded_by = request.user
        admin.administered_time = timezone.now()
        admin.save()
        audit_dose(request, admin)

        return Response(MARAdministrationSerializer(admin).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def refuse(self, request, pk=None):
        """Patient refused medication."""
        admin = self._locked_dose()

        if admin.status != MARAdministration.SCHEDULED:
            return Response(
                {"detail": f"Cannot refuse - already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin.status = "Refused"
        admin.reason_refused = request.data.get("reason", "")
        admin.notes = request.data.get("notes", "")
        admin.administered_by = self._nurse(request, admin)
        admin.recorded_by = request.user
        admin.administered_time = timezone.now()
        admin.save()
        audit_dose(request, admin)

        return Response(MARAdministrationSerializer(admin).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def mark_missed(self, request, pk=None):
        """Mark as missed."""
        admin = self._locked_dose()

        if admin.status != MARAdministration.SCHEDULED:
            return Response(
                {"detail": f"Cannot mark missed - already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # A dose cannot be missed before it is due.
        not_due = not_yet_due(admin, timezone.now(), timedelta(0))
        if not_due:
            return not_due

        admin.status = "Missed"
        admin.notes = request.data.get("notes", "Missed dose")
        admin.administered_time = timezone.now()
        admin.recorded_by = request.user
        admin.save()
        audit_dose(request, admin)

        return Response(MARAdministrationSerializer(admin).data)


class NurseWardAssignmentViewSet(HospitalScopedViewSet):
    """Ward duty roster: admins assign; nurses read it."""
    queryset = NurseWardAssignment.objects.select_related("nurse", "ward")
    serializer_class = NurseWardAssignmentSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsNurse]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [(IsAdmin | IsHospitalManager)()]

    def get_queryset(self):
        qs = super().get_queryset()
        for param in ("nurse", "ward", "shift", "shift_date"):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{param: value})
        return qs


class PatientAssignmentViewSet(HospitalScopedViewSet):
    queryset = PatientAssignment.objects.select_related("hospital", "nurse", "patient", "admission")
    serializer_class = PatientAssignmentSerializer
    permission_classes = [IsNurse | IsAdmin | IsHospitalManager]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        nurse_id = self.request.query_params.get("nurse")
        if nurse_id:
            qs = qs.filter(nurse_id=nurse_id)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        shift_date = self.request.query_params.get("shift_date")
        if shift_date:
            qs = qs.filter(shift_date=shift_date)
        shift = self.request.query_params.get("shift")
        if shift:
            qs = qs.filter(shift=shift)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    @action(detail=False, methods=["post"])
    def assign_patients(self, request):
        """Bulk assign patients to a nurse for a shift."""
        nurse_id = request.data.get("nurse_id")
        patient_ids = request.data.get("patient_ids", [])
        shift = request.data.get("shift")
        shift_date = request.data.get("shift_date")
        hospital_id = request.data.get("hospital")

        if not all([nurse_id, patient_ids, shift, shift_date, hospital_id]):
            return Response(
                {"detail": "nurse_id, patient_ids, shift, shift_date, and hospital are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        for patient_id in patient_ids:
            assignment, created_flag = PatientAssignment.objects.get_or_create(
                nurse_id=nurse_id,
                patient_id=patient_id,
                shift=shift,
                shift_date=shift_date,
                hospital_id=hospital_id,
                defaults={"is_active": True}
            )
            if created_flag:
                created.append(assignment)

        return Response(
            PatientAssignmentSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED
        )

class MedicationRoundViewSet(HospitalScopedViewSet):
    """
    A hospital's medication rounds. Ward staff read them; only an Admin or a
    Hospital Manager adds one or switches it off (rows are never deleted, so
    the history of which rounds existed stays).
    """
    queryset = MedicationRound.objects.select_related("hospital")
    serializer_class = MedicationRoundSerializer
    permission_classes = [IsNurse | IsDoctor | IsAdmin | IsHospitalManager]
    http_method_names = ["get", "post", "patch", "head", "options"]
    WRITE_ACTIONS = {"create", "partial_update"}

    def get_permissions(self):
        if getattr(self, "action", None) in self.WRITE_ACTIONS:
            return [(IsAdmin | IsHospitalManager)()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        if self.request.query_params.get("active") == "true":
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        hospital = serializer.validated_data.get("hospital")
        if hospital is not None and MedicationRound.objects.filter(
                hospital=hospital, time=serializer.validated_data["time"], is_active=True).exists():
            raise ValidationError({"time": ["This hospital already has an active round at that time."]})
        extra = self._check_tenancy(serializer.validated_data)
        instance = serializer.save(created_by=self.request.user, **extra)
        self._audit("create", instance)

    def perform_update(self, serializer):
        # Only switching a round off or on (or relabelling) is allowed; the time is fixed.
        if "time" in serializer.validated_data or "hospital" in serializer.validated_data:
            raise ValidationError({"time": ["Add a new round instead of moving one."]})
        super().perform_update(serializer)
