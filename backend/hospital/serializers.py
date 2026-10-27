from django.db import transaction
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


def bed_in_use(bed):
    """True while an admission holds the bed (an active BedAllocation)."""
    return bed is not None and bed.allocations.filter(is_active=True).exists()


class BedSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=BED_STATUSES, required=False)
    ward = serializers.IntegerField(source="room.ward_id", read_only=True)
    ward_name = serializers.CharField(source="room.ward.name", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    current_patient = serializers.SerializerMethodField()

    def get_current_patient(self, bed):
        if hasattr(bed, "current_patient_name"):  # annotated by BedViewSet
            return bed.current_patient_name
        active = bed.allocations.filter(is_active=True).select_related("admission__patient").first()
        return active.admission.patient.name if active else None

    def validate_bed_number(self, value):
        return _clean_name(value, "Bed number")

    def validate_status(self, value):
        # Occupied is set and cleared only by allocating / releasing the bed.
        in_use = bed_in_use(self.instance)
        if value == "Occupied" and not in_use:
            raise serializers.ValidationError("Occupied is set by allocating the bed to an admission.")
        if in_use and value != "Occupied":
            raise serializers.ValidationError("This bed is in use. Release it from the admission first.")
        return value

    def validate(self, attrs):
        room = attrs.get("room", getattr(self.instance, "room", None))
        if "room" in attrs and self.instance is not None and room != self.instance.room and bed_in_use(self.instance):
            raise serializers.ValidationError({"room": "This bed is in use. Release it before moving it to another room."})
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
            "ward",
            "ward_name",
            "room_number",
            "current_patient",
        ]
        read_only_fields = ["id"]

MAX_ROOMS_PER_WARD = 100
MAX_BEDS_PER_ROOM = 50


class RoomWithBedsSerializer(serializers.Serializer):
    room_number = serializers.CharField(max_length=50)
    room_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    beds = serializers.IntegerField(min_value=1, max_value=MAX_BEDS_PER_ROOM)
    bed_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")

    def validate_room_number(self, value):
        return _clean_name(value, "Room number")


class WardWithBedsSerializer(serializers.ModelSerializer):
    """
    A new ward with its rooms and numbered beds, created together during
    hospital setup. Beds are named <room>-1, <room>-2, … and start Available.
    """

    rooms = RoomWithBedsSerializer(many=True, write_only=True)
    room_count = serializers.SerializerMethodField()
    bed_count = serializers.SerializerMethodField()

    def get_room_count(self, ward):
        return ward.rooms.count()

    def get_bed_count(self, ward):
        return Bed.objects.filter(room__ward=ward).count()

    def validate_name(self, value):
        return _clean_name(value, "Ward name")

    def validate_rooms(self, rooms):
        if not rooms:
            raise serializers.ValidationError("Add at least one room.")
        if len(rooms) > MAX_ROOMS_PER_WARD:
            raise serializers.ValidationError(f"A ward can have at most {MAX_ROOMS_PER_WARD} rooms.")
        numbers = [room["room_number"].lower() for room in rooms]
        if len(set(numbers)) != len(numbers):
            raise serializers.ValidationError("Each room number must be different.")
        return rooms

    def validate(self, attrs):
        _refuse_duplicate(Ward, "name", attrs["name"], None, "Ward", hospital=attrs["hospital"])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        rooms = validated_data.pop("rooms")
        ward = Ward.objects.create(**validated_data)
        for spec in rooms:
            room = Room.objects.create(ward=ward, room_number=spec["room_number"], room_type=spec["room_type"])
            Bed.objects.bulk_create(
                Bed(room=room, bed_number=f"{room.room_number}-{n}", bed_type=spec["bed_type"], status="Available")
                for n in range(1, spec["beds"] + 1)
            )
        return ward

    class Meta:
        model = Ward
        fields = ["id", "hospital", "name", "ward_type", "rooms", "room_count", "bed_count"]
        read_only_fields = ["id", "room_count", "bed_count"]
