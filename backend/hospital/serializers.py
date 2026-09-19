from rest_framework import serializers
from .models import Hospital, Department, Ward, Room, Bed


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = "__all__"


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = "__all__"