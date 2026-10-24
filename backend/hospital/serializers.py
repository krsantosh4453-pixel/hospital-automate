from rest_framework import serializers
from .models import Hospital, Department, Ward, Room, Bed


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            "id",
            "name",
            "address",
            "city",
            "state",
            "phone",
            "email",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            "id",
            "hospital",
            "name",
            "description",
            "is_active",
        ]
        read_only_fields = ["id"]


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = [
            "id",
            "hospital",
            "name",
            "ward_type",
        ]
        read_only_fields = ["id"]


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            "id",
            "ward",
            "room_number",
            "room_type",
        ]
        read_only_fields = ["id"]


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = [
            "id",
            "room",
            "bed_number",
            "bed_type",
            "status",
        ]
        read_only_fields = ["id"]