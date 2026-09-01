from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id',
            'name',
            'age',
            'gender',
            'phone',
            'doctor',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
