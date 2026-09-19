from datetime import date

from rest_framework.decorators import api_view
from rest_framework.response import Response

from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from hospital.models import Bed


@api_view(["GET"])
def home_dashboard(request):
    total_patients = Patient.objects.count()

    total_doctors = Doctor.objects.filter(
        status="Active"
    ).count()

    today_appointments = Appointment.objects.filter(
        appointment_date=date.today()
    ).count()

    available_beds = Bed.objects.filter(
        status="Available"
    ).count()

    recent_patients = Patient.objects.order_by(
        "-created_at"
    )[:3]

    return Response({
        "statistics": {
            "total_patients": total_patients,
            "doctors": total_doctors,
            "today_appointments": today_appointments,
            "available_beds": available_beds,
        },

        "recent_patients": [
            {
                "id": patient.id,
                "name": patient.name,
            }
            for patient in recent_patients
        ],

        "status": "success",
    })