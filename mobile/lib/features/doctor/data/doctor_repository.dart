import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../patient/data/appointment_models.dart';
import '../../patient/data/json_read.dart';
import '../../patient/data/record_models.dart';
import 'doctor_models.dart';

/// Queue moves a doctor may make (encounters/views.py QueueTokenViewSet).
/// The server checks each transition and answers 400 for an invalid one.
enum QueueAction {
  call('call'),
  startConsultation('start-consultation'),
  complete('complete'),
  skip('skip'),
  noShow('no-show');

  const QueueAction(this.path);

  final String path;
}

/// Clinical work for the signed-in doctor. Every list is already narrowed by
/// the server to the doctor's patients in care at the acting hospital
/// (`X-Hospital-ID`, users/care_scope.py); the app never widens it.
abstract interface class DoctorRepository {
  /// The `doctors/` row of this login at [hospitalId], or null.
  Future<DoctorProfile?> myProfile({
    required int hospitalId,
    required int userId,
  });
  Future<List<Appointment>> appointments({DateTime? date, String? status});
  Future<List<QueueToken>> queue({DateTime? date});
  Future<QueueToken> moveToken(int tokenId, QueueAction action);
  Future<List<PatientSummary>> searchPatients(String query);
  Future<PatientSummary> patient(int id);
  Future<List<TimelineEvent>> timeline(int patientId);
  Future<List<Visit>> visits({int? patientId, String? status});
  Future<Visit> visit(int id);
  Future<Visit> setVisitStatus(int id, String status);
  Future<List<VitalReading>> vitals(int visitId);
  Future<VitalReading> addVitals(
    int visitId,
    Map<VitalField, String> values, {
    String comments,
  });
  Future<List<DiagnosisRecord>> diagnoses(int visitId);
  Future<DiagnosisRecord> addDiagnosis({
    required int visitId,
    required String name,
    String? icd10Code,
    required String type,
    String remarks,
  });
  Future<DiagnosisRecord> signDiagnosis(int id);
  Future<List<ClinicalNoteRecord>> notes(int visitId);
  Future<ClinicalNoteRecord> addNote(
    int visitId,
    Map<NoteSection, String> sections,
  );
  Future<ClinicalNoteRecord> signNote(int id);
  Future<List<Icd10Code>> icd10(String query);
  Future<List<SafetyAlert>> safetyCheck({
    required int hospitalId,
    required int patientId,
    required List<String> medicines,
  });

  /// Reuse [idempotencyKey] when retrying the same draft: the server then
  /// returns the prescription it already wrote instead of a second one.
  Future<Prescription> createPrescription(
    PrescriptionDraft draft, {
    required String idempotencyKey,
  });
  Future<List<Prescription>> prescriptions({int? patientId});
  Future<List<LabTest>> labTests({int? patientId});
  Future<LabTest> orderLabTest({
    required int hospitalId,
    required int patientId,
    required int visitId,
    required int doctorId,
    required String name,
    required String priority,
  });
}

/// [DoctorRepository] over the endpoints the web's doctor pages use
/// (Consultation.jsx, Prescription.jsx, queue.jsx, Patients.jsx).
class ApiDoctorRepository implements DoctorRepository {
  ApiDoctorRepository(this._api);

  final ApiClient _api;

  /// ICD-10 suggestions per query (the web typeahead's limit).
  static const icd10Limit = 15;

  @override
  Future<DoctorProfile?> myProfile({
    required int hospitalId,
    required int userId,
  }) async {
    final rows = await getAllRows(
      _api,
      'doctors/',
      query: {'hospital': hospitalId},
    );
    for (final row in rows) {
      if (readInt(row['user']) == userId) return DoctorProfile.fromJson(row);
    }
    return null;
  }

  @override
  Future<List<Appointment>> appointments({
    DateTime? date,
    String? status,
  }) async => [
    for (final row in await getAllRows(
      _api,
      'appointments/',
      query: {
        if (date != null) 'appointment_date': isoDay(date),
        'status': ?status,
      },
    ))
      Appointment.fromJson(row),
  ];

  @override
  Future<List<QueueToken>> queue({DateTime? date}) async => [
    for (final row in await getAllRows(
      _api,
      'encounters/queue-tokens/',
      query: {if (date != null) 'token_date': isoDay(date)},
    ))
      QueueToken.fromJson(row),
  ];

  @override
  Future<QueueToken> moveToken(int tokenId, QueueAction action) => _api.post(
    'encounters/queue-tokens/$tokenId/${action.path}/',
    body: const <String, Object?>{},
    decode: (json) => QueueToken.fromJson(asMap(json)),
  );

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
  Future<PatientSummary> patient(int id) => _api.get(
    'patients/$id/',
    decode: (json) => PatientSummary.fromJson(asMap(json)),
  );

  @override
  Future<List<TimelineEvent>> timeline(int patientId) => _api.get(
    'patients/$patientId/timeline/',
    decode: (json) => [
      for (final row in readRows(asMap(json)['events']))
        TimelineEvent.fromJson(row),
    ],
  );

  @override
  Future<List<Visit>> visits({int? patientId, String? status}) async => [
    for (final row in await getAllRows(
      _api,
      'encounters/visits/',
      query: {'patient': ?patientId, 'status': ?status},
    ))
      Visit.fromJson(row),
  ];

  @override
  Future<Visit> visit(int id) => _api.get(
    'encounters/visits/$id/',
    decode: (json) => Visit.fromJson(asMap(json)),
  );

