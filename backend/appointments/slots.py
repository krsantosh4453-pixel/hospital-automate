"""
Places in a doctor's appointment slot (Decision G, 2026-11-09).

A slot holds ``doctor.slot_capacity`` patients (1 by default). Each active
booking takes a numbered place (``Appointment.slot_seat``); the database
refuses two active bookings on one place, and ``take_place`` hands out only
places 1..capacity while the doctor row is locked, so parallel bookings for
one doctor run one at a time and can never exceed the capacity.

Call ``take_place`` inside ``transaction.atomic()``.
"""

from doctors.models import MAX_SLOT_CAPACITY, Doctor

from .models import Appointment


class SlotFull(Exception):
    """Every place in the slot is taken."""

    def __init__(self, capacity):
        self.capacity = capacity
        super().__init__(f"This slot is full ({capacity} of {capacity} places booked).")


def lock_doctor(doctor_id):
    """Lock the doctor row for this transaction and return it with its current capacity."""
    return Doctor.objects.select_for_update().get(pk=doctor_id)


def places_taken(doctor_id, day, slot, exclude_pk=None):
    """Places held by active bookings in this doctor's slot."""
    taken = Appointment.objects.filter(
        doctor_id=doctor_id, appointment_date=day, appointment_time=slot,
        status__in=Appointment.ACTIVE_STATUSES,
    )
    if exclude_pk is not None:
        taken = taken.exclude(pk=exclude_pk)
    return set(taken.values_list("slot_seat", flat=True))


def take_place(doctor_id, day, slot, exclude_pk=None):
    """Lock the doctor and return the lowest free place in the slot, or raise SlotFull."""
    capacity = lock_doctor(doctor_id).slot_capacity
    taken = places_taken(doctor_id, day, slot, exclude_pk)
    # Count, not "is a number up to capacity free": after a capacity cut the
    # held places can be {1, 3} with capacity 2, and place 2 must stay closed.
    if len(taken) >= capacity:
        raise SlotFull(capacity)
    return min(place for place in range(1, MAX_SLOT_CAPACITY + 1) if place not in taken)


def slot_is_full(doctor, day, slot):
    """Whether active bookings already fill the slot (no lock; for answering a refused insert)."""
    return len(places_taken(doctor.pk, day, slot)) >= doctor.slot_capacity


def remaining_places(doctor, day, slots):
    """``{slot: places left}`` for several slots of one doctor and day (no lock; for display)."""
    counts = {}
    rows = Appointment.objects.filter(doctor=doctor, appointment_date=day, appointment_time__in=slots,
                                      status__in=Appointment.ACTIVE_STATUSES)
    for slot in rows.values_list("appointment_time", flat=True):
        counts[slot] = counts.get(slot, 0) + 1
    return {slot: max(doctor.slot_capacity - counts.get(slot, 0), 0) for slot in slots}
