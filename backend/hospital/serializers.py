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


# Bed states. "Occupied" is set by allocating the bed to an admission.
BED_STATUSES = ("Available", "Occupied", "Maintenance", "Cleaning", "Reserved")


def _refuse_duplicate(model, field, value, instance, label, **scope):
    """Names are unique within their parent, ignoring case and spaces."""
    clashes = model.objects.filter(**scope, **{f"{field}__iexact": value})
    if instance is not None:
        clashes = clashes.exclude(pk=instance.pk)
    if clashes.exists():
        raise serializers.ValidationError({field: f"{label} {value} already exists here."})


def _clean_name(value, label):
    value = (value or "").strip()
    if not value:
        raise serializers.ValidationError(f"{label} is required.")
    return value


class WardSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        return _clean_name(value, "Ward name")

    def validate(self, attrs):
        hospital = attrs.get("hospital", getattr(self.instance, "hospital", None))
        name = attrs.get("name", getattr(self.instance, "name", ""))
        _refuse_duplicate(Ward, "name", name, self.instance, "Ward", hospital=hospital)
        return attrs

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
    def validate_room_number(self, value):
        return _clean_name(value, "Room number")

    def validate(self, attrs):
        ward = attrs.get("ward", getattr(self.instance, "ward", None))
        number = attrs.get("room_number", getattr(self.instance, "room_number", ""))
        _refuse_duplicate(Room, "room_number", number, self.instance, "Room", ward=ward)
        return attrs

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
    status = serializers.ChoiceField(choices=BED_STATUSES, required=False)

    def validate_bed_number(self, value):
        return _clean_name(value, "Bed number")

    def validate_status(self, value):
        if self.instance is None and value == "Occupied":
            raise serializers.ValidationError("A new bed cannot start as Occupied; allocate it to an admission.")
        return value

    def validate(self, attrs):
        room = attrs.get("room", getattr(self.instance, "room", None))
        number = attrs.get("bed_number", getattr(self.instance, "bed_number", ""))
        _refuse_duplicate(Bed, "bed_number", number, self.instance, "Bed", room=room)
        return attrs

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