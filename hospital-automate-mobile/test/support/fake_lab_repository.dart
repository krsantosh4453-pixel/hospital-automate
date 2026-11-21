import 'dart:async';

import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/laboratory/data/lab_repository.dart';
import 'package:hms_mobile/features/laboratory/data/lab_workflow.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

/// In-memory [LabRepository] for widget tests. Records every write; a
/// queued [failNext] error is thrown by the next call. Synthetic data only.
class FakeLabRepository implements LabRepository {
  FakeLabRepository({
    List<LabTest>? tests,
    this.patients = const [],
    this.loadError,
  }) : tests = [...?tests];

  List<LabTest> tests;
  List<PatientSummary> patients;
  Object? loadError;
  Object? failNext;

  /// When set, writes wait for it, so a test can tap twice mid-request.
  Completer<void>? gate;

  final List<String> statusQueries = [];
  final List<LabOrderDraft> created = [];
  final List<({int id, LabStep step, Map<String, Object?> body})> steps = [];
  final List<int> cancelled = [];
  final List<String> lookups = [];

  Future<void> _write() async {
    if (gate != null) await gate!.future;
    final error = failNext;
    if (error != null) {
      failNext = null;
      throw error;
    }
  }

  @override
  Future<List<LabTest>> orders({String? status}) async {
    statusQueries.add(status ?? '');
    if (loadError != null) throw loadError!;
    return [
      for (final test in tests)
        if (status == null || test.status == status) test,
    ];
  }

  @override
  Future<LabTest> order(int id) async {
    if (loadError != null) throw loadError!;
    return tests.firstWhere((t) => t.id == id);
  }

  @override
  Future<LabTest> findBySample(String sampleId) async =>
      tests.firstWhere((t) => t.sample?.sampleId == sampleId);

  @override
  Future<LabTest> createOrder(LabOrderDraft draft) async {
    await _write();
    created.add(draft);
    final test = LabTest(
      id: 900 + created.length,
      name: draft.testName,
      status: LabStatus.ordered,
      priority: draft.priority,
      patientId: draft.patientId,
      patientName: 'Test Patient Lab',
    );
    tests = [test, ...tests];
    return test;
  }

  @override
  Future<LabTest> advance(
    int id,
    LabStep step, [
    Map<String, Object?> body = const {},
  ]) async {
    await _write();
    steps.add((id: id, step: step, body: body));
    final next = switch (step) {
      LabStep.collect => LabStatus.collected,
      LabStep.dispatch => LabStatus.dispatched,
      LabStep.receive => LabStatus.received,
      LabStep.startProcessing => LabStatus.processing,
      LabStep.enterResult => LabStatus.resultEntered,
      LabStep.verify => LabStatus.verified,
      LabStep.release => LabStatus.released,
    };
    return _replace(id, next);
  }

  @override
  Future<LabTest> cancel(int id) async {
    await _write();
    cancelled.add(id);
    return _replace(id, LabStatus.cancelled);
  }

  @override
  Future<List<PatientSummary>> lookupPatients(String query) async {
    lookups.add(query);
    return patients;
  }

  LabTest _replace(int id, String status) {
    final old = tests.firstWhere((t) => t.id == id);
    final updated = LabTest(
      id: old.id,
      name: old.name,
      status: status,
      priority: old.priority,
      patientId: old.patientId,
      patientName: old.patientName,
      testDate: old.testDate,
      sample: status == LabStatus.collected
          ? const LabSample(sampleId: 'LAB-SYN-1', sampleType: 'Blood')
          : old.sample,
      result: old.result,
    );
    tests = [for (final t in tests) t.id == id ? updated : t];
    return updated;
  }
}
