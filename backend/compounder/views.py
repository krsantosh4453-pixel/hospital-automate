from rest_framework import viewsets
from users.viewsets import HospitalScopedViewSet
from users.permissions import IsAdmin, IsHospitalManager, IsCompounder
from .models import Compounder
from .serializers import CompounderSerializer


class CompounderViewSet(HospitalScopedViewSet):
    queryset = Compounder.objects.all()
    serializer_class = CompounderSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsCompounder]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        return qs
