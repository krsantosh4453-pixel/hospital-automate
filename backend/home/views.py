from datetime import date
from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from hospital.models import Bed
from encounters.models import QueueToken, Visit
from emergency.models import EmergencyVisit
from ipd.models import Admission
from billing.models import Invoice, Payment
from laboratory.models import LabTest
from users.care_scope import care_view_of
from users.permissions import REVENUE_ROLES, get_user_hospital_ids, get_user_roles
from config.hospital_time import hospital_today, on_hospital_day


def _get_authorized_hospital(request):
    """Get hospital_id from query params if user has access."""
    hospital_id = request.query_params.get("hospital")
    if not hospital_id:
        return None
    
    try:
        hospital_id = int(hospital_id)
    except (ValueError, TypeError):
        return None
    
    # Check if user has access to this hospital
    user_hospitals = get_user_hospital_ids(request.user)
    if hospital_id not in user_hospitals:
        return None
    
    return hospital_id


OPEN_INVOICE_STATUSES = (Invoice.Status.UNPAID, Invoice.Status.PARTIALLY_PAID)


def _sum_amount(payments):
    return payments.aggregate(total=Sum("amount"))["total"] or 0


def _net_received(payments):
    """Payments received less refunds paid back, as billing.services.net_paid counts them."""
    return (_sum_amount(payments.filter(kind=Payment.Kind.PAYMENT))
            - _sum_amount(payments.filter(kind=Payment.Kind.REFUND)))


