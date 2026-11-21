import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../doctor/data/doctor_models.dart';
import '../../doctor/data/doctor_repository.dart';
import '../../patient/data/json_read.dart';
import 'nursing_models.dart';

/// Ward work for the signed-in nurse. Every list is already narrowed by the
/// server to the patients of the nurse's duty at the acting hospital
/// (`X-Hospital-ID`, users/care_scope.py); the app never widens it. Records
/// are written under the nurse's own profile by the server.
abstract interface class NursingRepository {
  /// The `nurses/nurses/` row of this login at [hospitalId], or null.
  Future<NurseProfile?> myProfile({
    required int hospitalId,
    required int userId,
  });

  /// Ward and patient duties of [nurseId] on [day].
  Future<List<DutyAssignment>> wardDuties({
    required int nurseId,
    required DateTime day,
  });
  Future<List<DutyAssignment>> patientDuties({
    required int nurseId,
    required DateTime day,
  });

  /// Admissions the server lets this nurse see (still in the ward or not).
  Future<List<Admission>> admissions({int? patientId});
  Future<PatientSummary> patient(int id);

  /// Open OPD visits of a patient (vitals can be recorded on them too).
  Future<List<Visit>> openVisits(int patientId);

  Future<List<NursingAssessment>> assessments(int patientId);

  /// Vitals on an admission: a "Focused" assessment with a `vitals` record.
  Future<NursingAssessment> addWardVitals({
    required int hospitalId,
    required int patientId,
    required int admissionId,
    required Map<String, String> vitals,
  });

  /// Vitals on an OPD visit (`clinical/vitals/`, recorded_by set by the server).
  Future<List<VitalReading>> visitVitals(int visitId);
  Future<VitalReading> addVisitVitals(
    int visitId,
    Map<VitalField, String> values,
  );

  Future<List<NursingNote>> notes({int? patientId});
  Future<NursingNote> addNote({
    required int hospitalId,
    required int patientId,
    int? admissionId,
    required String type,
    required String text,
  });

  Future<List<CareTask>> careTasks({int? patientId, int? nurseId});
  Future<CareTask> startTask(int id);
  Future<CareTask> completeTask(int id, {String notes});

  /// Doses still due up to an hour ahead (overdue ones included).
  Future<List<Dose>> dueDoses(int hospitalId);
  Future<List<MedicationOrder>> medicationOrders(int patientId);

  /// Records [action] for a due dose. The server refuses one already
  /// recorded, or one whose order is no longer in force.
  Future<Dose> recordDose(int doseId, DoseAction action, {String reason});

  /// H-10: an as-needed (PRN) dose given now under [orderId]. The server
  /// refuses (409) a dose inside the order's minimum interval or over its
  /// 24-hour maximum, flagged `prn_min_interval` / `prn_max_per_24h`.
  Future<Dose> givePrnDose(int orderId, {String notes});
}

/// [NursingRepository] over the endpoints the web's Nurses page uses
/// (src/pages/Nurses.jsx, services/api.js `nurses`). Patient, visit and
/// visit-vitals reads reuse the shared clinical calls.
class ApiNursingRepository implements NursingRepository {
  ApiNursingRepository(this._api, this._clinical);

  final ApiClient _api;
  final DoctorRepository _clinical;

  @override
  Future<NurseProfile?> myProfile({
    required int hospitalId,
    required int userId,
  }) async {
    final rows = await getAllRows(
      _api,
      'nurses/nurses/',
      query: {'hospital': hospitalId},
    );
    for (final row in rows) {
      if (readInt(row['user']) == userId) return NurseProfile.fromJson(row);
    }
    return null;
  }

  @override
  Future<List<DutyAssignment>> wardDuties({
    required int nurseId,
    required DateTime day,
  }) async => [
    for (final row in await getAllRows(
      _api,
      'nurses/ward-assignments/',
      query: {'nurse': nurseId, 'shift_date': isoDay(day)},
    ))
      if (row['is_active'] != false) DutyAssignment.ward(row),
  ];

  @override
  Future<List<DutyAssignment>> patientDuties({
    required int nurseId,
    required DateTime day,
  }) async => [
    for (final row in await getAllRows(
      _api,
      'nurses/patient-assignments/',
      query: {'nurse': nurseId, 'shift_date': isoDay(day), 'is_active': 'true'},
    ))
      DutyAssignment.patient(row),
  ];

