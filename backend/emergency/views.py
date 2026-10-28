from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from users.viewsets import HospitalScopedViewSet
from users.permissions import IsDoctor, IsHospitalManagerReadOnly, IsNurse
from rest_framework.exceptions import ValidationError
from doctors.models import Doctor
from nurses.models import Nurse
from .models import (
    EmergencyVisit,
    EmergencyTriage,
    EmergencyVitals,
    EmergencyOrder,
    EmergencyMedication,
    EmergencyNote,
)
from .serializers import (
    EmergencyVisitSerializer,
    EmergencyVisitCreateSerializer,
    EmergencyTriageSerializer,
    EmergencyVitalsSerializer,
    EmergencyOrderSerializer,
    EmergencyMedicationSerializer,
    EmergencyNoteSerializer,
)



def _hospital_staff(model, value, hospital_id, field):
    """Resolve a staff id from the request to a record of the visit's hospital.

    The id used to be assigned straight to the ForeignKey (a 500 for any
    value) and was never checked against the hospital.
    """
    if value in (None, ""):
        return None
    try:
        pk = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field: "Must be an id."})
    obj = model.objects.filter(pk=pk, hospital_id=hospital_id).first()
    if obj is None:
        raise ValidationError({field: "Not found at this hospital."})
    return obj

