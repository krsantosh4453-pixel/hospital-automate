from django.db import transaction
from rest_framework import serializers
from .models import (
    VitalSign,
    Allergy,
    ClinicalNote,
    Diagnosis,
    ServiceOrder,
    Procedure,
    MedicalRecord,
    Prescription,
    PrescriptionItem,
    MedicalCertificate,
    Referral,
)


def _patient_belongs_to_hospital(patient, hospital):
    """
    A patient belongs to a hospital either via the legacy PatientHospital
    membership OR the direct Patient.hospital foreign key used by the
    Patients module. Mirrors the helper in encounters/serializers.py so the
    prescription and visit flows stay consistent.
    """
    if not (patient and hospital):
        return True

    # Callers pass either a Hospital or a raw id from request data.
    try:
        hospital_id = int(getattr(hospital, "id", hospital))
    except (TypeError, ValueError):
        return False

    has_membership = patient.hospital_memberships.filter(
        hospital_id=hospital_id,
        is_active=True
    ).exists()

    has_direct_link = getattr(patient, "hospital_id", None) == hospital_id

    return has_membership or has_direct_link


class VitalSignSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSign
        fields = [
            "id",
            "visit",
            "weight",
            "height",
            "systolic_bp",
            "diastolic_bp",
            "temperature",
            "respiratory_rate",
            "heart_rate",
            "blood_sugar",
            "spo2",
            "comments",
            "recorded_at",
        ]
        read_only_fields = ["id", "recorded_at"]


