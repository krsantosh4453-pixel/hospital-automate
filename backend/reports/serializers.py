from rest_framework import serializers
from reports.models import ReportTemplate, SavedReport, ScheduledReport, KPISnapshot


class PeriodSerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=[
            "today",
            "yesterday",
            "last_7_days",
            "last_30_days",
            "this_month",
            "last_month",
            "this_year",
            "custom",
        ],
        default="last_30_days",
    )
    custom_start = serializers.DateTimeField(required=False, allow_null=True)
    custom_end = serializers.DateTimeField(required=False, allow_null=True)


class PatientKPISerializer(serializers.Serializer):
    total = serializers.IntegerField()
    new_in_period = serializers.IntegerField()
    active = serializers.IntegerField()
    period = serializers.DictField()


class DoctorKPISerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    on_leave = serializers.IntegerField()
    period = serializers.DictField()


class AppointmentKPISerializer(serializers.Serializer):
    total = serializers.IntegerField()
    period_total = serializers.IntegerField()
    scheduled = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    no_show = serializers.IntegerField()
    no_show_rate = serializers.FloatField()
    cancellation_rate = serializers.FloatField()
    by_department = serializers.ListField(child=serializers.DictField())
    by_doctor = serializers.ListField(child=serializers.DictField())
    daily_trend = serializers.ListField(child=serializers.DictField())
    period = serializers.DictField()


class QueueKPISerializer(serializers.Serializer):
    total = serializers.IntegerField()
    period_total = serializers.IntegerField()
    waiting = serializers.IntegerField()
    in_consultation = serializers.IntegerField()
    completed = serializers.IntegerField()
    skipped = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    no_show = serializers.IntegerField()
    avg_wait_minutes = serializers.FloatField()
    peak_hours = serializers.ListField(child=serializers.DictField())
    daily_volume = serializers.ListField(child=serializers.DictField())
    period = serializers.DictField()


class IPDKPISerializer(serializers.Serializer):
    total_admissions = serializers.IntegerField()
    period_admissions = serializers.IntegerField()
    period_discharges = serializers.IntegerField()
    current_admitted = serializers.IntegerField()
    total_beds = serializers.IntegerField()
    available_beds = serializers.IntegerField()
    occupied_beds = serializers.IntegerField()
    occupancy_rate = serializers.FloatField()
    ward_occupancy = serializers.ListField(child=serializers.DictField())
    avg_length_of_stay_days = serializers.FloatField()
    daily_admissions = serializers.ListField(child=serializers.DictField())
    daily_discharges = serializers.ListField(child=serializers.DictField())
    period = serializers.DictField()


class EmergencyKPISerializer(serializers.Serializer):
    total = serializers.IntegerField()
    period_total = serializers.IntegerField()
    by_triage = serializers.ListField(child=serializers.DictField())
    by_status = serializers.ListField(child=serializers.DictField())
    by_disposition = serializers.ListField(child=serializers.DictField())
    admitted = serializers.IntegerField()
    admission_rate = serializers.FloatField()
    avg_door_to_doctor_minutes = serializers.FloatField()
    peak_hours = serializers.ListField(child=serializers.DictField())
    daily_volume = serializers.ListField(child=serializers.DictField())
    period = serializers.DictField()


class LaboratoryKPISerializer(serializers.Serializer):
    total = serializers.IntegerField()
    period_total = serializers.IntegerField()
    pending = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    urgent_pending = serializers.IntegerField()
    avg_turnaround_hours = serializers.FloatField()
    by_test = serializers.ListField(child=serializers.DictField())
    daily_trend = serializers.ListField(child=serializers.DictField())
    period = serializers.DictField()


class PharmacyKPISerializer(serializers.Serializer):
    total_medicines = serializers.IntegerField()
    low_stock = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()
    expired = serializers.IntegerField()
    total_sales = serializers.IntegerField()
    period_sales = serializers.IntegerField()
    period_revenue = serializers.FloatField()
    period_quantity = serializers.IntegerField()
    top_medicines = serializers.ListField(child=serializers.DictField())
    daily_sales = serializers.ListField(child=serializers.DictField())
    inventory_turnover = serializers.FloatField()
    period = serializers.DictField()


