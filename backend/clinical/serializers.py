from decimal import Decimal

from config.hospital_time import hospital_today

from django.db import transaction
from rest_framework import serializers

from .medication_safety import blocking
from .models import (
    Immunization,
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
    bmi = serializers.SerializerMethodField()
    recorded_by_name = serializers.SerializerMethodField()

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
            "pain_score",
            "gcs",
            "avpu",
            "head_circumference",
            "muac",
            "urine_output",
            "fluid_intake",
            "oxygen_device",
            "oxygen_flow",
            "mobility",
            "injuries",
            "bmi",
            "recorded_by",
            "recorded_by_name",
            "comments",
            "recorded_at",
        ]
        read_only_fields = ["id", "bmi", "recorded_by", "recorded_by_name", "recorded_at"]

    def get_bmi(self, obj):
        """kg / m^2 to one decimal, from this reading's weight and height (cm)."""
        if not obj.weight or not obj.height:
            return None
        metres = Decimal(obj.height) / 100
        return float(round(Decimal(obj.weight) / (metres * metres), 1))

    def get_recorded_by_name(self, obj) -> str:
        user = obj.recorded_by
        return (user.get_full_name() or user.username) if user else ""

    def validate(self, attrs):
        device = attrs.get("oxygen_device", getattr(self.instance, "oxygen_device", ""))
        flow = attrs.get("oxygen_flow", getattr(self.instance, "oxygen_flow", None))
        if flow and device in ("", VitalSign.OxygenDevice.ROOM_AIR):
            raise serializers.ValidationError({"oxygen_flow": "Give the oxygen device for a flow rate."})
        return attrs


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
            *[field for field, _ in ClinicalNote.SECTIONS],
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        # On a partial update the stored value stands in for a field not sent.
        def current(field):
            if field in attrs:
                return attrs[field] or ""
            return getattr(self.instance, field, "") if self.instance else ""

        if not any(current(field).strip() for field, _ in ClinicalNote.SECTIONS):
            raise serializers.ValidationError({"note": "Write at least one part of the note."})
        return attrs


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
    # Issued so far by the pharmacy; the rest can still be dispensed.
    dispensed_quantity = serializers.SerializerMethodField()

    class Meta:
        model = PrescriptionItem
        fields = ["id", "name", "dosage", "frequency", "duration", "quantity", "instructions", "dispensed_quantity"]

    def get_dispensed_quantity(self, obj) -> int:
        if not obj.pk:
            return 0
        return sum(sale.quantity for sale in obj.pharmacy_sales.all())

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Medicine name is required.")
        return value.strip()

    def validate_quantity(self, value):
        if value is None or value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


MIN_OVERRIDE_REASON = 10
# How far back a paper prescription may be dated when it is transcribed.
MAX_PAPER_AGE_DAYS = 180
# Set only by the pharmacy's dispense endpoint, when medicine is really issued.
DISPENSE_STATUSES = ("Dispensed", "Partially Dispensed")


