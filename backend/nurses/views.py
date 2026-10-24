from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsNurse, IsDoctor
from .models import (
    Nurse,
    NursingAssessment,
    NursingNote,
    CareTask,
    MAR,
    MARAdministration,
    PatientAssignment,
)
from .serializers import (
    NurseSerializer,
    NursingAssessmentSerializer,
    NursingNoteSerializer,
    CareTaskSerializer,
    MARSerializer,
    MARAdministrationSerializer,
    PatientAssignmentSerializer,
)


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


class NursingAssessmentViewSet(HospitalScopedViewSet):
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


class NursingNoteViewSet(HospitalScopedViewSet):
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
        task.completed_by_id = request.data.get("completed_by")
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
    queryset = MAR.objects.select_related("hospital", "patient", "admission", "prescription", "prescription_item")
    serializer_class = MARSerializer
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
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    @action(detail=True, methods=["post"])
    def generate_schedule(self, request, pk=None):
        """Generate MAR administration schedule based on frequency."""
        mar = self.get_object()

        # Delete existing future administrations
        MARAdministration.objects.filter(
            mar=mar,
            scheduled_time__gt=timezone.now(),
            status__in=["Administered", "Held", "Refused", "Missed"]
        ).delete()

        # Parse frequency (e.g., "Q8H", "BID", "TID", "QID", "Daily", "PRN")
        frequency = mar.frequency.upper()
        start_date = request.data.get("start_date")
        if start_date:
            start_dt = timezone.datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        else:
            start_dt = timezone.now()

        end_date = mar.end_date
        if not end_date:
            end_date = start_dt.date() + timedelta(days=7)

        administrations = []
        current_dt = start_dt

        # Simple frequency parsing
        interval_hours = 24
        if "Q" in frequency and "H" in frequency:
            # Q8H, Q6H, etc.
            import re
            match = re.search(r"Q(\d+)H", frequency)
            if match:
                interval_hours = int(match.group(1))
        elif "BID" in frequency:
            interval_hours = 12
        elif "TID" in frequency:
            interval_hours = 8
        elif "QID" in frequency:
            interval_hours = 6
        elif "DAILY" in frequency or "OD" in frequency:
            interval_hours = 24
        elif "PRN" in frequency:
            # PRN - as needed, no fixed schedule
            return Response({"detail": "PRN medications do not have fixed schedules."})

        while current_dt.date() <= end_date:
            MARAdministration.objects.get_or_create(
                mar=mar,
                scheduled_time=current_dt,
                defaults={"status": "Administered"}
            )
            current_dt += timedelta(hours=interval_hours)

        # Return upcoming administrations
        upcoming = mar.administrations.filter(
            scheduled_time__gte=timezone.now(),
            scheduled_time__lte=timezone.now() + timedelta(days=1)
        ).order_by("scheduled_time")

        return Response(MARAdministrationSerializer(upcoming, many=True).data)

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
        window_start = now - timedelta(minutes=30)
        window_end = now + timedelta(hours=1)

        administrations = MARAdministration.objects.filter(
            mar__hospital_id=hospital_id,
            mar__is_active=True,
            scheduled_time__gte=window_start,
            scheduled_time__lte=window_end,
            status="Administered"  # Not yet administered
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

    @action(detail=True, methods=["post"])
    def administer(self, request, pk=None):
        """Record medication administration."""
        admin = self.get_object()

        if admin.status != "Administered":
            return Response(
                {"detail": f"Already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin.administered_time = timezone.now()
        admin.administered_by_id = request.data.get("administered_by")
        admin.dose_given = request.data.get("dose_given", admin.mar.dose)
        admin.route_given = request.data.get("route_given", admin.mar.route)
        admin.site = request.data.get("site", "")
        admin.notes = request.data.get("notes", "")
        admin.status = "Administered"
        admin.save()

        return Response(MARAdministrationSerializer(admin).data)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        """Hold medication."""
        admin = self.get_object()

        if admin.status != "Administered":
            return Response(
                {"detail": f"Cannot hold - already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin.status = "Held"
        admin.reason_held = request.data.get("reason", "")
        admin.notes = request.data.get("notes", "")
        admin.administered_by_id = request.data.get("administered_by")
        admin.administered_time = timezone.now()
        admin.save()

        return Response(MARAdministrationSerializer(admin).data)

    @action(detail=True, methods=["post"])
    def refuse(self, request, pk=None):
        """Patient refused medication."""
        admin = self.get_object()

        if admin.status != "Administered":
            return Response(
                {"detail": f"Cannot refuse - already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin.status = "Refused"
        admin.reason_refused = request.data.get("reason", "")
        admin.notes = request.data.get("notes", "")
        admin.administered_by_id = request.data.get("administered_by")
        admin.administered_time = timezone.now()
        admin.save()

        return Response(MARAdministrationSerializer(admin).data)

    @action(detail=True, methods=["post"])
    def mark_missed(self, request, pk=None):
        """Mark as missed."""
        admin = self.get_object()

        if admin.status != "Administered":
            return Response(
                {"detail": f"Cannot mark missed - already {admin.status.lower()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin.status = "Missed"
        admin.notes = request.data.get("notes", "Missed dose")
        admin.administered_time = timezone.now()
        admin.save()

        return Response(MARAdministrationSerializer(admin).data)


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