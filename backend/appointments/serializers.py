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
        fields = "__all__"

    def validate(self, attrs):
        hospital = attrs.get("hospital")
        patient = attrs.get("patient")
        doctor = attrs.get("doctor")

        if hospital and patient:
            # A patient counts as "belonging" to the hospital either via
            # the legacy PatientHospital membership OR the direct
            # Patient.hospital foreign key added by the Patients module.
            # Both are honoured so the appointment flow works with the
            # way patients are actually created today.
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