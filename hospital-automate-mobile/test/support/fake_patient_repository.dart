import 'dart:async';

import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/features/patient/data/patient_repository.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

/// In-memory [PatientRepository] for widget tests. All names and figures
/// are synthetic. Set an `…Error` to make that call fail; [bookGate] holds
/// a booking open so a test can tap again while it is in flight.
class FakePatientRepository implements PatientRepository {
  FakePatientRepository({
    this.appointmentRows = const [],
    this.tokens = const [],
    this.prescriptionRows = const [],
    this.labRows = const [],
    this.invoiceRows = const [],
    this.notificationRows = const [],
    this.documentRows = const [],
    this.options = defaultOptions,
    this.profileUser,
  });

  static const defaultOptions = BookingOptions(
    hospitals: [BookingHospital(id: 7, name: 'Test General Hospital')],
    doctors: [
      BookingDoctor(id: 3, name: 'Dr Test Doctor', specialization: 'General'),
    ],
    slots: [
      BookingSlot(time: '10:00', available: true),
      BookingSlot(time: '10:15', available: false),
    ],
  );

  List<Appointment> appointmentRows;
  List<QueueToken> tokens;
  List<Prescription> prescriptionRows;
  List<LabTest> labRows;
  List<Invoice> invoiceRows;
  List<PatientNotification> notificationRows;
  List<PatientDocument> documentRows;
  BookingOptions options;
  SessionUser? profileUser;

  Object? listError;
  Object? bookError;
  Object? markReadError;
  Completer<void>? bookGate;

  int appointmentCalls = 0;
  int queueCalls = 0;
  final List<({BookingRequest request, String key})> bookings = [];
  final List<int> markedRead = [];

  Future<T> _answer<T>(T value) async {
    if (listError != null) throw listError!;
    return value;
  }

  @override
  Future<SessionUser> profile(AccountType accountType) => _answer(profileUser!);

  @override
  Future<List<Appointment>> appointments() {
    appointmentCalls++;
    return _answer(appointmentRows);
  }

  @override
  Future<BookingOptions> bookingOptions({
    int? hospitalId,
    int? doctorId,
    DateTime? date,
  }) => _answer(
    BookingOptions(
      hospitals: options.hospitals,
      doctors: hospitalId == null ? const [] : options.doctors,
      slots: doctorId == null ? const [] : options.slots,
      windowDays: options.windowDays,
    ),
  );

  @override
  Future<Appointment> book(
    BookingRequest request,
    String idempotencyKey,
  ) async {
    bookings.add((request: request, key: idempotencyKey));
    await bookGate?.future;
    if (bookError != null) throw bookError!;
    return Appointment(
      id: 501,
      status: AppointmentStatus.scheduled,
      date: request.date,
      time: request.time,
      doctorName: 'Dr Test Doctor',
      hospitalName: 'Test General Hospital',
    );
  }

  @override
  Future<List<QueueToken>> queueTokens() {
    queueCalls++;
    return _answer(tokens);
  }

  @override
  Future<List<Prescription>> prescriptions() => _answer(prescriptionRows);

  @override
  Future<List<LabTest>> labTests() => _answer(labRows);

  @override
  Future<List<Invoice>> invoices() => _answer(invoiceRows);

  @override
  Future<List<PatientNotification>> notifications() =>
      _answer(notificationRows);

  @override
  Future<void> markNotificationRead(int id) async {
    if (markReadError != null) throw markReadError!;
    markedRead.add(id);
  }

  @override
  Future<List<PatientDocument>> documents() => _answer(documentRows);
}

const networkError = ApiException(kind: ApiErrorKind.network);
