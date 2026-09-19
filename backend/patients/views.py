from django.db.models import Q
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status

from .models import Patient, PatientHospital
from .serializers import PatientSerializer, PatientHospitalSerializer


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer

    def get_queryset(self):
        hospital_id = self.request.query_params.get("hospital")

        if hospital_id:
            # Preserve the existing membership-based scoping AND support
            # the direct hospital field used by the Patients UI form.
            return Patient.objects.filter(
                Q(hospital_id=hospital_id)
                | Q(
                    hospital_memberships__hospital_id=hospital_id,
                    hospital_memberships__is_active=True,
                )
            ).distinct()

        return Patient.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


class PatientHospitalViewSet(viewsets.ModelViewSet):
    queryset = PatientHospital.objects.all()
    serializer_class = PatientHospitalSerializer