from datetime import date, datetime, time, timedelta

from django.db import IntegrityError, transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import Appointment, clashing_booking
from .serializers import AppointmentSerializer, refuse_double_booking
from audit.services import record_audit
from config.hospital_time import hospital_now
from doctors.models import Doctor
from hospital.models import Hospital
from users.viewsets import HospitalScopedViewSet
from users.permissions import (
    IsAdmin,
    IsHospitalManager,
    IsReceptionist,
    IsDoctor,
    IsLinkedPatient,
    IsNurseReadOnly,
    IsPatientReadOnly,
    get_linked_patient,
    parse_hospital_id,
)

# Online booking by patients: 15-minute OPD slots between these times.
SLOT_START = time(9, 0)
SLOT_END = time(17, 0)
SLOT_MINUTES = 15
BOOKING_WINDOW_DAYS = 60
MAX_UPCOMING_BOOKINGS = 3
IDEMPOTENCY_KEY_LENGTH = 80
# Doctors with these statuses take no online bookings.
UNBOOKABLE_DOCTOR_STATUSES = {"On Leave", "Inactive", "Unavailable"}


def _hospital_now():
    # Settings use UTC; slots and "today" follow the hospital's clock.
    return hospital_now()


def _day_slots():
    slots, current = [], datetime.combine(date.today(), SLOT_START)
    end = datetime.combine(date.today(), SLOT_END)
    while current < end:
        slots.append(current.time())
        current += timedelta(minutes=SLOT_MINUTES)
    return slots


def _patient_hospital_ids(patient):
    """Hospitals where the patient is registered (directly or by membership)."""
    ids = set(patient.hospital_memberships.filter(is_active=True).values_list("hospital_id", flat=True))
    if patient.hospital_id:
        ids.add(patient.hospital_id)
    return ids


def _parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ValidationError({"appointment_date": "Use a date like 2026-11-05."})


def _parse_slot(value):
    try:
        slot = time.fromisoformat(str(value)[:5])
    except (TypeError, ValueError):
        raise ValidationError({"appointment_time": "Use a time like 10:30."})
    if slot not in _day_slots():
        raise ValidationError({"appointment_time": "Choose one of the offered slots."})
    return slot


def _booking_with_key(patient, key):
    """The patient's earlier booking made with this Idempotency-Key, if any."""
    if not key:
        return None
    return Appointment.objects.filter(patient=patient, idempotency_key=key).first()


def _taken_slots(doctor, day):
    return set(
        Appointment.objects.filter(doctor=doctor, appointment_date=day)
        .exclude(status="Cancelled")
        .values_list("appointment_time", flat=True)
    )


