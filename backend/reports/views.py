from datetime import datetime
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsStaffUser, get_user_hospital_ids, is_active_staff, parse_hospital_id
from reports.services import KPIService
from reports.forecasting import ForecastingService
from reports.models import ReportTemplate, SavedReport, ScheduledReport, KPISnapshot
from reports.serializers import (
    PeriodSerializer,
    ComprehensiveDashboardSerializer,
    ReportTemplateSerializer,
    SavedReportSerializer,
    ScheduledReportSerializer,
    KPISnapshotSerializer,
)


def _get_authorized_hospital(request):
    """Get hospital_id from query params if user has access."""
    hospital_id = request.query_params.get("hospital")
    if not hospital_id:
        return None

    try:
        hospital_id = int(hospital_id)
    except (ValueError, TypeError):
        return None

    user_hospitals = get_user_hospital_ids(request.user)
    if hospital_id not in user_hospitals:
        return None

    return hospital_id


class AnalyticsViewSet(viewsets.ViewSet):
    """Main analytics endpoints for hospital KPIs and dashboards."""

    permission_classes = [IsAuthenticated]

    def _check_hospital_access(self, request):
        hospital_id = _get_authorized_hospital(request)
        if not hospital_id:
            return Response(
                {
                    "error": "Hospital parameter is required or access denied",
                    "detail": "Provide ?hospital=<id> query parameter for a hospital you have access to",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return hospital_id

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """Comprehensive dashboard with all KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        period = period_serializer.validated_data["period"]
        custom_start = period_serializer.validated_data.get("custom_start")
        custom_end = period_serializer.validated_data.get("custom_end")

        service = KPIService(hospital_id)
        data = service.get_comprehensive_dashboard(period, custom_start, custom_end)

        serializer = ComprehensiveDashboardSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="patients")
    def patients(self, request):
        """Patient KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_patient_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="doctors")
    def doctors(self, request):
        """Doctor KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_doctor_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="appointments")
    def appointments(self, request):
        """Appointment/OPD KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_appointment_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="queue")
    def queue(self, request):
        """Queue intelligence KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_queue_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="ipd")
    def ipd(self, request):
        """IPD/Bed management KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_ipd_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="emergency")
    def emergency(self, request):
        """Emergency department KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_emergency_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="laboratory")
    def laboratory(self, request):
        """Laboratory KPIs with turnaround time."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_laboratory_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="pharmacy")
    def pharmacy(self, request):
        """Pharmacy KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_pharmacy_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="inventory")
    def inventory(self, request):
        """Inventory intelligence KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_inventory_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="billing")
    def billing(self, request):
        """Billing/Financial KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_billing_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="bloodbank")
    def bloodbank(self, request):
        """Blood bank KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_bloodbank_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="ai-scribe")
    def ai_scribe(self, request):
        """AI Scribe usage KPIs."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        data = service.get_ai_scribe_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="financial")
    def financial(self, request):
        """Financial report - alias for billing with additional context."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        billing_data = service.get_billing_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        pharmacy_data = service.get_pharmacy_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        lab_data = service.get_laboratory_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )

        return Response(
            {
                "billing": billing_data,
                "pharmacy_revenue": pharmacy_data.get("period_revenue", 0),
                "laboratory_revenue": 0,  # Lab revenue would come from billing items
                "total_revenue": billing_data.get("period_revenue", 0)
                + pharmacy_data.get("period_revenue", 0),
                "period": billing_data.get("period"),
            }
        )

    @action(detail=False, methods=["get"], url_path="clinical")
    def clinical(self, request):
        """Clinical report - appointments, encounters, lab, pharmacy."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        appt_data = service.get_appointment_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        lab_data = service.get_laboratory_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        pharmacy_data = service.get_pharmacy_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        emergency_data = service.get_emergency_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        ipd_data = service.get_ipd_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )

        return Response(
            {
                "appointments": appt_data,
                "laboratory": lab_data,
                "pharmacy": pharmacy_data,
                "emergency": emergency_data,
                "ipd": ipd_data,
                "period": appt_data.get("period"),
            }
        )

    @action(detail=False, methods=["get"], url_path="operational")
    def operational(self, request):
        """Operational report - queue, beds, inventory, staff."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        queue_data = service.get_queue_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        ipd_data = service.get_ipd_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        inventory_data = service.get_inventory_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        doctor_data = service.get_doctor_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        emergency_data = service.get_emergency_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )

        return Response(
            {
                "queue": queue_data,
                "beds": {
                    "occupancy_rate": ipd_data.get("occupancy_rate", 0),
                    "total_beds": ipd_data.get("total_beds", 0),
                    "available_beds": ipd_data.get("available_beds", 0),
                    "occupied_beds": ipd_data.get("occupied_beds", 0),
                    "ward_occupancy": ipd_data.get("ward_occupancy", []),
                },
                "inventory": inventory_data,
                "staff": {
                    "active_doctors": doctor_data.get("active", 0),
                    "total_doctors": doctor_data.get("total", 0),
                },
                "emergency": {
                    "avg_wait_minutes": emergency_data.get("avg_door_to_doctor_minutes", 0),
                    "queue_length": emergency_data.get("period_total", 0),
                },
                "period": queue_data.get("period"),
            }
        )

    @action(detail=False, methods=["get"], url_path="patient-summary")
    def patient_summary(self, request):
        """Patient summary report."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        period_serializer = PeriodSerializer(data=request.query_params)
        period_serializer.is_valid(raise_exception=True)

        service = KPIService(hospital_id)
        patient_data = service.get_patient_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )
        appt_data = service.get_appointment_kpis(
            period_serializer.validated_data["period"],
            period_serializer.validated_data.get("custom_start"),
            period_serializer.validated_data.get("custom_end"),
        )

        return Response(
            {
                "patients": patient_data,
                "appointments": {
                    "total": appt_data.get("period_total", 0),
                    "completed": appt_data.get("completed", 0),
                    "cancelled": appt_data.get("cancelled", 0),
                },
                "period": patient_data.get("period"),
            }
        )


    @action(detail=False, methods=["get"], url_path="forecast")
    def forecast(self, request):
        """Get all available forecasts."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        # Parse forecast_days parameter
        forecast_days = int(request.query_params.get("forecast_days", 7))
        forecast_days = min(max(forecast_days, 1), 90)  # Clamp between 1 and 90

        forecasting_service = ForecastingService(hospital_id)
        forecasts = forecasting_service.get_all_forecasts(forecast_days)
        return Response(forecasts)

    @action(detail=False, methods=["get"], url_path="forecast/appointments")
    def forecast_appointments(self, request):
        """Forecast appointment volume."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 7))
        forecast_days = min(max(forecast_days, 1), 90)
        method = request.query_params.get("method", "auto")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_appointments(forecast_days, method)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="forecast/patients")
    def forecast_patients(self, request):
        """Forecast patient registrations."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 7))
        forecast_days = min(max(forecast_days, 1), 90)
        method = request.query_params.get("method", "auto")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_patient_registrations(forecast_days, method)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="forecast/queue")
    def forecast_queue(self, request):
        """Forecast queue volume."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 7))
        forecast_days = min(max(forecast_days, 1), 90)
        method = request.query_params.get("method", "auto")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_queue_volume(forecast_days, method)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="forecast/laboratory")
    def forecast_laboratory(self, request):
        """Forecast lab workload."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 7))
        forecast_days = min(max(forecast_days, 1), 90)
        method = request.query_params.get("method", "auto")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_lab_workload(forecast_days, method)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="forecast/medicine")
    def forecast_medicine(self, request):
        """Forecast medicine consumption."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 30))
        forecast_days = min(max(forecast_days, 1), 180)
        method = request.query_params.get("method", "auto")
        medicine_id = request.query_params.get("medicine_id")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_medicine_consumption(
            medicine_id=int(medicine_id) if medicine_id else None,
            forecast_days=forecast_days,
            method=method,
        )
        return Response(result)

    @action(detail=False, methods=["get"], url_path="forecast/beds")
    def forecast_beds(self, request):
        """Forecast bed occupancy."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 7))
        forecast_days = min(max(forecast_days, 1), 90)
        method = request.query_params.get("method", "auto")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_bed_occupancy(forecast_days, method)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="forecast/emergency")
    def forecast_emergency(self, request):
        """Forecast emergency volume."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 7))
        forecast_days = min(max(forecast_days, 1), 90)
        method = request.query_params.get("method", "auto")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_emergency_volume(forecast_days, method)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="forecast/revenue")
    def forecast_revenue(self, request):
        """Forecast revenue."""
        hospital_id = self._check_hospital_access(request)
        if isinstance(hospital_id, Response):
            return hospital_id

        forecast_days = int(request.query_params.get("forecast_days", 30))
        forecast_days = min(max(forecast_days, 1), 180)
        method = request.query_params.get("method", "auto")

        forecasting_service = ForecastingService(hospital_id)
        result = forecasting_service.forecast_revenue(forecast_days, method)
        return Response(result)


def _member_hospital_id(request, value):
    """A hospital id from the request that the user is an active member of."""
    hospital_id = parse_hospital_id(value)
    if hospital_id is None:
        raise serializers.ValidationError({"hospital": "Hospital is required."})
    if hospital_id not in get_user_hospital_ids(request.user):
        raise serializers.ValidationError({"hospital": "Access denied to this hospital"})
    return hospital_id


class IsTemplateEditor(BasePermission):
    """
    Templates have no hospital and are shared by all of them: hospital staff
    read them, only the platform administrator (superuser) changes them.
    """

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.method in SAFE_METHODS and is_active_staff(request.user)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for report templates."""

    permission_classes = [IsAuthenticated, IsTemplateEditor]
    serializer_class = ReportTemplateSerializer
    queryset = ReportTemplate.objects.all()

    def get_queryset(self):
        return ReportTemplate.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SavedReportViewSet(viewsets.ModelViewSet):
    """CRUD for saved reports."""

    permission_classes = [IsAuthenticated, IsStaffUser]
    serializer_class = SavedReportSerializer

    def get_queryset(self):
        user_hospitals = get_user_hospital_ids(self.request.user)
        return SavedReport.objects.filter(
            created_by=self.request.user, hospital_id__in=user_hospitals
        )

    def perform_create(self, serializer):
        hospital_id = _member_hospital_id(self.request, self.request.data.get("hospital"))
        serializer.save(created_by=self.request.user, hospital_id=hospital_id)