  @override
  Future<List<Admission>> admissions({int? patientId}) async => [
    for (final row in await getAllRows(
      _api,
      'ipd/admissions/',
      query: {'patient': ?patientId},
    ))
      Admission.fromJson(row),
  ];

  @override
  Future<PatientSummary> patient(int id) => _clinical.patient(id);

  @override
  Future<List<Visit>> openVisits(int patientId) async => [
    for (final visit in await _clinical.visits(patientId: patientId))
      if (visit.isOpen) visit,
  ];

  @override
  Future<List<NursingAssessment>> assessments(int patientId) async => [
    for (final row in await getAllRows(
      _api,
      'nurses/assessments/',
      query: {'patient': patientId},
    ))
      NursingAssessment.fromJson(row),
  ];

  @override
  Future<NursingAssessment> addWardVitals({
    required int hospitalId,
    required int patientId,
    required int admissionId,
    required Map<String, String> vitals,
  }) => _api.post(
    'nurses/assessments/',
    body: {
      'hospital': hospitalId,
      'patient': patientId,
      'admission': admissionId,
      'assessment_type': NursingAssessment.vitalsType,
      'vitals': vitals,
    },
    decode: (json) => NursingAssessment.fromJson(asMap(json)),
  );

  @override
  Future<List<VitalReading>> visitVitals(int visitId) =>
      _clinical.vitals(visitId);

  @override
  Future<VitalReading> addVisitVitals(
    int visitId,
    Map<VitalField, String> values,
  ) => _clinical.addVitals(visitId, values);

  @override
  Future<List<NursingNote>> notes({int? patientId}) async => [
    for (final row in await getAllRows(
      _api,
      'nurses/notes/',
      query: {'patient': ?patientId},
      maxPages: patientId == null ? 1 : maxListPages,
    ))
      NursingNote.fromJson(row),
  ];

  @override
  Future<NursingNote> addNote({
    required int hospitalId,
    required int patientId,
    int? admissionId,
    required String type,
    required String text,
  }) => _api.post(
    'nurses/notes/',
    body: {
      'hospital': hospitalId,
      'patient': patientId,
      'admission': ?admissionId,
      'note_type': type,
      'note': text.trim(),
    },
    decode: (json) => NursingNote.fromJson(asMap(json)),
  );

  @override
  Future<List<CareTask>> careTasks({int? patientId, int? nurseId}) async => [
    for (final row in await getAllRows(
      _api,
      'nurses/care-tasks/',
      query: {'patient': ?patientId, 'assigned_nurse': ?nurseId},
    ))
      CareTask.fromJson(row),
  ];

  @override
  Future<CareTask> startTask(int id) => _api.post(
    'nurses/care-tasks/$id/start/',
    body: const <String, Object?>{},
    decode: (json) => CareTask.fromJson(asMap(json)),
  );

  @override
  Future<CareTask> completeTask(int id, {String notes = ''}) => _api.post(
    'nurses/care-tasks/$id/complete/',
    body: {if (notes.trim().isNotEmpty) 'notes': notes.trim()},
    decode: (json) => CareTask.fromJson(asMap(json)),
  );

  @override
  Future<List<Dose>> dueDoses(int hospitalId) => _api.get(
    'nurses/mar/due_medications/',
    query: {'hospital': hospitalId},
    decode: (json) => [for (final row in readRows(json)) Dose.fromJson(row)],
  );

  @override
  Future<List<MedicationOrder>> medicationOrders(int patientId) async => [
    for (final row in await getAllRows(
      _api,
      'nurses/mar/',
      query: {'patient': patientId},
    ))
      MedicationOrder.fromJson(row),
  ];

  @override
  Future<Dose> recordDose(
    int doseId,
    DoseAction action, {
    String reason = '',
  }) => _api.post(
    'nurses/mar-administrations/$doseId/${action.path}/',
    body: {if (reason.trim().isNotEmpty) 'reason': reason.trim()},
    decode: (json) => Dose.fromJson(asMap(json)),
  );

  @override
  Future<Dose> givePrnDose(int orderId, {String notes = ''}) => _api.post(
    'nurses/mar/$orderId/prn/',
    body: {'notes': notes.trim()},
    decode: (json) => Dose.fromJson(asMap(json)),
  );
}