class AppointmentViewSet(HospitalScopedViewSet):
    queryset = Appointment.objects.select_related("patient", "doctor", "hospital")
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdmin | IsHospitalManager | IsReceptionist | IsDoctor | IsPatientReadOnly | IsNurseReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()

        hospital_id = self.request.query_params.get("hospital")
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)

        # Additional filters
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        appointment_date = self.request.query_params.get("appointment_date")
        if appointment_date:
            queryset = queryset.filter(appointment_date=appointment_date)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    # ------------------------------------------------------------------
    # Online booking by a signed-in patient (for themselves only)
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="booking-options", permission_classes=[IsLinkedPatient])
    def booking_options(self, request):
        """
        GET ?hospital=&doctor=&date= — the patient's hospitals, the doctors
        there, and the free slots of one doctor on one day. No other
        patient's data is returned.
        """
        patient = get_linked_patient(request.user)
        allowed = _patient_hospital_ids(patient)
        payload = {
            "hospitals": list(
                Hospital.objects.filter(id__in=allowed, is_active=True).order_by("name").values("id", "name")
            ),
            "window_days": BOOKING_WINDOW_DAYS,
        }
        hospital_id = parse_hospital_id(request.query_params.get("hospital"))
        if hospital_id is None:
            return Response(payload)
        if hospital_id not in allowed:
            raise PermissionDenied("You are not registered at this hospital.")
        doctors = Doctor.objects.filter(hospital_id=hospital_id).exclude(status__in=UNBOOKABLE_DOCTOR_STATUSES)
        payload["doctors"] = list(doctors.order_by("name").values("id", "name", "specialization", "availability"))

        doctor_id, day = request.query_params.get("doctor"), request.query_params.get("date")
        if doctor_id and day:
            doctor = doctors.filter(pk=doctor_id).first()
            if doctor is None:
                raise ValidationError({"doctor": "Choose a doctor at this hospital."})
            day = _parse_date(day)
            now = _hospital_now()
            taken = _taken_slots(doctor, day)
            payload["slots"] = [
                {
                    "time": slot.strftime("%H:%M"),
                    "available": slot not in taken and (day > now.date() or (day == now.date() and slot > now.time())),
                }
                for slot in _day_slots()
            ]
        return Response(payload)

    @action(detail=False, methods=["post"], url_path="book", permission_classes=[IsLinkedPatient])
    def book(self, request):
        """
        POST {doctor, appointment_date, appointment_time, reason?} — book a slot for yourself.

        An optional ``Idempotency-Key`` header makes retries safe: repeating a
        request with the same key returns the first booking (200) instead of a
        second one; the same key for a different slot is refused (409).
        """
        patient = get_linked_patient(request.user)
        doctor = (
            Doctor.objects.filter(pk=request.data.get("doctor"), hospital_id__in=_patient_hospital_ids(patient))
            .exclude(status__in=UNBOOKABLE_DOCTOR_STATUSES)
            .first()
        )
        if doctor is None:
            raise ValidationError({"doctor": "Choose a doctor at a hospital where you are registered."})

        day = _parse_date(request.data.get("appointment_date"))
        slot = _parse_slot(request.data.get("appointment_time"))
        key = request.headers.get("Idempotency-Key", "").strip()
        if len(key) > IDEMPOTENCY_KEY_LENGTH:
            # Refused, not truncated: two long keys sharing a prefix would collide.
            raise ValidationError({"idempotency_key": f"Use at most {IDEMPOTENCY_KEY_LENGTH} characters."})
        earlier = _booking_with_key(patient, key)
        if earlier is not None:
            # Checked before the time and limit rules so a late retry still gets its booking back.
            return self._replay_booking(earlier, doctor, day, slot)

        now = _hospital_now()
        if day < now.date() or (day == now.date() and slot <= now.time()):
            raise ValidationError({"appointment_time": "This time has already passed."})
        if day > now.date() + timedelta(days=BOOKING_WINDOW_DAYS):
            raise ValidationError({"appointment_date": f"Book at most {BOOKING_WINDOW_DAYS} days ahead."})

        upcoming = Appointment.objects.filter(patient=patient, appointment_date__gte=now.date()).exclude(
            status__in=["Cancelled", "Completed"]
        )
        if upcoming.count() >= MAX_UPCOMING_BOOKINGS:
            raise ValidationError(f"You already have {MAX_UPCOMING_BOOKINGS} upcoming appointments.")

        try:
            with transaction.atomic():
                # Lock the doctor row, not the day's appointments: on a day with no
                # bookings yet there are no rows to lock, and two patients could
                # both take the same slot.
                Doctor.objects.select_for_update().filter(pk=doctor.pk).first()
                earlier = _booking_with_key(patient, key)
                if earlier is not None:
                    return self._replay_booking(earlier, doctor, day, slot)
                if slot in _taken_slots(doctor, day):
                    return Response(
                        {"error": "This slot was just booked. Please choose another time."},
                        status=status.HTTP_409_CONFLICT,
                    )
                appointment = Appointment.objects.create(
                    hospital_id=doctor.hospital_id,
                    patient=patient,
                    doctor=doctor,
                    appointment_date=day,
                    appointment_time=slot,
                    status="Scheduled",
                    reason=str(request.data.get("reason") or "")[:500],
                    contact=(patient.phone or "")[:15],
                    idempotency_key=key,
                )
        except IntegrityError:
            # Either the same key was used at the same moment for another doctor
            # (each doctor has its own lock), or a staff booking, which does not
            # take the doctor lock, put this patient in the slot first.
            earlier = _booking_with_key(patient, key)
            if earlier is not None:
                return self._replay_booking(earlier, doctor, day, slot)
            if clashing_booking(patient, doctor, day, slot) is not None:
                return Response(
                    {"error": "This slot was just booked. Please choose another time."},
                    status=status.HTTP_409_CONFLICT,
                )
            raise
        record_audit(request, "appointments.appointment.self_booked", appointment, hospital=doctor.hospital_id)
        return Response(self.get_serializer(appointment).data, status=status.HTTP_201_CREATED)

    def _replay_booking(self, earlier, doctor, day, slot):
        """Answer a retried booking request with the booking its key already made."""
        if (earlier.doctor_id, earlier.appointment_date, earlier.appointment_time) != (doctor.pk, day, slot):
            return Response(
                {"error": "This Idempotency-Key was already used for a different booking."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(earlier).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an appointment."""
        appointment = self.get_object()
        appointment.status = "Cancelled"
        appointment.save()
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        """Reschedule an appointment."""
        appointment = self.get_object()
        appointment_date = request.data.get("appointment_date")
        appointment_time = request.data.get("appointment_time")
        
        if appointment_date:
            appointment.appointment_date = appointment_date
        if appointment_time:
            appointment.appointment_time = appointment_time
        if appointment.status in Appointment.ACTIVE_STATUSES:
            refuse_double_booking(appointment.patient, appointment.doctor, appointment.appointment_date,
                                  appointment.appointment_time, exclude_pk=appointment.pk)
        appointment.save()
        return Response(self.get_serializer(appointment).data)