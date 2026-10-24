from rest_framework import serializers
from .models import Hospital, Department, Ward, Room, Bed


class HospitalSerializer(serializers.ModelSerializer):
    type = serializers.ChoiceField(source="hospital_type", choices=Hospital.Type.choices, required=False)
    status = serializers.SerializerMethodField()
    departments = serializers.SerializerMethodField()
    doctors = serializers.SerializerMethodField()
    nurses = serializers.SerializerMethodField()

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def get_departments(self, obj):
        return obj.departments.count()

    def get_doctors(self, obj):
        return obj.doctors.count()

    def get_nurses(self, obj):
        return obj.nurses.count()

    def validate_code(self, value):
        return (value or "").strip().upper() or None

    class Meta:
        model = Hospital
        fields = [
            "id",
            "name",
            "code",
            "type",
            "status",
            "departments",
            "doctors",
            "nurses",
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
    head_name = serializers.CharField(source="head.name", read_only=True, default="")
    doctors = serializers.SerializerMethodField()

    def get_doctors(self, obj):
        return obj.doctors.count()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        hospital = attrs.get("hospital", getattr(self.instance, "hospital", None))
        head = attrs.get("head")
        if head is not None and head.hospital_id != getattr(hospital, "pk", None):
            raise serializers.ValidationError({"head": "The head must be a doctor of this hospital."})
        return attrs

    class Meta:
        model = Department
        fields = [
            "id",
            "hospital",
            "name",
            "code",
            "head",
            "head_name",
            "doctors",
            "description",
            "is_active",
        ]
        read_only_fields = ["id", "head_name", "doctors"]


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