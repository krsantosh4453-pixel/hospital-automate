from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    # ------------------------------------------------------------------
    # Read-only display helpers.
    # The React appointment table is flat and shows the patient/doctor as
    # plain names. These expose the related object's name so the existing
    # UI columns keep working without changing the model relationships
    # (patient / doctor / hospital stay as foreign keys).
    # read_only=True => they never participate in validation or writes.
    # ------------------------------------------------------------------
    patient_name = serializers.CharField(
        source="patient.name",
        read_only=True
    )
    doctor_name = serializers.CharField(
        source="doctor.name",
        read_only=True
    )
    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "hospital",
            "patient",
            "doctor",
            "appointment_date",
            "appointment_time",
            "status",
            "reason",
            "village",
            "contact",
            "created_at",
            "patient_name",
            "doctor_name",
            "hospital_name",
        ]
        read_only_fields = ["id", "created_at"]

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

    def validate_patient(self, value):
        """Ensure patient belongs to the hospital."""
        hospital_id = self.initial_data.get("hospital")
        if hospital_id and value:
            from hospital.models import Hospital
            try:
                hospital = Hospital.objects.get(pk=hospital_id)
            except Hospital.DoesNotExist:
                raise serializers.ValidationError({
                    "hospital": "Invalid hospital."
                })
            has_membership = value.hospital_memberships.filter(
                hospital=hospital,
                is_active=True
            ).exists()

            has_direct_link = (
                getattr(value, "hospital_id", None)
                == hospital.id
            )

            if not (has_membership or has_direct_link):
                raise serializers.ValidationError({
                    "patient": "This patient is not registered in this hospital."
                })
        return value

    def validate(self, attrs):
        hospital = attrs.get("hospital")
        patient = attrs.get("patient")
        doctor = attrs.get("doctor")

        if hospital and patient:
            has_membership = patient.hospital_memberships.filter(
                hospital=hospital,
                is_active=True
            ).exists()

            has_direct_link = (
                getattr(patient, "hospital_id", None)
                == hospital.id
            )

            if not (has_membership or has_direct_link):
                raise serializers.ValidationError({
                    "patient": "This patient is not registered in this hospital."
                })

        if hospital and doctor:
            if doctor.hospital_id != hospital.id:
                raise serializers.ValidationError({
                    "doctor": "This doctor does not belong to this hospital."
                })

        return attrs