  @override
  Future<Visit> setVisitStatus(int id, String status) => _api.patch(
    'encounters/visits/$id/',
    body: {'status': status},
    decode: (json) => Visit.fromJson(asMap(json)),
  );

  /// The server ignores `?visit=` on these lists (clinical/views.py has no
  /// such filter), so rows are also filtered here by their own `visit`.
  Future<List<Map<String, Object?>>> _forVisit(
    String path,
    int visitId,
  ) async => [
    for (final row in await getAllRows(_api, path, query: {'visit': visitId}))
      if (readInt(row['visit']) == visitId) row,
  ];

  @override
  Future<List<VitalReading>> vitals(int visitId) async => [
    for (final row in await _forVisit('clinical/vitals/', visitId))
      VitalReading.fromJson(row),
  ];

  @override
  Future<VitalReading> addVitals(
    int visitId,
    Map<VitalField, String> values, {
    String comments = '',
  }) => _api.post(
    'clinical/vitals/',
    body: {
      'visit': visitId,
      for (final entry in values.entries)
        if (entry.value.trim().isNotEmpty)
          entry.key.key: num.parse(entry.value.trim()),
      if (comments.trim().isNotEmpty) 'comments': comments.trim(),
    },
    decode: (json) => VitalReading.fromJson(asMap(json)),
  );

  @override
  Future<List<DiagnosisRecord>> diagnoses(int visitId) async => [
    for (final row in await _forVisit('clinical/diagnoses/', visitId))
      DiagnosisRecord.fromJson(row),
  ];

  @override
  Future<DiagnosisRecord> addDiagnosis({
    required int visitId,
    required String name,
    String? icd10Code,
    required String type,
    String remarks = '',
  }) => _api.post(
    'clinical/diagnoses/',
    body: {
      'visit': visitId,
      'name': name.trim(),
      if (icd10Code != null && icd10Code.trim().isNotEmpty)
        'icd10_code': icd10Code.trim(),
      'diagnosis_type': type,
      if (remarks.trim().isNotEmpty) 'remarks': remarks.trim(),
    },
    decode: (json) => DiagnosisRecord.fromJson(asMap(json)),
  );

  @override
  Future<DiagnosisRecord> signDiagnosis(int id) => _api.post(
    'clinical/diagnoses/$id/sign/',
    body: const <String, Object?>{},
    decode: (json) => DiagnosisRecord.fromJson(asMap(json)),
  );

  @override
  Future<List<ClinicalNoteRecord>> notes(int visitId) async => [
    for (final row in await _forVisit('clinical/clinical-notes/', visitId))
      ClinicalNoteRecord.fromJson(row),
  ];

  @override
  Future<ClinicalNoteRecord> addNote(
    int visitId,
    Map<NoteSection, String> sections,
  ) => _api.post(
    'clinical/clinical-notes/',
    body: {
      'visit': visitId,
      for (final entry in sections.entries)
        if (entry.value.trim().isNotEmpty) entry.key.key: entry.value.trim(),
    },
    decode: (json) => ClinicalNoteRecord.fromJson(asMap(json)),
  );

  @override
  Future<ClinicalNoteRecord> signNote(int id) => _api.post(
    'clinical/clinical-notes/$id/sign/',
    body: const <String, Object?>{},
    decode: (json) => ClinicalNoteRecord.fromJson(asMap(json)),
  );

  @override
  Future<List<Icd10Code>> icd10(String query) => _api.get(
    'terminology/icd10/',
    query: {'q': query.trim(), 'limit': icd10Limit},
    decode: (json) => [
      for (final row in readRows(json)) Icd10Code.fromJson(row),
    ],
  );

  @override
  Future<List<SafetyAlert>> safetyCheck({
    required int hospitalId,
    required int patientId,
    required List<String> medicines,
  }) => _api.post(
    'clinical/prescriptions/safety-check/',
    body: {
      'hospital': hospitalId,
      'patient': patientId,
      'items': [
        for (final name in medicines) {'name': name.trim()},
      ],
    },
    decode: (json) => [
      for (final row in readRows(asMap(json)['alerts']))
        SafetyAlert.fromJson(row),
    ],
  );

  @override
  Future<Prescription> createPrescription(
    PrescriptionDraft draft, {
    required String idempotencyKey,
  }) => _api.post(
    'clinical/prescriptions/',
    body: draft.toJson(),
    idempotencyKey: idempotencyKey,
    decode: (json) => Prescription.fromJson(asMap(json)),
  );

  @override
  Future<List<Prescription>> prescriptions({int? patientId}) async => [
    for (final row in await getAllRows(
      _api,
      'clinical/prescriptions/',
      query: {'patient': ?patientId},
    ))
      Prescription.fromJson(row),
  ];

  @override
  Future<List<LabTest>> labTests({int? patientId}) async => [
    for (final row in await getAllRows(
      _api,
      'laboratory/',
      query: {'patient': ?patientId},
    ))
      LabTest.fromJson(row),
  ];

  @override
  Future<LabTest> orderLabTest({
    required int hospitalId,
    required int patientId,
    required int visitId,
    required int doctorId,
    required String name,
    required String priority,
  }) => _api.post(
    'laboratory/',
    body: {
      'hospital': hospitalId,
      'patient': patientId,
      'visit': visitId,
      'doctor': doctorId,
      'name': name.trim(),
      'priority': priority,
    },
    decode: (json) => LabTest.fromJson(asMap(json)),
  );
}

/// LabTest.PRIORITY_CHOICES on the server.
const labPriorities = ['Normal', 'Urgent'];