class ScheduledReportViewSet(viewsets.ModelViewSet):
    """CRUD for scheduled reports."""

    permission_classes = [IsAuthenticated, IsStaffUser]
    serializer_class = ScheduledReportSerializer

    def get_queryset(self):
        user_hospitals = get_user_hospital_ids(self.request.user)
        return ScheduledReport.objects.filter(hospital_id__in=user_hospitals)

    def _check_recipients(self, hospital_id, recipients):
        # One hospital's report must not be delivered to another hospital's staff.
        if any(hospital_id not in get_user_hospital_ids(user) for user in recipients):
            raise serializers.ValidationError({"recipients": "Recipients must be staff of this hospital."})

    def perform_create(self, serializer):
        hospital_id = _member_hospital_id(self.request, self.request.data.get("hospital"))
        self._check_recipients(hospital_id, serializer.validated_data.get("recipients", []))
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        hospital_id = _member_hospital_id(self.request, serializer.validated_data.get("hospital", instance.hospital))
        self._check_recipients(hospital_id, serializer.validated_data.get("recipients", instance.recipients.all()))
        serializer.save()


class KPISnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to historical KPI snapshots."""

    permission_classes = [IsAuthenticated]
    serializer_class = KPISnapshotSerializer

    def get_queryset(self):
        user_hospitals = get_user_hospital_ids(self.request.user)
        return KPISnapshot.objects.filter(hospital_id__in=user_hospitals)