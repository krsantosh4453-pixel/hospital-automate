from rest_framework import viewsets

from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            return Appointment.objects.filter(
                hospital_id=hospital_id
            )

        return Appointment.objects.all()