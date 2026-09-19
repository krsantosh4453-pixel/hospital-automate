from rest_framework import viewsets
from .models import Compounder
from .serializers import CompounderSerializer


class CompounderViewSet(viewsets.ModelViewSet):
    queryset = Compounder.objects.all()
    serializer_class = CompounderSerializer