class EmergencyVisitViewSet(HospitalScopedViewSet):
    queryset = EmergencyVisit.objects.select_related("hospital", "patient", "attending_doctor").prefetch_related(
        "triage", "vitals_records", "orders", "medications", "notes__written_by"
    )
    serializer_class = EmergencyVisitSerializer
    permission_classes = [IsDoctor | IsNurse | IsHospitalManagerReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return EmergencyVisitCreateSerializer
        return EmergencyVisitSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        visit_status = self.request.query_params.get("status")
        if visit_status:
            qs = qs.filter(status=visit_status)
        triage_level = self.request.query_params.get("triage_level")
        if triage_level:
            qs = qs.filter(triage_level=triage_level)
        return qs

    @action(detail=True, methods=["post"])
    def start_triage(self, request, pk=None):
        """Start triage process."""
        visit = self.get_object()

        if visit.status != "Registered":
            return Response(
                {"detail": "Triage can only be started for registered patients."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        visit.status = "Triage"
        visit.triage_time = timezone.now()
        visit.save()

        return Response(EmergencyVisitSerializer(visit).data)

    @action(detail=True, methods=["post"])
    def complete_triage(self, request, pk=None):
        """Complete triage with assessment."""
        visit = self.get_object()

        if visit.status != "Triage":
            return Response(
                {"detail": "Triage must be started first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        triage_data = request.data
        triage, created = EmergencyTriage.objects.update_or_create(
            visit=visit,
            defaults={
                "chief_complaint": triage_data.get("chief_complaint", ""),
                "vitals": triage_data.get("vitals", {}),
                "pain_score": triage_data.get("pain_score"),
                "glasgow_coma_scale": triage_data.get("glasgow_coma_scale"),
                "triage_notes": triage_data.get("triage_notes", ""),
                "triaged_by": _hospital_staff(Nurse, triage_data.get("triaged_by"), visit.hospital_id, "triaged_by"),
            }
        )

        visit.triage_level = triage_data.get("triage_level", visit.triage_level)
        visit.status = "Waiting"
        visit.save()

        return Response(EmergencyVisitSerializer(visit).data)

    @action(detail=True, methods=["post"])
    def start_consultation(self, request, pk=None):
        """Doctor starts consultation."""
        visit = self.get_object()

        if visit.status not in ["Waiting", "Triage"]:
            return Response(
                {"detail": "Patient must be waiting or in triage for consultation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = _hospital_staff(Doctor, request.data.get("doctor_id"), visit.hospital_id, "doctor_id")
        if doctor:
            visit.attending_doctor = doctor

        visit.status = "Under Consultation"
        visit.consultation_start_time = timezone.now()
        visit.save()

        return Response(EmergencyVisitSerializer(visit).data)

    @action(detail=True, methods=["post"])
    def add_vitals(self, request, pk=None):
        """Record vitals for ER patient."""
        visit = self.get_object()

        vitals = EmergencyVitals.objects.create(
            visit=visit,
            temperature=request.data.get("temperature"),
            systolic_bp=request.data.get("systolic_bp"),
            diastolic_bp=request.data.get("diastolic_bp"),
            heart_rate=request.data.get("heart_rate"),
            respiratory_rate=request.data.get("respiratory_rate"),
            spo2=request.data.get("spo2"),
            blood_sugar=request.data.get("blood_sugar"),
            recorded_by=_hospital_staff(Nurse, request.data.get("recorded_by"), visit.hospital_id, "recorded_by"),
        )

        return Response(EmergencyVitalsSerializer(vitals).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_order(self, request, pk=None):
        """Add investigation/treatment order."""
        visit = self.get_object()

        order = EmergencyOrder.objects.create(
            visit=visit,
            order_type=request.data.get("order_type"),
            description=request.data.get("description"),
            ordered_by=_hospital_staff(Doctor, request.data.get("ordered_by"), visit.hospital_id, "ordered_by"),
        )

        if visit.status == "Under Consultation":
            visit.status = "Investigations"
            visit.save()

        return Response(EmergencyOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_medication(self, request, pk=None):
        """Prescribe medication."""
        visit = self.get_object()

        medication = EmergencyMedication.objects.create(
            visit=visit,
            name=request.data.get("name"),
            dose=request.data.get("dose"),
            route=request.data.get("route"),
            frequency=request.data.get("frequency"),
            duration=request.data.get("duration", ""),
            prescribed_by=_hospital_staff(Doctor, request.data.get("prescribed_by"), visit.hospital_id, "prescribed_by"),
        )

        return Response(EmergencyMedicationSerializer(medication).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def administer_medication(self, request, pk=None):
        """Mark medication as administered."""
        visit = self.get_object()
        medication_id = request.data.get("medication_id")

        try:
            medication = visit.medications.get(id=medication_id)
        except EmergencyMedication.DoesNotExist:
            return Response(
                {"detail": "Medication not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        medication.administered = True
        medication.administered_by = _hospital_staff(Nurse, request.data.get("administered_by"), visit.hospital_id, "administered_by")
        medication.administered_at = timezone.now()
        medication.save()

        return Response(EmergencyMedicationSerializer(medication).data)

    @action(detail=True, methods=["post"])
    def admit_to_ipd(self, request, pk=None):
        """Admit patient to IPD - creates admission and transfers care."""
        visit = self.get_object()

        if visit.status not in ["Under Consultation", "Investigations", "Treatment", "Observation"]:
            return Response(
                {"detail": "Patient must be under care before admission."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bed_id = request.data.get("bed_id")
        if not bed_id:
            return Response(
                {"detail": "bed_id is required for admission."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                from ipd.models import Admission, BedAllocation
                from hospital.models import Bed

                bed = Bed.objects.select_for_update().get(id=bed_id, room__ward__hospital=visit.hospital)
                if bed.status != "Available":
                    return Response(
                        {"detail": "Bed is not available."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                bed.status = "Occupied"
                bed.save()

                admission = Admission.objects.create(
                    patient=visit.patient,
                    hospital=visit.hospital,
                    status="Admitted",
                    reason=f"ER Admission: {visit.triage.chief_complaint if hasattr(visit, 'triage') else 'Emergency'}",
                    admitting_doctor=visit.attending_doctor,
                )

                BedAllocation.objects.create(
                    admission=admission,
                    bed=bed,
                    is_active=True,
                )

                visit.status = "Admitted"
                visit.disposition = "Admitted"
                visit.discharge_time = timezone.now()
                visit.save()

        except Bed.DoesNotExist:
            return Response(
                {"detail": "Bed not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "detail": "Patient admitted to IPD",
                "admission": {
                    "id": admission.id,
                    "patient": admission.patient.name,
                    "bed": f"{bed.room.ward.name} - {bed.room.room_number} - {bed.bed_number}",
                }
            }
        )

    @action(detail=True, methods=["post"])
    def discharge(self, request, pk=None):
        """Discharge patient from ER."""
        visit = self.get_object()

        if visit.status in ["Admitted", "Discharged", "Referred", "Expired", "Left Against Advice"]:
            return Response(
                {"detail": f"Cannot discharge patient with status {visit.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        visit.status = "Discharged"
        visit.discharge_time = timezone.now()
        visit.disposition = "Discharged"
        visit.discharge_diagnosis = request.data.get("discharge_diagnosis", "")
        visit.follow_up_instructions = request.data.get("follow_up_instructions", "")
        visit.save()

        return Response(EmergencyVisitSerializer(visit).data)

    @action(detail=True, methods=["post"])
    def refer(self, request, pk=None):
        """Refer patient to another facility."""
        visit = self.get_object()

        if visit.status in ["Admitted", "Discharged", "Referred", "Expired"]:
            return Response(
                {"detail": f"Cannot refer patient with status {visit.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        visit.status = "Referred"
        visit.discharge_time = timezone.now()
        visit.disposition = "Referred"
        visit.discharge_diagnosis = request.data.get("discharge_diagnosis", "")
        visit.follow_up_instructions = request.data.get("follow_up_instructions", "")
        visit.remarks = f"Referred to: {request.data.get('referred_to', '')}. {visit.remarks}"
        visit.save()

        return Response(EmergencyVisitSerializer(visit).data)

    @action(detail=True, methods=["post"])
    def add_note(self, request, pk=None):
        """ER action "Doctor Notes": append a note; notes are never edited."""
        visit = self.get_object()
        text = str(request.data.get("note", "")).strip()
        if not text:
            raise ValidationError({"note": "Write the note."})
        note = EmergencyNote.objects.create(visit=visit, note=text, written_by=request.user)
        self._audit("note", visit)
        return Response(EmergencyNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def charge_slip(self, request, pk=None):
        """ER action "Charge Slip Details": everything done in this visit that can be billed."""
        visit = self.get_object()
        lines = [
            {"date": order.ordered_at, "kind": order.get_order_type_display(), "description": order.description,
             "status": order.status}
            for order in visit.orders.all()
        ] + [
            {"date": med.prescribed_at, "kind": "Medicine",
             "description": f"{med.name} {med.dose} {med.route}".strip(),
             "status": "Given" if med.administered else "Prescribed"}
            for med in visit.medications.all()
        ]
        lines.sort(key=lambda line: line["date"])
        return Response({
            "visit": visit.pk,
            "visit_number": visit.visit_number,
            "patient": visit.patient_id,
            "patient_name": visit.patient.name,
            "hospital_name": visit.hospital.name,
            "arrival_time": visit.arrival_time,
            "status": visit.status,
            "lines": lines,
        })

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """ER dashboard with counts by status/triage."""
        hospital_id = request.query_params.get("hospital")
        qs = self.get_queryset()
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)

        status_counts = {}
        for choice in EmergencyVisit.STATUS_CHOICES:
            status_counts[choice[0]] = qs.filter(status=choice[0]).count()

        triage_counts = {}
        for choice in EmergencyVisit.TRIAGE_LEVELS:
            triage_counts[choice[0]] = qs.filter(triage_level=choice[0]).count()

        return Response({
            "status_counts": status_counts,
            "triage_counts": triage_counts,
            "total_active": qs.exclude(status__in=["Discharged", "Admitted", "Referred", "Expired", "Left Against Advice"]).count(),
        })


class EmergencyTriageViewSet(HospitalScopedViewSet):
    queryset = EmergencyTriage.objects.select_related("visit__hospital", "visit__patient", "triaged_by")
    serializer_class = EmergencyTriageSerializer
    permission_classes = [IsNurse | IsDoctor | IsHospitalManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(visit__hospital_id=hospital_id)
        return qs


class EmergencyVitalsViewSet(HospitalScopedViewSet):
    queryset = EmergencyVitals.objects.select_related("visit__hospital", "visit__patient", "recorded_by")
    serializer_class = EmergencyVitalsSerializer
    permission_classes = [IsNurse | IsDoctor | IsHospitalManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(visit__hospital_id=hospital_id)
        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)
        return qs


class EmergencyOrderViewSet(HospitalScopedViewSet):
    queryset = EmergencyOrder.objects.select_related("visit__hospital", "visit__patient", "ordered_by")
    serializer_class = EmergencyOrderSerializer
    permission_classes = [IsDoctor | IsNurse | IsHospitalManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(visit__hospital_id=hospital_id)
        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)
        return qs

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()
        order.status = "Completed"
        order.completed_at = timezone.now()
        order.result = request.data.get("result", "")
        order.save()
        return Response(EmergencyOrderSerializer(order).data)


class EmergencyMedicationViewSet(HospitalScopedViewSet):
    queryset = EmergencyMedication.objects.select_related("visit__hospital", "visit__patient", "prescribed_by", "administered_by")
    serializer_class = EmergencyMedicationSerializer
    permission_classes = [IsDoctor | IsNurse | IsHospitalManagerReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            qs = qs.filter(visit__hospital_id=hospital_id)
        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)
        return qs