class InventoryKPISerializer(serializers.Serializer):
    stock_in = serializers.IntegerField()
    stock_out = serializers.IntegerField()
    adjustments = serializers.IntegerField()
    net_movement = serializers.IntegerField()
    total_purchase_orders = serializers.IntegerField()
    period_purchase_orders = serializers.IntegerField()
    pos_received = serializers.IntegerField()
    pos_pending = serializers.IntegerField()
    total_goods_receipts = serializers.IntegerField()
    period_goods_receipts = serializers.IntegerField()
    supplier_performance = serializers.ListField(child=serializers.DictField())
    slow_moving = serializers.ListField(child=serializers.DictField())
    fast_moving = serializers.ListField(child=serializers.DictField())
    period = serializers.DictField()


class BillingKPISerializer(serializers.Serializer):
    total_invoices = serializers.IntegerField()
    period_invoices = serializers.IntegerField()
    paid = serializers.IntegerField()
    unpaid = serializers.IntegerField()
    partial = serializers.IntegerField()
    period_revenue = serializers.FloatField()
    period_outstanding = serializers.FloatField()
    by_payment_method = serializers.ListField(child=serializers.DictField())
    daily_revenue = serializers.ListField(child=serializers.DictField())
    period = serializers.DictField()


class BloodBankKPISerializer(serializers.Serializer):
    total_units = serializers.IntegerField()
    by_group_component = serializers.ListField(child=serializers.DictField())
    total_requests = serializers.IntegerField()
    period_requests = serializers.IntegerField()
    by_status = serializers.ListField(child=serializers.DictField())
    by_component = serializers.ListField(child=serializers.DictField())
    issues = serializers.IntegerField()
    receives = serializers.IntegerField()
    expiries = serializers.IntegerField()
    net_change = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()
    period = serializers.DictField()


class AIScribeKPISerializer(serializers.Serializer):
    total_sessions = serializers.IntegerField()
    period_sessions = serializers.IntegerField()
    by_status = serializers.ListField(child=serializers.DictField())
    completed = serializers.IntegerField()
    recording = serializers.IntegerField()
    total_audio_seconds = serializers.IntegerField()
    total_audio_hours = serializers.FloatField()
    transcripts_generated = serializers.IntegerField()
    transcripts_completed = serializers.IntegerField()
    transcripts_failed = serializers.IntegerField()
    transcript_completion_rate = serializers.FloatField()
    period = serializers.DictField()


class ComprehensiveDashboardSerializer(serializers.Serializer):
    period = serializers.CharField()
    patients = PatientKPISerializer()
    doctors = DoctorKPISerializer()
    appointments = AppointmentKPISerializer()
    queue = QueueKPISerializer()
    ipd = IPDKPISerializer()
    emergency = EmergencyKPISerializer()
    laboratory = LaboratoryKPISerializer()
    pharmacy = PharmacyKPISerializer()
    inventory = InventoryKPISerializer()
    billing = BillingKPISerializer()
    bloodbank = BloodBankKPISerializer()
    ai_scribe = AIScribeKPISerializer()


class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "name",
            "report_type",
            "description",
            "default_period",
            "filters",
            "is_system",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class SavedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedReport
        fields = [
            "id",
            "template",
            "name",
            "report_type",
            "period",
            "custom_start_date",
            "custom_end_date",
            "filters",
            "created_by",
            "hospital",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "hospital", "created_at", "updated_at"]


class ScheduledReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledReport
        fields = [
            "id",
            "name",
            "template",
            "hospital",
            "frequency",
            "delivery_method",
            "recipients",
            "filters",
            "is_active",
            "last_generated",
            "next_run",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class KPISnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPISnapshot
        fields = [
            "id",
            "hospital",
            "period_start",
            "period_end",
            "kpi_name",
            "kpi_value",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]