def _money(request, hospital_id, amount):
    """``amount`` as a float for REVENUE_ROLES; None (not shown) for other roles."""
    if not set(get_user_roles(request.user, hospital_id)) & REVENUE_ROLES:
        return None
    return float(amount)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_dashboard(request):
    """Dashboard statistics endpoint with hospital scoping."""
    hospital_id = _get_authorized_hospital(request)
    
    if not hospital_id:
        return Response({
            "error": "Hospital parameter is required or access denied",
            "detail": "Provide ?hospital=<id> query parameter for a hospital you have access to"
        }, status=403)

    # Hospital-scoped queries; a Doctor or Nurse counts only their own patients.
    def own(queryset):
        return care_view_of(queryset, request.user, hospital_id)

    patient_qs = own(Patient.objects.filter(hospital_id=hospital_id))
    doctor_qs = Doctor.objects.filter(hospital_id=hospital_id)
    appointment_qs = own(Appointment.objects.filter(hospital_id=hospital_id))
    bed_qs = Bed.objects.filter(room__ward__hospital_id=hospital_id)
    queue_qs = own(QueueToken.objects.filter(hospital_id=hospital_id))
    visit_qs = own(Visit.objects.filter(hospital_id=hospital_id))
    emergency_qs = own(EmergencyVisit.objects.filter(hospital_id=hospital_id))
    admission_qs = own(Admission.objects.filter(hospital_id=hospital_id))
    invoice_qs = own(Invoice.objects.filter(hospital_id=hospital_id))
    payment_qs = own(Payment.objects.filter(invoice__hospital_id=hospital_id))
    lab_qs = own(LabTest.objects.filter(hospital_id=hospital_id))

    today = hospital_today()
    
    # Patient stats
    total_patients = patient_qs.count()
    today_patients = patient_qs.filter(on_hospital_day("created_at", today)).count()
    
    # Doctor stats
    total_doctors = doctor_qs.count()
    active_doctors = doctor_qs.filter(status="Available").count()
    
    # Appointment stats
    total_appointments = appointment_qs.count()
    today_appointments = appointment_qs.filter(appointment_date=today).count()
    pending_appointments = appointment_qs.filter(status="Scheduled").count()
    completed_appointments = appointment_qs.filter(status="Completed").count()
    
    # Queue stats cover today's tokens only, like the queue board.
    today_queue_qs = queue_qs.filter(token_date=today)
    total_queue = today_queue_qs.count()
    waiting_queue = today_queue_qs.filter(status="Waiting").count()
    in_consultation_queue = today_queue_qs.filter(status="In Consultation").count()
    completed_queue = today_queue_qs.filter(status="Completed").count()
    
    # Bed stats
    total_beds = bed_qs.count()
    available_beds = bed_qs.filter(status="Available").count()
    occupied_beds = total_beds - available_beds
    
    # Emergency stats
    total_emergency = emergency_qs.count()
    today_emergency = emergency_qs.filter(on_hospital_day("arrival_time", today)).count()
    active_emergency = emergency_qs.filter(status__in=["Waiting", "In Treatment"]).count()
    
    # Admission/IPD stats
    total_admissions = admission_qs.count()
    current_admissions = admission_qs.filter(status="Admitted").count()
    
    # Lab stats
    total_lab_tests = lab_qs.count()
    open_lab_qs = lab_qs.exclude(status__in=LabTest.CLOSED_STATUSES)
    pending_lab_tests = open_lab_qs.count()
    completed_lab_tests = lab_qs.filter(status__in=LabTest.DONE_STATUSES).count()
    urgent_lab_tests = open_lab_qs.filter(priority="Urgent").count()
    
    # Billing stats
    total_invoices = invoice_qs.count()
    paid_invoices = invoice_qs.filter(status=Invoice.Status.PAID).count()
    pending_invoices = invoice_qs.filter(status=Invoice.Status.UNPAID).count()
    # This counted status="Partial", which an invoice never has, so it was always 0.
    partial_invoices = invoice_qs.filter(status=Invoice.Status.PARTIALLY_PAID).count()

    # Money received net of refunds (refunds are Payment rows too).
    total_revenue = _net_received(payment_qs)
    today_revenue = _net_received(payment_qs.filter(on_hospital_day("paid_at", today)))
    refunded = _sum_amount(payment_qs.filter(kind=Payment.Kind.REFUND))
    # Still owed on open bills: their totals less what was received on them.
    open_invoice_qs = invoice_qs.filter(status__in=OPEN_INVOICE_STATUSES)
    outstanding = (
        (open_invoice_qs.aggregate(total=Sum("total"))["total"] or 0)
        - _net_received(payment_qs.filter(invoice__in=open_invoice_qs))
    )

    # The token being seen now. It used to be the highest number issued today,
    # whatever its status, so dashboards said "Now serving" while nobody was
    # in consultation (BUG-03). 0 means nobody is with a doctor.
    current_token = today_queue_qs.filter(status="In Consultation").order_by("-consultation_started_at", "-token_number").first()
    current_token_number = current_token.token_number if current_token else 0
    
    # Waiting patients estimate (waiting queue * estimated wait)
    avg_wait = today_queue_qs.filter(status="Waiting").aggregate(
        avg=Sum("estimated_wait_minutes")
    )["avg"] or 0
    waiting_patients = waiting_queue
    
    # Recent patients
    recent_patients = patient_qs.order_by("-created_at")[:5]
    
    return Response({
        "statistics": {
            "patients": {
                "total": total_patients,
                "today": today_patients,
            },
            "doctors": {
                "total": total_doctors,
                "active": active_doctors,
            },
            "appointments": {
                "total": total_appointments,
                "today": today_appointments,
                "pending": pending_appointments,
                "completed": completed_appointments,
            },
            "queue": {
                "total": total_queue,
                "waiting": waiting_queue,
                "in_consultation": in_consultation_queue,
                "completed": completed_queue,
                "current_token": current_token_number,
                "waiting_patients": waiting_patients,
                "avg_wait_minutes": round(avg_wait) if avg_wait else 0,
            },
            "beds": {
                "total": total_beds,
                "available": available_beds,
                "occupied": occupied_beds,
            },
            "emergency": {
                "total": total_emergency,
                "today": today_emergency,
                "active": active_emergency,
            },
            "admissions": {
                "total": total_admissions,
                "current": current_admissions,
            },
            "laboratory": {
                "total": total_lab_tests,
                "pending": pending_lab_tests,
                "completed": completed_lab_tests,
                "urgent": urgent_lab_tests,
            },
            "billing": {
                "total_invoices": total_invoices,
                "paid": paid_invoices,
                "pending": pending_invoices,
                "partial": partial_invoices,
                "total_revenue": _money(request, hospital_id, total_revenue),
                "today_revenue": _money(request, hospital_id, today_revenue),
                "refunded": _money(request, hospital_id, refunded),
                "outstanding": _money(request, hospital_id, outstanding),
            },
        },
        "recent_patients": [
            {
                "id": patient.id,
                "name": patient.name,
                "patient_id": f"P{str(patient.id).zfill(3)}",
                "age": patient.age,
                "gender": patient.gender,
                "created_at": patient.created_at,
            }
            for patient in recent_patients
        ],
        "hospital_id": hospital_id,
        "generated_at": timezone.now(),
        "status": "success",
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_stats_summary(request):
    """Lightweight stats endpoint for quick polling."""
    hospital_id = _get_authorized_hospital(request)
    
    if not hospital_id:
        return Response({"error": "Hospital parameter required or access denied"}, status=403)

    today = hospital_today()
    
    # Quick counts only; a Doctor or Nurse counts only their own patients.
    def own(queryset):
        return care_view_of(queryset, request.user, hospital_id)

    total_patients = own(Patient.objects.filter(hospital_id=hospital_id)).count()
    today_appointments = own(Appointment.objects.filter(
        hospital_id=hospital_id,
        appointment_date=hospital_today()
    )).count()
    waiting_queue = own(QueueToken.objects.filter(
        hospital_id=hospital_id,
        token_date=today,
        status="Waiting"
    )).count()
    available_beds = Bed.objects.filter(
        room__ward__hospital_id=hospital_id,
        status="Available"
    ).count()
    total_revenue = _net_received(own(Payment.objects.filter(invoice__hospital_id=hospital_id)))

    return Response({
        "patients": total_patients,
        "today_appointments": today_appointments,
        "waiting_queue": waiting_queue,
        "available_beds": available_beds,
        "total_revenue": _money(request, hospital_id, total_revenue),
    })