import 'package:flutter/foundation.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../doctor/data/doctor_models.dart' show PatientSummary;
import '../../patient/data/json_read.dart';
import '../../patient/data/record_models.dart';
import 'lab_workflow.dart';

/// A new laboratory order as the lab desk enters it. The server sets the
/// status (`Ordered`) and the date; the hospital is the acting one.
@immutable
class LabOrderDraft {
  const LabOrderDraft({
    required this.hospitalId,
    required this.patientId,
    required this.testName,
    this.priority = 'Normal',
  });

  final int hospitalId;
  final int patientId;
  final String testName;
  final String priority;

  Map<String, Object?> toJson() => {
    'hospital': hospitalId,
    'patient': patientId,
    'name': testName.trim(),
    'priority': priority,
  };
}

/// What the collect step records (`collect_sample`). An empty [sampleId]
/// lets the server number the sample itself.
@immutable
class SampleCollectionInput {
  const SampleCollectionInput({
    required this.sampleType,
    required this.containerType,
    this.sampleId = '',
    this.notes = '',
  });

  final String sampleType;
  final String containerType;
  final String sampleId;
  final String notes;

  Map<String, Object?> toJson() => {
    'sample_type': sampleType,
    'container_type': containerType,
    if (sampleId.trim().isNotEmpty) 'sample_id': sampleId.trim(),
    if (notes.trim().isNotEmpty) 'collection_notes': notes.trim(),
  };
}

/// Laboratory orders for the acting hospital (`X-Hospital-ID`), over the
/// endpoints the web laboratory page uses. Every step is checked again on
/// the server: role, hospital and the test's current status.
abstract interface class LabRepository {
  Future<List<LabTest>> orders({String? status});
  Future<LabTest> order(int id);

  /// The order whose sample carries [sampleId] (barcode or typed number).
  Future<LabTest> findBySample(String sampleId);
  Future<LabTest> createOrder(LabOrderDraft draft);

  /// Runs [step] on order [id]; [body] carries the step's own fields.
  Future<LabTest> advance(int id, LabStep step, [Map<String, Object?> body]);
  Future<LabTest> cancel(int id);

  /// `patients/lookup/`: at least three characters, at most 20 matches.
  Future<List<PatientSummary>> lookupPatients(String query);
}

class ApiLabRepository implements LabRepository {
  ApiLabRepository(this._api);

  final ApiClient _api;

  // The root router serves lab tests at laboratory/ itself (laboratory/urls.py).
  static const _base = 'laboratory/';

  @override
  Future<List<LabTest>> orders({String? status}) async => [
    for (final row in await getAllRows(_api, _base, query: {'status': ?status}))
      LabTest.fromJson(row),
  ];

  @override
  Future<LabTest> order(int id) =>
      _api.get('$_base$id/', decode: (json) => LabTest.fromJson(asMap(json)));

  @override
  Future<LabTest> findBySample(String sampleId) => _api.get(
    '${_base}by_sample/',
    query: {'sample_id': sampleId.trim()},
    decode: (json) => LabTest.fromJson(asMap(json)),
  );

  @override
  Future<LabTest> createOrder(LabOrderDraft draft) => _api.post(
    _base,
    body: draft.toJson(),
    decode: (json) => LabTest.fromJson(asMap(json)),
  );

  @override
  Future<LabTest> advance(
    int id,
    LabStep step, [
    Map<String, Object?> body = const {},
  ]) => _api.post('$_base$id/${step.action}/', body: body, decode: _labTestOf);

  @override
  Future<LabTest> cancel(int id) => _api.post(
    '$_base$id/cancel/',
    body: const <String, Object?>{},
    decode: _labTestOf,
  );

  @override
  Future<List<PatientSummary>> lookupPatients(String query) => _api.get(
    'patients/lookup/',
    query: {'search': query.trim()},
    decode: (json) => [
      for (final row in readRows(json)) PatientSummary.fromJson(row),
    ],
  );
}

/// Most steps answer `{lab_test: {...}, <record>: {...}}`; start_processing
/// and cancel answer the test itself.
LabTest _labTestOf(Object? json) {
  final map = asMap(json);
  final test = map['lab_test'];
  return LabTest.fromJson(test is Map ? asMap(test) : map);
}
