from rest_framework import serializers
from .models import Compounder


class CompounderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compounder
        fields = "__all__"