from rest_framework import viewsets
from .models import Compounder
from .serializers import CompounderSerializer
from users.permissions import IsStaffUser


class CompounderViewSet(viewsets.ModelViewSet):
    queryset = Compounder.objects.all()
    serializer_class = CompounderSerializer
    permission_classes = [IsStaffUser]