class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = [
            "id",
            "patient",
            "name",
            "reaction",
            "severity",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ClinicalNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalNote
        fields = [
            "id",
            "visit",
            "doctor",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = [
            "recorded_by",
            "id",
            "visit",
            "name",
            "icd10_code",
            "diagnosis_type",
            "remarks",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "recorded_by"]


class ServiceOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrder
        fields = [
            "id",
            "visit",
            "service_name",
            "quantity",
            "status",
            "remarks",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProcedureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        fields = [
            "id",
            "visit",
            "name",
            "description",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = [
            "id",
            "patient",
            "visit",
            "summary",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ["id", "name", "dosage", "frequency", "duration", "quantity", "instructions"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Medicine name is required.")
        return value.strip()

    def validate_quantity(self, value):
        if value is None or value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class PrescriptionSerializer(serializers.ModelSerializer):
    # Nested write/read items so the Prescription page can create a
    # prescription and its medicines in a single request.
    items = PrescriptionItemSerializer(many=True)

    # Read-only display helpers so the list/table can render without extra
    # round trips (mirrors VisitSerializer in the encounters app).
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    visit_label = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            "id",
            "hospital",
            "patient",
            "doctor",
            "visit",
            "status",
            "dispensed_at",
            "created_at",
            "items",
            "patient_name",
            "doctor_name",
            "hospital_name",
            "visit_label",
        ]
        read_only_fields = ["id", "created_at", "dispensed_at"]

    def get_visit_label(self, obj):
        return f"Visit #{obj.visit_id}" if obj.visit_id else ""

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one medicine is required."
            )
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        def current(field):
            return attrs.get(field, getattr(instance, field, None))

        hospital = current("hospital")
        patient = current("patient")
        doctor = current("doctor")
        visit = current("visit")

        if hospital and patient:
            if not _patient_belongs_to_hospital(patient, hospital):
                raise serializers.ValidationError({
                    "patient": "This patient is not registered in this hospital."
                })

        if hospital and doctor and doctor.hospital_id != hospital.id:
            raise serializers.ValidationError({
                "doctor": "This doctor does not belong to this hospital."
            })

        if visit:
            if hospital and visit.hospital_id != hospital.id:
                raise serializers.ValidationError({
                    "visit": "This visit does not belong to this hospital."
                })
            if patient and visit.patient_id != patient.id:
                raise serializers.ValidationError({
                    "visit": "This visit does not belong to the selected patient."
                })

        return attrs

    def validate_hospital(self, value):
        """Ensure user has access to the hospital."""
        request = self.context.get("request")
        if request and value:
            from users.permissions import get_user_hospital_ids
            user_hospital_ids = get_user_hospital_ids(request.user)
            if value.id not in user_hospital_ids:
                raise serializers.ValidationError(
                    "You do not have access to this hospital."
                )
        return value

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        prescription = Prescription.objects.create(**validated_data)
        PrescriptionItem.objects.bulk_create([
            PrescriptionItem(prescription=prescription, **item)
            for item in items_data
        ])
        return prescription

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            PrescriptionItem.objects.bulk_create([
                PrescriptionItem(prescription=instance, **item)
                for item in items_data
            ])

        return instance

class MedicalCertificateSerializer(serializers.ModelSerializer):
    # Display fields so the certificate prints without extra requests.
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    patient_age = serializers.IntegerField(source="patient.age", read_only=True)
    patient_gender = serializers.CharField(source="patient.gender", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)
    doctor_specialization = serializers.CharField(source="doctor.specialization", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    hospital_address = serializers.CharField(source="hospital.address", read_only=True, default="")

    class Meta:
        model = MedicalCertificate
        fields = [
            "id",
            "hospital",
            "patient",
            "doctor",
            "kind",
            "diagnosis",
            "remarks",
            "start_date",
            "end_date",
            "issued_at",
            "patient_name",
            "patient_age",
            "patient_gender",
            "doctor_name",
            "doctor_specialization",
            "hospital_name",
            "hospital_address",
        ]
        read_only_fields = ["id", "doctor", "issued_at"]
        # Defaults to the acting hospital (X-Hospital-ID) in the view.
        extra_kwargs = {"hospital": {"required": False}}

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if attrs.get("kind", MedicalCertificate.Kind.SICK_LEAVE) == MedicalCertificate.Kind.SICK_LEAVE and not end:
            raise serializers.ValidationError({"end_date": "A sick-leave certificate needs an end date."})
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "The end date cannot be before the start date."})
        return attrs


class ReferralSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    patient_age = serializers.IntegerField(source="patient.age", read_only=True)
    patient_gender = serializers.CharField(source="patient.gender", read_only=True)
    referring_doctor_name = serializers.CharField(source="referring_doctor.name", read_only=True)
    referred_to_doctor_name = serializers.CharField(source="referred_to_doctor.name", read_only=True, default="")
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    hospital_address = serializers.CharField(source="hospital.address", read_only=True, default="")

    class Meta:
        model = Referral
        fields = [
            "id",
            "hospital",
            "patient",
            "visit",
            "referring_doctor",
            "referred_to_doctor",
            "referred_to_external",
            "specialty",
            "reason",
            "urgency",
            "status",
            "created_at",
            "patient_name",
            "patient_age",
            "patient_gender",
            "referring_doctor_name",
            "referred_to_doctor_name",
            "hospital_name",
            "hospital_address",
        ]
        read_only_fields = ["id", "referring_doctor", "created_at"]
        # Defaults to the acting hospital (X-Hospital-ID) in the view.
        extra_kwargs = {"hospital": {"required": False}}

    def validate(self, attrs):
        if self.instance is not None:
            # A referral is a record of what was asked: only its progress changes.
            changed = set(attrs) - {"status"}
            if changed:
                raise serializers.ValidationError(
                    {name: "Only the status of a referral can change." for name in sorted(changed)}
                )
            return attrs
        internal = attrs.get("referred_to_doctor")
        external = attrs.get("referred_to_external", "").strip()
        if bool(internal) == bool(external):
            raise serializers.ValidationError(
                {"referred_to_doctor": "Refer to one doctor of this hospital or one outside doctor/facility."}
            )
        if not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": "Give the reason for the referral."})
        attrs["referred_to_external"] = external
        return attrs