class PrescriptionSerializer(serializers.ModelSerializer):
    # Set on PrescriptionTranscriptionSerializer, the pharmacy's paper-transcription form (F13).
    transcribing = False

    # Nested write/read items so the Prescription page can create a
    # prescription and its medicines in a single request.
    items = PrescriptionItemSerializer(many=True)
    # The doctor's reason to prescribe despite a high-severity safety alert.
    safety_override_reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)

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
            "patient_uhid",
            "doctor_name",
            "hospital_name",
            "visit_label",
            "safety_alerts",
            "safety_override_reason",
            "source",
            "original_prescriber_name",
            "original_prescriber_registration",
            "original_prescription_date",
            "transcribed_by",
            "transcribed_by_name",
            "verified_by",
            "verified_by_name",
            "verified_at",
        ]
        # F13: where a prescription came from is recorded only by the
        # transcribe and verify actions (PrescriptionViewSet).
        read_only_fields = [
            "id", "created_at", "dispensed_at", "safety_alerts", "source", "original_prescriber_name",
            "original_prescriber_registration", "original_prescription_date", "transcribed_by", "verified_by",
            "verified_at",
        ]

    transcribed_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    # F6: shown in the pharmacy queue; the UHID at the prescription's own hospital.
    patient_uhid = serializers.SerializerMethodField()

    def get_patient_uhid(self, obj) -> str:
        if not obj.patient_id:
            return ""
        memberships = getattr(obj.patient, "_prefetched_objects_cache", {}).get("hospital_memberships")
        if memberships is None:
            memberships = obj.patient.hospital_memberships.all()
        return next((m.uhid for m in memberships if m.hospital_id == obj.hospital_id and m.is_active), "")

    @staticmethod
    def _user_name(user):
        return (user.get_full_name() or user.username) if user else ""

    def get_transcribed_by_name(self, obj) -> str:
        return self._user_name(obj.transcribed_by)

    def get_verified_by_name(self, obj) -> str:
        return self._user_name(obj.verified_by)

    def get_visit_label(self, obj) -> str:
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

        status = attrs.get("status")
        current_status = getattr(instance, "status", None)
        if status in DISPENSE_STATUSES and status != current_status:
            raise serializers.ValidationError({
                "status": "The pharmacy records dispensing when it issues the medicine."
            })
        if status and status != current_status and not self.transcribing:
            if status == Prescription.PENDING_VERIFICATION:
                raise serializers.ValidationError({
                    "status": "Only a transcribed paper prescription waits for verification."
                })
            if current_status == Prescription.PENDING_VERIFICATION and status != "Cancelled":
                raise serializers.ValidationError({
                    "status": "A second pharmacist or an Admin verifies this transcription with Verify."
                })

        own_doctor = self._sign_as_requesting_doctor(attrs, instance, hospital) if hospital else None

        if visit:
            if hospital and visit.hospital_id != hospital.id:
                raise serializers.ValidationError({
                    "visit": "This visit does not belong to this hospital."
                })
            if patient and visit.patient_id != patient.id:
                raise serializers.ValidationError({
                    "visit": "This visit does not belong to the selected patient."
                })
            # F4: a doctor prescribes on their own visit (or one with no doctor yet).
            if own_doctor is not None and visit.doctor_id not in (None, own_doctor.pk):
                raise serializers.ValidationError({
                    "visit": "This visit is another doctor's; prescribe from your own consultation."
                })

        if "items" in attrs and hospital:
            self._check_medication_safety(attrs, hospital, patient)

        return attrs

    def _sign_as_requesting_doctor(self, attrs, instance, hospital):
        """
        A doctor prescribes in their own name; an Admin may record one for any
        doctor here. Returns the requesting doctor's profile when the rule
        applied to them, else None.
        """
        from doctors.models import Doctor
        from users.models import StaffRole
        from users.permissions import get_user_roles

        request = self.context.get("request")
        user = getattr(request, "user", None)
        roles = get_user_roles(user, hospital.id)
        if StaffRole.DOCTOR not in roles or StaffRole.ADMIN in roles:
            return None
        own = Doctor.objects.filter(user=user, hospital=hospital).first()
        if own is None:
            return None
        named = attrs.get("doctor")
        if named is not None and named != own:
            raise serializers.ValidationError({"doctor": "You can only prescribe in your own name."})
        if instance is None and named is None:
            attrs["doctor"] = own
        return own

    def _check_medication_safety(self, attrs, hospital, patient):
        """High-severity alerts block the prescription unless the doctor records why."""
        from .medication_safety import blocking, check_items

        alerts = check_items(hospital, patient, [item["name"] for item in attrs["items"]])
        reason = (attrs.get("safety_override_reason") or "").strip()
        high = blocking(alerts)
        if high and len(reason) < MIN_OVERRIDE_REASON:
            summary = "; ".join(f"{', '.join(alert['medicines'])}: {alert['message']}" for alert in high)
            raise serializers.ValidationError({
                "safety_override_reason": (
                    f"High-risk medication alert: {summary} "
                    f"To prescribe anyway, record your reason (at least {MIN_OVERRIDE_REASON} characters)."
                )
            })
        attrs["safety_alerts"] = alerts
        attrs["safety_override_reason"] = reason if high else ""

    def _audit_override(self, prescription):
        if not blocking(prescription.safety_alerts):
            return
        from audit.services import record_audit

        record_audit(
            self.context.get("request"), "clinical.prescription.safety_override", prescription,
            hospital=prescription.hospital_id,
            details={
                "rules": [alert["rule"] for alert in blocking(prescription.safety_alerts)],
                "reason": prescription.safety_override_reason,
            },
        )

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
        self._audit_override(prescription)
        return prescription

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        if items_data is not None and instance.pharmacy_sales.exists():
            # Replacing the lines would cut them off from what was issued and billed.
            raise serializers.ValidationError({
                "items": "Medicine has already been issued for this prescription; write a new one instead."
            })

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            PrescriptionItem.objects.bulk_create([
                PrescriptionItem(prescription=instance, **item)
                for item in items_data
            ])
            self._audit_override(instance)

        return instance

