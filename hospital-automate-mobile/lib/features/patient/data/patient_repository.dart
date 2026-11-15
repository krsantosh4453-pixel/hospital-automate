import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../../core/security/session_controller.dart';
import '../../auth/auth_models.dart';
import 'appointment_models.dart';
import 'json_read.dart';
import 'record_models.dart';

/// The signed-in patient's own records. The server decides whose records
/// these are from the session (users/viewsets.py narrows every query to the
/// linked patient), so no patient id is ever sent as authority. The acting
/// hospital goes out as `X-Hospital-ID` from the API client.
abstract interface class PatientRepository {
  /// `auth/patient/me/`, read fresh. The backend offers no patient
  /// self-edit endpoint, so the profile is read-only in the app.
  Future<SessionUser> profile(AccountType accountType);
  Future<List<Appointment>> appointments();
  Future<BookingOptions> bookingOptions({
    int? hospitalId,
    int? doctorId,
    DateTime? date,
  });

  /// Books a slot. Reuse [idempotencyKey] when retrying the same request so
  /// the server returns the first booking instead of making a second one.
  Future<Appointment> book(BookingRequest request, String idempotencyKey);
  Future<List<QueueToken>> queueTokens();
  Future<List<Prescription>> prescriptions();
  Future<List<LabTest>> labTests();
  Future<List<Invoice>> invoices();
  Future<List<PatientNotification>> notifications();
  Future<void> markNotificationRead(int id);
  Future<List<PatientDocument>> documents();
}

/// [PatientRepository] over the Django `/api/v1/` endpoints the web
/// patient portal uses (src/pages/patient/*.jsx).
class ApiPatientRepository implements PatientRepository {
  ApiPatientRepository(this._api);

  final ApiClient _api;

  @override
  Future<SessionUser> profile(AccountType accountType) => _api.get(
    'auth/patient/me/',
    decode: (json) => patientUserFromJson(json, accountType),
  );

  @override
  Future<List<Appointment>> appointments() async => [
    for (final row in await _allRows('appointments/'))
      Appointment.fromJson(row),
  ];

  @override
  Future<BookingOptions> bookingOptions({
    int? hospitalId,
    int? doctorId,
    DateTime? date,
  }) => _api.get(
    'appointments/booking-options/',
    query: {
      'hospital': ?hospitalId,
      'doctor': ?doctorId,
      if (date != null) 'date': isoDay(date),
    },
    decode: BookingOptions.fromJson,
  );

  @override
  Future<Appointment> book(BookingRequest request, String idempotencyKey) =>
      _api.post(
        'appointments/book/',
        body: request.toJson(),
        idempotencyKey: idempotencyKey,
        decode: (json) => Appointment.fromJson(asMap(json)),
      );

  @override
  Future<List<QueueToken>> queueTokens() async => [
    for (final row in await _allRows('encounters/queue-tokens/'))
      QueueToken.fromJson(row),
  ];

  @override
  Future<List<Prescription>> prescriptions() async => [
    for (final row in await _allRows('clinical/prescriptions/'))
      Prescription.fromJson(row),
  ];

  @override
  Future<List<LabTest>> labTests() async => [
    // The root router serves lab tests at laboratory/ itself (laboratory/urls.py).
    for (final row in await _allRows('laboratory/')) LabTest.fromJson(row),
  ];

  @override
  Future<List<Invoice>> invoices() async => [
    for (final row in await _allRows('billing/invoices/'))
      Invoice.fromJson(row),
  ];

  @override
  Future<List<PatientNotification>> notifications() async => [
    for (final row in await _allRows('notifications/notifications/'))
      PatientNotification.fromJson(row),
  ];

  @override
  Future<void> markNotificationRead(int id) => _api.post(
    'notifications/notifications/$id/mark_read/',
    body: const <String, Object?>{},
    decode: (_) {},
  );

  /// `documents/` answers `{documents: [...], count}` (at most 100 rows).
  @override
  Future<List<PatientDocument>> documents() => _api.get(
    'documents/',
    decode: (json) => [
      for (final row in readRows(asMap(json)['documents']))
        PatientDocument.fromJson(row),
    ],
  );

  Future<List<Map<String, Object?>>> _allRows(String path) =>
      getAllRows(_api, path);
}
