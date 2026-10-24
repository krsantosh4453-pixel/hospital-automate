from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Appointment
from .serializers import AppointmentSerializer
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsReceptionist, IsDoctor, IsPatientReadOnly


class AppointmentViewSet(HospitalScopedViewSet):
    queryset = Appointment.objects.select_related("patient", "doctor", "hospital")
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsPatientReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        # Additional filters
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        appointment_date = self.request.query_params.get("appointment_date")
        if appointment_date:
            queryset = queryset.filter(appointment_date=appointment_date)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an appointment."""
        appointment = self.get_object()
        appointment.status = "Cancelled"
        appointment.save()
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        """Reschedule an appointment."""
        appointment = self.get_object()
        appointment_date = request.data.get("appointment_date")
        appointment_time = request.data.get("appointment_time")
        
        if appointment_date:
            appointment.appointment_date = appointment_date
        if appointment_time:
            appointment.appointment_time = appointment_time
        appointment.save()
        return Response(self.get_serializer(appointment).data)