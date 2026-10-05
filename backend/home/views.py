from datetime import date
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
from users.permissions import get_user_hospital_ids


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

    # Hospital-scoped queries
    patient_qs = Patient.objects.filter(hospital_id=hospital_id)
    doctor_qs = Doctor.objects.filter(hospital_id=hospital_id)
    appointment_qs = Appointment.objects.filter(hospital_id=hospital_id)
    bed_qs = Bed.objects.filter(room__ward__hospital_id=hospital_id)
    queue_qs = QueueToken.objects.filter(hospital_id=hospital_id)
    visit_qs = Visit.objects.filter(hospital_id=hospital_id)
    emergency_qs = EmergencyVisit.objects.filter(hospital_id=hospital_id)
    admission_qs = Admission.objects.filter(hospital_id=hospital_id)
    invoice_qs = Invoice.objects.filter(hospital_id=hospital_id)
    payment_qs = Payment.objects.filter(invoice__hospital_id=hospital_id)
    lab_qs = LabTest.objects.filter(patient__hospital_id=hospital_id)

    today = timezone.localdate()
    
    # Patient stats
    total_patients = patient_qs.count()
    today_patients = patient_qs.filter(created_at__date=today).count()
    
    # Doctor stats
    total_doctors = doctor_qs.count()
    active_doctors = doctor_qs.filter(status="Active").count()
    
    # Appointment stats
    total_appointments = appointment_qs.count()
    today_appointments = appointment_qs.filter(appointment_date=today).count()
    pending_appointments = appointment_qs.filter(status="Scheduled").count()
    completed_appointments = appointment_qs.filter(status="Completed").count()
    
    # Queue stats
    total_queue = queue_qs.count()
    waiting_queue = queue_qs.filter(status="Waiting").count()
    in_consultation_queue = queue_qs.filter(status="In Consultation").count()
    completed_queue = queue_qs.filter(status="Completed").count()
    
    # Bed stats
    total_beds = bed_qs.count()
    available_beds = bed_qs.filter(status="Available").count()
    occupied_beds = total_beds - available_beds
    
    # Emergency stats
    total_emergency = emergency_qs.count()
    today_emergency = emergency_qs.filter(arrival_time__date=today).count()
    active_emergency = emergency_qs.filter(status__in=["Waiting", "In Treatment"]).count()
    
    # Admission/IPD stats
    total_admissions = admission_qs.count()
    current_admissions = admission_qs.filter(status="Admitted").count()
    
    # Lab stats
    total_lab_tests = lab_qs.count()
    pending_lab_tests = lab_qs.filter(status="Pending").count()
    completed_lab_tests = lab_qs.filter(status="Completed").count()
    urgent_lab_tests = lab_qs.filter(priority="Urgent", status__in=["Pending", "Processing"]).count()
    
    # Billing stats
    total_invoices = invoice_qs.count()
    paid_invoices = invoice_qs.filter(status="Paid").count()
    pending_invoices = invoice_qs.filter(status="Unpaid").count()
    partial_invoices = invoice_qs.filter(status="Partial").count()
    
    # Revenue - use aggregation
    from django.db.models import Sum
    total_revenue = payment_qs.aggregate(total=Sum("amount"))["total"] or 0
    today_revenue = payment_qs.filter(paid_at__date=today).aggregate(total=Sum("amount"))["total"] or 0
    
    # Queue tokens for today
    current_token = queue_qs.filter(token_date=today).order_by("-token_number").first()
    current_token_number = current_token.token_number if current_token else 0
    
    # Waiting patients estimate (waiting queue * estimated wait)
    avg_wait = queue_qs.filter(status="Waiting").aggregate(
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
                "total_revenue": float(total_revenue),
                "today_revenue": float(today_revenue),
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

    today = timezone.localdate()
    
    # Quick counts only
    total_patients = Patient.objects.filter(hospital_id=hospital_id).count()
    today_appointments = Appointment.objects.filter(
        hospital_id=hospital_id,
        appointment_date=timezone.localdate()
    ).count()
    waiting_queue = QueueToken.objects.filter(
        hospital_id=hospital_id,
        status="Waiting"
    ).count()
    available_beds = Bed.objects.filter(
        room__ward__hospital_id=hospital_id,
        status="Available"
    ).count()
    total_revenue = Payment.objects.filter(
        invoice__hospital_id=hospital_id
    ).aggregate(total=Sum("amount"))["total"] or 0

    return Response({
        "patients": total_patients,
        "today_appointments": today_appointments,
        "waiting_queue": waiting_queue,
        "available_beds": available_beds,
        "total_revenue": float(total_revenue),
    })