"""
OpenAPI descriptions of the patient booking endpoints (``booking-options`` and
``book``), which are hand-written actions without their own serializer. Kept
here so views.py stays readable; the mobile client is generated from these.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from .serializers import AppointmentSerializer

_BOOKING_SLOT_FIELDS = {
    "time": serializers.CharField(help_text="Slot start, HH:MM in the hospital's time zone."),
    "available": serializers.BooleanField(help_text="A place is free and the time has not passed."),
    "capacity": serializers.IntegerField(help_text="Patients this doctor takes per slot (1 unless raised)."),
    "remaining": serializers.IntegerField(help_text="Places still free in the slot."),
}

BOOKING_OPTIONS_SCHEMA = extend_schema(
    summary="Hospitals, doctors and free slots the signed-in patient can book",
    parameters=[
        OpenApiParameter("hospital", OpenApiTypes.INT, description="Return this hospital's bookable doctors."),
        OpenApiParameter("doctor", OpenApiTypes.INT, description="With `date`, return this doctor's slots."),
        OpenApiParameter("date", OpenApiTypes.DATE, description="With `doctor`, the day to list slots for."),
    ],
    responses={
        200: inline_serializer("BookingOptions", {
            "hospitals": inline_serializer("BookingHospital", {
                "id": serializers.IntegerField(), "name": serializers.CharField()}, many=True),
            "window_days": serializers.IntegerField(help_text="How many days ahead a patient may book."),
            "doctors": inline_serializer("BookingDoctor", {
                "id": serializers.IntegerField(), "name": serializers.CharField(),
                "specialization": serializers.CharField(), "availability": serializers.CharField(),
            }, many=True, required=False),
            "slots": inline_serializer("BookingSlot", _BOOKING_SLOT_FIELDS, many=True, required=False),
        }),
        403: OpenApiResponse(description="The patient is not registered at that hospital."),
    },
)

BOOK_SCHEMA = extend_schema(
    summary="Book a slot for the signed-in patient",
    # COMPONENT_SPLIT_REQUEST adds "Request": the component is named BookingRequest.
    request=inline_serializer("Booking", {
        "doctor": serializers.IntegerField(),
        "appointment_date": serializers.DateField(),
        "appointment_time": serializers.CharField(help_text="HH:MM; one of the offered 15-minute slots."),
        "reason": serializers.CharField(required=False, max_length=500),
    }),
    parameters=[
        OpenApiParameter(
            "Idempotency-Key", OpenApiTypes.STR, OpenApiParameter.HEADER, required=False,
            description="Up to 80 characters, unique per patient. Repeating a request with the same key returns "
                        "the first booking (200) instead of booking again.",
        ),
    ],
    responses={
        201: AppointmentSerializer,
        200: OpenApiResponse(AppointmentSerializer, description="Replay: the booking this Idempotency-Key made."),
        400: OpenApiResponse(description="Invalid doctor, date or time, past time, outside the booking window, "
                                         "too many upcoming bookings, or an Idempotency-Key over 80 characters."),
        409: OpenApiResponse(description="Every place in the slot is taken, or the Idempotency-Key was used "
                                         "for a different booking."),
    },
)
