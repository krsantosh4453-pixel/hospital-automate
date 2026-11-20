import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../../doctor/data/doctor_models.dart';
import '../../patient/data/json_read.dart';
import '../../patient/data/record_models.dart';

/// A new patient registered at the front desk (`POST patients/`).
@immutable
class NewPatientDraft {
  const NewPatientDraft({
    required this.name,
    required this.dateOfBirth,
    required this.gender,
    required this.phone,
  });

  final String name;
  final DateTime dateOfBirth;
  final String gender;
  final String phone;

  Map<String, Object?> toJson(int hospitalId, {bool confirmNew = false}) => {
    'name': name,
    'date_of_birth': isoDay(dateOfBirth),
    'gender': gender,
    'phone': phone,
    'hospital': hospitalId,
    if (confirmNew) 'confirm_new': true,
  };

  @override
  String toString() => 'NewPatientDraft(<redacted>)';
}

/// The front desk's writes. Reads (patient search, appointments, queue) use
/// the same API calls as the doctor's screens (`DoctorRepository`); the
/// server limits each to what the Receptionist role may see.
abstract interface class ReceptionRepository {
  /// Registers a new patient at [hospitalId]; the server issues the UHID.
  /// A 409 means a possible duplicate (flag `portal_account` when the
  /// number has a patient-app account: link that patient instead).
  Future<PatientSummary> registerPatient(
    NewPatientDraft draft,
    int hospitalId, {
    bool confirmNew = false,
  });

  /// Registers an existing patient (found by mobile number and date of
  /// birth) at the acting hospital (BUG-01). 404 when nobody matches.
  Future<PatientSummary> linkPatient(String phone, DateTime dateOfBirth);

  /// Checks the appointment in: the server makes the visit and the queue
  /// token, or returns the token it already made.
  Future<QueueToken> checkIn(int appointmentId);
}

class ApiReceptionRepository implements ReceptionRepository {
  ApiReceptionRepository(this._api);

  final ApiClient _api;

  @override
  Future<PatientSummary> registerPatient(
    NewPatientDraft draft,
    int hospitalId, {
    bool confirmNew = false,
  }) => _api.post(
    'patients/',
    body: draft.toJson(hospitalId, confirmNew: confirmNew),
    decode: (json) => PatientSummary.fromJson(asMap(json)),
  );

  @override
  Future<PatientSummary> linkPatient(String phone, DateTime dateOfBirth) =>
      _api.post(
        'patients/link/',
        body: {'phone': phone, 'date_of_birth': isoDay(dateOfBirth)},
        decode: (json) => PatientSummary.fromJson(asMap(json)),
      );

  @override
  Future<QueueToken> checkIn(int appointmentId) => _api.post(
    'encounters/queue-tokens/issue/',
    body: {'appointment': appointmentId},
    decode: (json) => QueueToken.fromJson(asMap(json)),
  );
}
