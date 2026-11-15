import 'package:flutter/foundation.dart';

import 'json_read.dart';

/// `Appointment.Status` on the server (backend/appointments/models.py).
abstract final class AppointmentStatus {
  static const scheduled = 'Scheduled';
  static const checkedIn = 'Checked In';
  static const inConsultation = 'In Consultation';
  static const completed = 'Completed';
  static const cancelled = 'Cancelled';
  static const noShow = 'No Show';

  /// Still ahead of the patient (web `UPCOMING_STATUSES`).
  static const upcoming = {scheduled, checkedIn, inConsultation};
}

/// One row of `GET appointments/` (AppointmentSerializer).
@immutable
class Appointment {
  const Appointment({
    required this.id,
    required this.status,
    this.patientId,
    this.patientName,
    this.hospitalId,
    this.date,
    this.time,
    this.doctorName,
    this.hospitalName,
    this.reason,
    this.slotSeat,
  });

  factory Appointment.fromJson(Map<String, Object?> json) => Appointment(
    id: readInt(json['id']) ?? 0,
    status: readText(json['status']) ?? '',
    patientId: readInt(json['patient']),
    patientName: readText(json['patient_name']),
    hospitalId: readInt(json['hospital']),
    date: readDate(json['appointment_date']),
    time: readClock(json['appointment_time']),
    doctorName: readText(json['doctor_name']),
    hospitalName: readText(json['hospital_name']),
    reason: readText(json['reason']),
    slotSeat: readInt(json['slot_seat']),
  );

  final int id;
  final String status;
  final int? patientId;

  /// Shown to staff (the doctor's list); a patient sees their own bookings.
  final String? patientName;
  final int? hospitalId;
  final DateTime? date;

  /// `HH:MM`, the booked slot (a confirmed time, not an estimate).
  final String? time;
  final String? doctorName;
  final String? hospitalName;
  final String? reason;

  /// The place this booking holds in the doctor's slot, from the server.
  final int? slotSeat;

  bool get isUpcoming => AppointmentStatus.upcoming.contains(status);

  /// Sort key: date then time; undated rows last.
  String get sortKey => '${date?.toIso8601String() ?? '9999'} ${time ?? ''}';
}

@immutable
class BookingHospital {
  const BookingHospital({required this.id, required this.name});

  final int id;
  final String name;
}

@immutable
class BookingDoctor {
  const BookingDoctor({
    required this.id,
    required this.name,
    this.specialization,
    this.availability,
  });

  final int id;
  final String name;
  final String? specialization;
  final String? availability;
}

/// One 15-minute OPD slot from `booking-options`.
@immutable
class BookingSlot {
  const BookingSlot({
    required this.time,
    required this.available,
    this.capacity,
    this.remaining,
  });

  /// `HH:MM`.
  final String time;
  final bool available;
  final int? capacity;
  final int? remaining;
}

/// `GET appointments/booking-options/?hospital=&doctor=&date=` (patients only).
/// Each level is present only when the query asked for it.
@immutable
class BookingOptions {
  const BookingOptions({
    this.hospitals = const [],
    this.doctors = const [],
    this.slots = const [],
    this.windowDays = defaultWindowDays,
  });

  factory BookingOptions.fromJson(Object? json) {
    final map = asMap(json);
    List<Map<String, Object?>> rows(String key) => readRows(map[key]);
    return BookingOptions(
      hospitals: [
        for (final h in rows('hospitals'))
          if (readInt(h['id']) != null)
            BookingHospital(
              id: readInt(h['id'])!,
              name: readText(h['name']) ?? '',
            ),
      ],
      doctors: [
        for (final d in rows('doctors'))
          if (readInt(d['id']) != null)
            BookingDoctor(
              id: readInt(d['id'])!,
              name: readText(d['name']) ?? '',
              specialization: readText(d['specialization']),
              availability: readText(d['availability']),
            ),
      ],
      slots: [
        for (final s in rows('slots'))
          if (readText(s['time']) != null)
            BookingSlot(
              time: readText(s['time'])!,
              available: s['available'] == true,
              capacity: readInt(s['capacity']),
              remaining: readInt(s['remaining']),
            ),
      ],
      windowDays: readInt(map['window_days']) ?? defaultWindowDays,
    );
  }

  /// The server's `BOOKING_WINDOW_DAYS` when it does not say.
  static const defaultWindowDays = 60;

  final List<BookingHospital> hospitals;
  final List<BookingDoctor> doctors;
  final List<BookingSlot> slots;
  final int windowDays;

  List<BookingSlot> get freeSlots => [
    for (final slot in slots)
      if (slot.available) slot,
  ];
}

/// A booking the patient asks for. The server re-checks every rule.
@immutable
class BookingRequest {
  const BookingRequest({
    required this.doctorId,
    required this.date,
    required this.time,
    this.reason = '',
  });

  /// The server keeps at most this many characters of the reason.
  static const maxReasonLength = 500;

  final int doctorId;
  final DateTime date;

  /// `HH:MM`, one of the offered slots.
  final String time;
  final String reason;

  String get isoDate => isoDay(date);

  Map<String, Object?> toJson() => {
    'doctor': doctorId,
    'appointment_date': isoDate,
    'appointment_time': time,
    if (reason.trim().isNotEmpty) 'reason': reason.trim(),
  };

  /// Same doctor, day and slot: a retry of the same booking (the reason is
  /// free text and does not make it a different booking).
  @override
  bool operator ==(Object other) =>
      other is BookingRequest &&
      other.doctorId == doctorId &&
      other.isoDate == isoDate &&
      other.time == time;

  @override
  int get hashCode => Object.hash(doctorId, isoDate, time);
}
