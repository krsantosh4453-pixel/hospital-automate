from rest_framework import viewsets

from .models import Doctor
from .serializers import DoctorSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorSerializer

    def get_queryset(self):
        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            return Doctor.objects.filter(
                hospital_id=hospital_id
            )

        return Doctor.objects.all()