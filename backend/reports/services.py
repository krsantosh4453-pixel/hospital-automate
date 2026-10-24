"""
Centralized KPI calculation service for hospital analytics.

All KPI calculations should go through this service to ensure:
1. Consistent calculations across the application
2. Proper hospital scoping and permission checks
3. Real data from operational models (no hardcoded values)
4. Timezone-aware period handling
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import Avg, Count, F, Q, Sum, ExpressionWrapper, DurationField
from django.utils import timezone

from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from encounters.models import QueueToken, Visit
from emergency.models import EmergencyVisit
from ipd.models import Admission, BedAllocation
from laboratory.models import LabTest
from pharmacy.models import Medicine, Sale
from billing.models import Invoice, Payment
from bloodbank.models import BloodInventory, BloodRequest, BloodTransaction
from hospital.models import Bed, Ward, Room
from procurement.models import PurchaseOrder, GoodsReceipt, StockTransaction
from ai_scribe.models import ConsultationSession


class KPIService:
    """Centralized service for all hospital KPI calculations."""

    def __init__(self, hospital_id: int):
        self.hospital_id = hospital_id

    def _get_period_bounds(self, period: str, custom_start: Optional[datetime] = None, custom_end: Optional[datetime] = None):
        """Get timezone-aware start/end datetime for a period."""
        now = timezone.now()
        today = now.date()

        if period == "today":
            start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        elif period == "yesterday":
            yesterday = today - timedelta(days=1)
            start = timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
            end = timezone.make_aware(datetime.combine(yesterday, datetime.max.time()))
        elif period == "last_7_days":
            start = timezone.make_aware(datetime.combine(today - timedelta(days=6), datetime.min.time()))
            end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        elif period == "last_30_days":
            start = timezone.make_aware(datetime.combine(today - timedelta(days=29), datetime.min.time()))
            end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        elif period == "this_month":
            start = timezone.make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))
            end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        elif period == "last_month":
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start = timezone.make_aware(datetime.combine(last_month_start, datetime.min.time()))
            end = timezone.make_aware(datetime.combine(last_month_end, datetime.max.time()))
        elif period == "this_year":
            start = timezone.make_aware(datetime.combine(today.replace(month=1, day=1), datetime.min.time()))
            end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        elif period == "custom" and custom_start and custom_end:
            start = custom_start
            end = custom_end
        else:
            start = timezone.make_aware(datetime.combine(today - timedelta(days=29), datetime.min.time()))
            end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        return start, end

    # ========================
    # Patient KPIs
    # ========================

    def get_patient_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        qs = Patient.objects.filter(hospital_id=self.hospital_id)
        total = qs.count()
        new_in_period = qs.filter(created_at__gte=start, created_at__lte=end).count()
        active = qs.filter(status="Active").count()

        return {
            "total": total,
            "new_in_period": new_in_period,
            "active": active,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Doctor KPIs
    # ========================

    def get_doctor_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        qs = Doctor.objects.filter(hospital_id=self.hospital_id)
        total = qs.count()
        active = qs.filter(status="Available").count()
        on_leave = qs.filter(status="On Leave").count()

        return {
            "total": total,
            "active": active,
            "on_leave": on_leave,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Appointment / OPD KPIs
    # ========================

    def get_appointment_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        qs = Appointment.objects.filter(hospital_id=self.hospital_id)
        in_period = qs.filter(appointment_date__gte=start.date(), appointment_date__lte=end.date())

        total = qs.count()
        period_total = in_period.count()
        scheduled = in_period.filter(status="Scheduled").count()
        completed = in_period.filter(status="Completed").count()
        cancelled = in_period.filter(status="Cancelled").count()
        no_show = in_period.filter(status="No Show").count()

        no_show_rate = 0
        if period_total > 0:
            no_show_rate = round((no_show / period_total) * 100, 2)

        cancellation_rate = 0
        if period_total > 0:
            cancellation_rate = round((cancelled / period_total) * 100, 2)

        # By department
        by_dept = (
            in_period.values("doctor__specialization")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # By doctor
        by_doctor = (
            in_period.values("doctor__name", "doctor__specialization")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Daily trend
        daily = (
            in_period.values("appointment_date")
            .annotate(count=Count("id"))
            .order_by("appointment_date")
        )

        return {
            "total": total,
            "period_total": period_total,
            "scheduled": scheduled,
            "completed": completed,
            "cancelled": cancelled,
            "no_show": no_show,
            "no_show_rate": no_show_rate,
            "cancellation_rate": cancellation_rate,
            "by_department": list(by_dept),
            "by_doctor": list(by_doctor),
            "daily_trend": list(daily),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Queue KPIs
    # ========================

    def get_queue_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        qs = QueueToken.objects.filter(hospital_id=self.hospital_id)
        in_period = qs.filter(token_date__gte=start.date(), token_date__lte=end.date())

        total = qs.count()
        period_total = in_period.count()
        waiting = in_period.filter(status="Waiting").count()
        in_consultation = in_period.filter(status="In Consultation").count()
        completed = in_period.filter(status="Completed").count()
        skipped = in_period.filter(status="Skipped").count()
        cancelled = in_period.filter(status="Cancelled").count()
        no_show = in_period.filter(status="No Show").count()

        # Average wait time for completed tokens
        avg_wait = in_period.filter(
            status="Completed", acknowledged_at__isnull=False, consultation_started_at__isnull=False
        ).aggregate(
            avg_wait=Avg(
                ExpressionWrapper(
                    F("consultation_started_at") - F("acknowledged_at"),
                    output_field=DurationField(),
                )
            )
        )["avg_wait"]

        avg_wait_minutes = 0
        if avg_wait:
            avg_wait_minutes = round(avg_wait.total_seconds() / 60, 2)

        # Peak hours analysis
        peak_hours = (
            in_period.filter(created_at__isnull=False)
            .extra({"hour": "EXTRACT(hour FROM created_at)"})
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # Daily volume
        daily_volume = (
            in_period.values("token_date")
            .annotate(
                total=Count("id"),
                completed=Count("id", filter=Q(status="Completed")),
                waiting=Count("id", filter=Q(status="Waiting")),
            )
            .order_by("token_date")
        )

        return {
            "total": total,
            "period_total": period_total,
            "waiting": waiting,
            "in_consultation": in_consultation,
            "completed": completed,
            "skipped": skipped,
            "cancelled": cancelled,
            "no_show": no_show,
            "avg_wait_minutes": avg_wait_minutes,
            "peak_hours": list(peak_hours),
            "daily_volume": list(daily_volume),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # IPD / Bed KPIs
    # ========================

    def get_ipd_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        # Admissions
        admission_qs = Admission.objects.filter(hospital_id=self.hospital_id)
        admissions_in_period = admission_qs.filter(admission_date__gte=start, admission_date__lte=end)
        discharges_in_period = admission_qs.filter(discharge_date__gte=start, discharge_date__lte=end)

        total_admissions = admission_qs.count()
        period_admissions = admissions_in_period.count()
        period_discharges = discharges_in_period.count()
        current_admitted = admission_qs.filter(status="Admitted").count()

        # Bed occupancy
        bed_qs = Bed.objects.filter(room__ward__hospital_id=self.hospital_id)
        total_beds = bed_qs.count()
        available_beds = bed_qs.filter(status="Available").count()
        occupied_beds = total_beds - available_beds
        occupancy_rate = 0
        if total_beds > 0:
            occupancy_rate = round((occupied_beds / total_beds) * 100, 2)

        # Ward-level occupancy
        ward_occupancy = []
        for ward in Ward.objects.filter(hospital_id=self.hospital_id):
            ward_beds = Bed.objects.filter(room__ward=ward)
            ward_total = ward_beds.count()
            ward_available = ward_beds.filter(status="Available").count()
            ward_occupied = ward_total - ward_available
            ward_rate = 0
            if ward_total > 0:
                ward_rate = round((ward_occupied / ward_total) * 100, 2)
            ward_occupancy.append(
                {
                    "ward": ward.name,
                    "total_beds": ward_total,
                    "occupied": ward_occupied,
                    "available": ward_available,
                    "occupancy_rate": ward_rate,
                }
            )

        # Average Length of Stay (for discharged patients in period)
        los_data = discharges_in_period.exclude(discharge_date__isnull=True).aggregate(
            avg_los=Avg(
                ExpressionWrapper(
                    F("discharge_date") - F("admission_date"),
                    output_field=DurationField(),
                )
            )
        )
        avg_los_days = 0
        if los_data["avg_los"]:
            avg_los_days = round(los_data["avg_los"].total_seconds() / 86400, 2)

        # Admission/Discharge daily trend
        daily_admissions = (
            admissions_in_period.values("admission_date__date")
            .annotate(count=Count("id"))
            .order_by("admission_date__date")
        )
        daily_discharges = (
            discharges_in_period.values("discharge_date__date")
            .annotate(count=Count("id"))
            .order_by("discharge_date__date")
        )

        return {
            "total_admissions": total_admissions,
            "period_admissions": period_admissions,
            "period_discharges": period_discharges,
            "current_admitted": current_admitted,
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": occupied_beds,
            "occupancy_rate": occupancy_rate,
            "ward_occupancy": ward_occupancy,
            "avg_length_of_stay_days": avg_los_days,
            "daily_admissions": list(daily_admissions),
            "daily_discharges": list(daily_discharges),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Emergency KPIs
    # ========================

    def get_emergency_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        qs = EmergencyVisit.objects.filter(hospital_id=self.hospital_id)
        in_period = qs.filter(arrival_time__gte=start, arrival_time__lte=end)

        total = qs.count()
        period_total = in_period.count()
        by_triage = in_period.values("triage_level").annotate(count=Count("id")).order_by("triage_level")
        by_status = in_period.values("status").annotate(count=Count("id"))
        by_disposition = in_period.exclude(disposition="").values("disposition").annotate(count=Count("id"))

        # Admission conversion rate
        admitted = in_period.filter(status="Admitted").count()
        admission_rate = 0
        if period_total > 0:
            admission_rate = round((admitted / period_total) * 100, 2)

        # Average door-to-doctor time (where triage_time and consultation_start_time exist)
        door_to_doctor = in_period.filter(
            triage_time__isnull=False, consultation_start_time__isnull=False
        ).aggregate(
            avg_time=Avg(
                ExpressionWrapper(
                    F("consultation_start_time") - F("triage_time"),
                    output_field=DurationField(),
                )
            )
        )
        avg_door_to_doctor_minutes = 0
        if door_to_doctor["avg_time"]:
            avg_door_to_doctor_minutes = round(door_to_doctor["avg_time"].total_seconds() / 60, 2)

        # Peak hours
        peak_hours = (
            in_period.values("arrival_time__hour")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        daily_volume = (
            in_period.values("arrival_time__date")
            .annotate(count=Count("id"))
            .order_by("arrival_time__date")
        )

        return {
            "total": total,
            "period_total": period_total,
            "by_triage": list(by_triage),
            "by_status": list(by_status),
            "by_disposition": list(by_disposition),
            "admitted": admitted,
            "admission_rate": admission_rate,
            "avg_door_to_doctor_minutes": avg_door_to_doctor_minutes,
            "peak_hours": list(peak_hours),
            "daily_volume": list(daily_volume),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Laboratory KPIs
    # ========================

    def get_laboratory_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        qs = LabTest.objects.filter(hospital_id=self.hospital_id)
        in_period = qs.filter(test_date__gte=start.date(), test_date__lte=end.date())

        total = qs.count()
        period_total = in_period.count()
        pending = in_period.filter(status__in=["Ordered", "Sample Pending", "Collected", "Dispatched", "Received", "Processing"]).count()
        completed = in_period.filter(status__in=["Verified", "Released"]).count()
        cancelled = in_period.filter(status="Cancelled").count()

        # Turnaround time: from ordered to released
        tat_data = in_period.filter(
            status__in=["Verified", "Released"],
            test_date__isnull=False,
            released_at__isnull=False,
        ).aggregate(
            avg_tat=Avg(
                ExpressionWrapper(
                    F("released_at") - F("test_date"),
                    output_field=DurationField(),
                )
            )
        )
        avg_tat_hours = 0
        if tat_data["avg_tat"]:
            avg_tat_hours = round(tat_data["avg_tat"].total_seconds() / 3600, 2)

        # By test category (name)
        by_test = in_period.values("name").annotate(count=Count("id")).order_by("-count")[:20]

        # Daily trend
        daily = in_period.values("test_date").annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status__in=["Verified", "Released"])),
            pending=Count("id", filter=Q(status__in=["Ordered", "Sample Pending", "Collected", "Dispatched", "Received", "Processing"])),
        ).order_by("test_date")

        # Urgent tests
        urgent_pending = in_period.filter(priority="Urgent", status__in=["Ordered", "Sample Pending", "Collected", "Dispatched", "Received", "Processing"]).count()

        return {
            "total": total,
            "period_total": period_total,
            "pending": pending,
            "completed": completed,
            "cancelled": cancelled,
            "urgent_pending": urgent_pending,
            "avg_turnaround_hours": avg_tat_hours,
            "by_test": list(by_test),
            "daily_trend": list(daily),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Pharmacy KPIs
    # ========================

    def get_pharmacy_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        # Medicine inventory
        med_qs = Medicine.objects.filter(hospital_id=self.hospital_id)
        total_medicines = med_qs.count()
        low_stock = med_qs.filter(quantity__lte=10, quantity__gt=0).count()
        out_of_stock = med_qs.filter(quantity=0).count()
        expiring_soon = med_qs.filter(
            expiry_date__isnull=False,
            expiry_date__lte=timezone.now().date() + timedelta(days=30),
            quantity__gt=0,
        ).count()
        expired = med_qs.filter(
            expiry_date__isnull=False,
            expiry_date__lt=timezone.now().date(),
            quantity__gt=0,
        ).count()

        # Sales
        sale_qs = Sale.objects.filter(hospital_id=self.hospital_id)
        sales_in_period = sale_qs.filter(created_at__gte=start, created_at__lte=end)

        total_sales = sale_qs.count()
        period_sales = sales_in_period.count()
        period_revenue = sales_in_period.aggregate(total=Sum("total"))["total"] or Decimal("0")
        period_quantity = sales_in_period.aggregate(total=Sum("quantity"))["total"] or 0

        # Top selling medicines
        top_medicines = (
            sales_in_period.values("medicine__name", "medicine__category")
            .annotate(total_qty=Sum("quantity"), total_revenue=Sum("total"))
            .order_by("-total_qty")[:10]
        )

        # Daily sales trend
        daily_sales = (
            sales_in_period.values("created_at__date")
            .annotate(count=Count("id"), revenue=Sum("total"), quantity=Sum("quantity"))
            .order_by("created_at__date")
        )

        # Inventory turnover (simplified: sales / average inventory)
        avg_inventory = med_qs.aggregate(avg=Avg("quantity"))["avg"] or 0
        inventory_turnover = 0
        if avg_inventory > 0:
            inventory_turnover = round(float(period_quantity) / float(avg_inventory), 2)

        return {
            "total_medicines": total_medicines,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "total_sales": total_sales,
            "period_sales": period_sales,
            "period_revenue": float(period_revenue),
            "period_quantity": period_quantity,
            "top_medicines": list(top_medicines),
            "daily_sales": list(daily_sales),
            "inventory_turnover": inventory_turnover,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Inventory Intelligence
    # ========================

    def get_inventory_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        # Stock transactions
        txn_qs = StockTransaction.objects.filter(hospital_id=self.hospital_id)
        txns_in_period = txn_qs.filter(created_at__gte=start, created_at__lte=end)

        stock_in = txns_in_period.filter(transaction_type="IN").aggregate(total=Sum("quantity"))["total"] or 0
        stock_out = txns_in_period.filter(transaction_type="OUT").aggregate(total=Sum("quantity"))["total"] or 0
        adjustments = txns_in_period.filter(transaction_type="ADJUST").aggregate(total=Sum("quantity"))["total"] or 0

        # Procurement
        po_qs = PurchaseOrder.objects.filter(hospital_id=self.hospital_id)
        pos_in_period = po_qs.filter(created_at__gte=start, created_at__lte=end)
        total_pos = po_qs.count()
        period_pos = pos_in_period.count()
        pos_received = pos_in_period.filter(status="Received").count()
        pos_pending = pos_in_period.filter(status__in=["Draft", "Ordered", "Partial"]).count()

        # Goods receipts
        grn_qs = GoodsReceipt.objects.filter(hospital_id=self.hospital_id)
        grns_in_period = grn_qs.filter(created_at__gte=start, created_at__lte=end)
        total_grns = grn_qs.count()
        period_grns = grns_in_period.count()

        # Supplier performance
        supplier_perf = (
            grns_in_period.values("supplier__name")
            .annotate(total_receipts=Count("id"), total_qty=Sum("items__quantity_received"))
            .order_by("-total_qty")[:10]
        )

        # Slow moving / fast moving (simplified)
        med_qs = Medicine.objects.filter(hospital_id=self.hospital_id)
        slow_moving = med_qs.filter(quantity__gt=0).order_by("quantity")[:10]
        fast_moving = med_qs.order_by("-quantity")[:10]

        return {
            "stock_in": stock_in,
            "stock_out": stock_out,
            "adjustments": adjustments,
            "net_movement": stock_in - stock_out,
            "total_purchase_orders": total_pos,
            "period_purchase_orders": period_pos,
            "pos_received": pos_received,
            "pos_pending": pos_pending,
            "total_goods_receipts": total_grns,
            "period_goods_receipts": period_grns,
            "supplier_performance": list(supplier_perf),
            "slow_moving": [
                {"name": m.name, "quantity": m.quantity, "category": m.category}
                for m in slow_moving
            ],
            "fast_moving": [
                {"name": m.name, "quantity": m.quantity, "category": m.category}
                for m in fast_moving
            ],
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Billing KPIs
    # ========================

    def get_billing_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        inv_qs = Invoice.objects.filter(hospital_id=self.hospital_id)
        inv_in_period = inv_qs.filter(created_at__gte=start, created_at__lte=end)

        pay_qs = Payment.objects.filter(invoice__hospital_id=self.hospital_id)
        pay_in_period = pay_qs.filter(paid_at__gte=start, paid_at__lte=end)
        refunds_in_period = pay_in_period.filter(kind=Payment.Kind.REFUND)
        pay_in_period = pay_in_period.filter(kind=Payment.Kind.PAYMENT)

        total_invoices = inv_qs.count()
        period_invoices = inv_in_period.count()
        paid_invoices = inv_in_period.filter(status=Invoice.Status.PAID).count()
        unpaid_invoices = inv_in_period.filter(status=Invoice.Status.UNPAID).count()
        partial_invoices = inv_in_period.filter(status=Invoice.Status.PARTIALLY_PAID).count()

        # Revenue is money received minus refunds given in the period.
        received = pay_in_period.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        refunded = refunds_in_period.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        period_revenue = received - refunded

        # Outstanding = billed minus net received, for invoices still owing.
        open_invoices = inv_in_period.filter(
            status__in=[Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID]
        )
        billed = open_invoices.aggregate(total=Sum("total"))["total"] or Decimal("0")
        open_paid = Payment.objects.filter(invoice__in=open_invoices, kind=Payment.Kind.PAYMENT).aggregate(
            total=Sum("amount"))["total"] or Decimal("0")
        open_refunded = Payment.objects.filter(invoice__in=open_invoices, kind=Payment.Kind.REFUND).aggregate(
            total=Sum("amount"))["total"] or Decimal("0")
        period_outstanding = billed - (open_paid - open_refunded)

        # Payment method breakdown
        by_method = pay_in_period.values("payment_method").annotate(
            count=Count("id"), total=Sum("amount")
        )

        # Daily revenue
        daily_revenue = (
            pay_in_period.values("paid_at__date")
            .annotate(count=Count("id"), revenue=Sum("amount"))
            .order_by("paid_at__date")
        )

        # By department (via invoice items)
        # This would need a join through invoice items

        return {
            "total_invoices": total_invoices,
            "period_invoices": period_invoices,
            "paid": paid_invoices,
            "unpaid": unpaid_invoices,
            "partial": partial_invoices,
            "period_revenue": float(period_revenue),
            "period_outstanding": float(period_outstanding),
            "by_payment_method": list(by_method),
            "daily_revenue": list(daily_revenue),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Blood Bank KPIs
    # ========================

    def get_bloodbank_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        # Inventory
        inv_qs = BloodInventory.objects.filter(hospital_id=self.hospital_id)
        total_units = inv_qs.aggregate(total=Sum("units"))["total"] or 0
        by_group = inv_qs.values("blood_group", "component").annotate(total=Sum("units"))

        # Requests
        req_qs = BloodRequest.objects.filter(hospital_id=self.hospital_id)
        req_in_period = req_qs.filter(created_at__gte=start, created_at__lte=end)
        total_requests = req_qs.count()
        period_requests = req_in_period.count()
        by_status = req_in_period.values("status").annotate(count=Count("id"))
        by_component = req_in_period.values("blood_group", "component").annotate(count=Count("id"))

        # Transactions
        txn_qs = BloodTransaction.objects.filter(hospital_id=self.hospital_id)
        txns_in_period = txn_qs.filter(created_at__gte=start, created_at__lte=end)
        issues = txns_in_period.filter(transaction_type="Issue").aggregate(total=Sum("units"))["total"] or 0
        receives = txns_in_period.filter(transaction_type="Receive").aggregate(total=Sum("units"))["total"] or 0
        expiries = txns_in_period.filter(transaction_type="Expiry").aggregate(total=Sum("units"))["total"] or 0

        # Expiry risk
        expiring = inv_qs.filter(
            expiry_date__isnull=False,
            expiry_date__lte=timezone.now().date() + timedelta(days=30),
            units__gt=0,
        ).count()

        return {
            "total_units": total_units,
            "by_group_component": list(by_group),
            "total_requests": total_requests,
            "period_requests": period_requests,
            "by_status": list(by_status),
            "by_component": list(by_component),
            "issues": issues,
            "receives": receives,
            "expiries": expiries,
            "net_change": receives - issues - expiries,
            "expiring_soon": expiring,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # AI Scribe KPIs
    # ========================

    def get_ai_scribe_kpis(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        start, end = self._get_period_bounds(period, custom_start, custom_end)

        qs = ConsultationSession.objects.filter(hospital_id=self.hospital_id)
        in_period = qs.filter(started_at__gte=start, started_at__lte=end)

        total = qs.count()
        period_total = in_period.count()
        by_status = in_period.values("status").annotate(count=Count("id"))
        completed = in_period.filter(status="completed").count()
        recording = in_period.filter(status="recording").count()

        # Audio duration
        total_audio_seconds = in_period.aggregate(total=Sum("audio_duration_seconds"))["total"] or 0

        # Transcription completion rate
        from ai_scribe.models import ConversationTranscript
        transcripts = ConversationTranscript.objects.filter(consultation__hospital_id=self.hospital_id)
        transcripts_in_period = transcripts.filter(created_at__gte=start, created_at__lte=end)
        transcript_total = transcripts_in_period.count()
        transcript_completed = transcripts_in_period.filter(status="completed").count()
        transcript_failed = transcripts_in_period.filter(status="failed").count()

        completion_rate = 0
        if transcript_total > 0:
            completion_rate = round((transcript_completed / transcript_total) * 100, 2)

        return {
            "total_sessions": total,
            "period_sessions": period_total,
            "by_status": list(by_status),
            "completed": completed,
            "recording": recording,
            "total_audio_seconds": total_audio_seconds,
            "total_audio_hours": round(total_audio_seconds / 3600, 2),
            "transcripts_generated": transcript_total,
            "transcripts_completed": transcript_completed,
            "transcripts_failed": transcript_failed,
            "transcript_completion_rate": completion_rate,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }

    # ========================
    # Comprehensive Dashboard
    # ========================

    def get_comprehensive_dashboard(self, period: str = "last_30_days", custom_start=None, custom_end=None):
        """Get all KPIs in one call for main dashboard."""
        return {
            "period": self._get_period_bounds(period, custom_start, custom_end)[0].isoformat(),
            "patients": self.get_patient_kpis(period, custom_start, custom_end),
            "doctors": self.get_doctor_kpis(period, custom_start, custom_end),
            "appointments": self.get_appointment_kpis(period, custom_start, custom_end),
            "queue": self.get_queue_kpis(period, custom_start, custom_end),
            "ipd": self.get_ipd_kpis(period, custom_start, custom_end),
            "emergency": self.get_emergency_kpis(period, custom_start, custom_end),
            "laboratory": self.get_laboratory_kpis(period, custom_start, custom_end),
            "pharmacy": self.get_pharmacy_kpis(period, custom_start, custom_end),
            "inventory": self.get_inventory_kpis(period, custom_start, custom_end),
            "billing": self.get_billing_kpis(period, custom_start, custom_end),
            "bloodbank": self.get_bloodbank_kpis(period, custom_start, custom_end),
            "ai_scribe": self.get_ai_scribe_kpis(period, custom_start, custom_end),
        }