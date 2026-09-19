from rest_framework import serializers
from .models import EmergencyVisit


class EmergencyVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyVisit
        fields = "__all__"