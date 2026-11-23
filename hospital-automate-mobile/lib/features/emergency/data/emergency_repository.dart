import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../doctor/data/doctor_models.dart' show PatientSummary;
import '../../patient/data/json_read.dart';
import 'emergency_models.dart';

const _visits = 'emergency/emergency-visits/';

/// The emergency department of the acting hospital (`X-Hospital-ID`).
///
/// Every list is scoped by the server to that hospital and to what the
/// role may see (users/care_scope.py). Writes need a Doctor, Nurse or Admin
/// role there; the server answers 403 for anyone else and 400 for a move
/// the visit's status does not allow.
abstract interface class EmergencyRepository {
  Future<ErDashboard> dashboard();
  Future<List<EmergencyVisit>> visits({String? status});
  Future<EmergencyVisit> visit(int id);

  /// Registers an ER visit for an existing patient. The server's answer is
  /// the stored values only (no visit id), so callers refresh the list.
  Future<void> register({
    required int patientId,
    required String triageLevel,
    String remarks,
  });
  Future<EmergencyVisit> startTriage(int id);
  Future<EmergencyVisit> completeTriage(int id, TriageDraft draft);

  /// [doctorId] (a `doctors/` id at this hospital) becomes the attending
  /// doctor; null keeps whoever is attending now.
  Future<EmergencyVisit> startConsultation(int id, {int? doctorId});
  Future<ErNote> addNote(int id, String note);
  Future<EmergencyVisit> discharge(
    int id, {
    required String diagnosis,
    required String followUp,
  });
  Future<EmergencyVisit> refer(
    int id, {
    required String referredTo,
    required String diagnosis,
    required String followUp,
  });
  Future<List<PatientSummary>> searchPatients(String query);
  Future<List<DoctorOption>> doctors();

  /// Records vitals; [recordedBy] is the nurse profile id at this hospital.
  Future<ErVitals> addVitals(
    int id,
    Map<ErVitalField, String> values, {
    int? recordedBy,
  });

  /// Admits the patient to [bedId] (a free bed of this hospital). The
  /// server locks the bed and refuses one that is no longer Available.
  Future<ErAdmission> admitToIpd(int id, {required int bedId});
}

/// [EmergencyRepository] over the endpoints the web's Emergency page uses.
class ApiEmergencyRepository implements EmergencyRepository {
  ApiEmergencyRepository(this._api);

  final ApiClient _api;

  @override
  Future<ErDashboard> dashboard() => _api.get(
    '${_visits}dashboard/',
    decode: (json) => ErDashboard.fromJson(asMap(json)),
  );

  @override
  Future<List<EmergencyVisit>> visits({String? status}) async => [
    for (final row in await getAllRows(
      _api,
      _visits,
      query: {'status': ?status},
    ))
      EmergencyVisit.fromJson(row),
  ];

  @override
  Future<EmergencyVisit> visit(int id) =>
      _api.get('$_visits$id/', decode: _decodeVisit);

  @override
  Future<void> register({
    required int patientId,
    required String triageLevel,
    String remarks = '',
  }) => _api.post(
    _visits,
    body: {
      'patient': patientId,
      'triage_level': triageLevel,
      if (remarks.trim().isNotEmpty) 'remarks': remarks.trim(),
    },
    decode: (_) {},
  );

  @override
  Future<EmergencyVisit> startTriage(int id) => _move(id, 'start_triage');

  @override
  Future<EmergencyVisit> completeTriage(int id, TriageDraft draft) =>
      _move(id, 'complete_triage', draft.toJson());

  @override
  Future<EmergencyVisit> startConsultation(int id, {int? doctorId}) =>
      _move(id, 'start_consultation', {'doctor_id': ?doctorId});

  @override
  Future<ErNote> addNote(int id, String note) => _api.post(
    '$_visits$id/add_note/',
    body: {'note': note.trim()},
    decode: (json) => ErNote.fromJson(asMap(json)),
  );

  @override
  Future<EmergencyVisit> discharge(
    int id, {
    required String diagnosis,
    required String followUp,
  }) => _move(id, 'discharge', {
    'discharge_diagnosis': diagnosis.trim(),
    'follow_up_instructions': followUp.trim(),
  });

  @override
  Future<EmergencyVisit> refer(
    int id, {
    required String referredTo,
    required String diagnosis,
    required String followUp,
  }) => _move(id, 'refer', {
    'referred_to': referredTo.trim(),
    'discharge_diagnosis': diagnosis.trim(),
    'follow_up_instructions': followUp.trim(),
  });

  @override
  Future<List<PatientSummary>> searchPatients(String query) async => [
    for (final row in await getAllRows(
      _api,
      'patients/',
      query: {'search': query.trim()},
      maxPages: 1,
    ))
      PatientSummary.fromJson(row),
  ];

  @override
  Future<List<DoctorOption>> doctors() async => [
    for (final row in await getAllRows(_api, 'doctors/'))
      DoctorOption.fromJson(row),
  ];

  @override
  Future<ErVitals> addVitals(
    int id,
    Map<ErVitalField, String> values, {
    int? recordedBy,
  }) => _api.post(
    '$_visits$id/add_vitals/',
    body: vitalsBody(values, recordedBy: recordedBy),
    decode: (json) => ErVitals.fromJson(asMap(json)),
  );

  @override
  Future<ErAdmission> admitToIpd(int id, {required int bedId}) => _api.post(
    '$_visits$id/admit_to_ipd/',
    body: {'bed_id': bedId},
    decode: (json) => ErAdmission.fromJson(asMap(json)),
  );

  Future<EmergencyVisit> _move(
    int id,
    String action, [
    Map<String, Object?> body = const {},
  ]) => _api.post('$_visits$id/$action/', body: body, decode: _decodeVisit);

  static EmergencyVisit _decodeVisit(Object? json) =>
      EmergencyVisit.fromJson(asMap(json));
}