class PrescriptionTranscriptionSerializer(PrescriptionSerializer):
    """
    F13: a paper prescription copied in by the pharmacy. It names who signed
    the paper (a doctor of this hospital, or an outside doctor by name and
    registration number) and its date, and is saved Pending Verification
    with the transcriber recorded; the view sets those.
    """

    transcribing = True

    class Meta(PrescriptionSerializer.Meta):
        read_only_fields = [
            "id", "created_at", "dispensed_at", "safety_alerts", "source", "status", "transcribed_by",
            "verified_by", "verified_at",
        ]
        extra_kwargs = {"original_prescription_date": {"required": True, "allow_null": False}}

    def validate_original_prescription_date(self, value):
        from datetime import timedelta

        today = hospital_today()
        if value > today:
            raise serializers.ValidationError("The prescription date cannot be in the future.")
        if value < today - timedelta(days=MAX_PAPER_AGE_DAYS):
            raise serializers.ValidationError(
                f"Paper prescriptions older than {MAX_PAPER_AGE_DAYS} days cannot be transcribed.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        name = (attrs.get("original_prescriber_name") or "").strip()
        registration = (attrs.get("original_prescriber_registration") or "").strip()
        if attrs.get("doctor") is None and not name:
            raise serializers.ValidationError({
                "original_prescriber_name": "Name the doctor who signed the paper prescription."
            })
        if attrs.get("doctor") is None and not registration:
            raise serializers.ValidationError({
                "original_prescriber_registration": "Give the outside doctor's registration number."
            })
        attrs["original_prescriber_name"] = name or attrs["doctor"].name
        attrs["original_prescriber_registration"] = registration
        return attrs


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


class ImmunizationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Immunization
        fields = [
            "id",
            "hospital",
            "patient",
            "vaccine",
            "dose_number",
            "administered_on",
            "batch_number",
            "manufacturer",
            "route",
            "site",
            "next_due_on",
            "notes",
            "recorded_by",
            "created_at",
            "patient_name",
            "recorded_by_name",
        ]
        read_only_fields = ["id", "recorded_by", "created_at"]
        # Defaults to the acting hospital (X-Hospital-ID) in the view.
        extra_kwargs = {"hospital": {"required": False}}

    def get_recorded_by_name(self, obj):
        user = obj.recorded_by
        return (user.get_full_name() or user.username) if user else ""

    def validate(self, attrs):
        vaccine = attrs.get("vaccine")
        if vaccine is not None:
            if not vaccine.strip():
                raise serializers.ValidationError({"vaccine": "Name the vaccine."})
            attrs["vaccine"] = vaccine.strip()
        given = attrs.get("administered_on", getattr(self.instance, "administered_on", None))
        due = attrs.get("next_due_on", getattr(self.instance, "next_due_on", None))
        if given and given > hospital_today():
            raise serializers.ValidationError({"administered_on": "A dose cannot be recorded in the future."})
        if given and due and due <= given:
            raise serializers.ValidationError({"next_due_on": "The next dose must be due after this one."})
        return attrs
