import 'dart:async';

import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

/// In-memory [DoctorRepository] for widget tests. Synthetic data only. Set an
/// `…Error` to make that call fail; [gate] holds writes open so a test can tap
/// again while one is in flight.
class FakeDoctorRepository implements DoctorRepository {
  FakeDoctorRepository({
    this.profile = testDoctor,
    this.appointmentRows = const [],
    this.tokens = const [],
    this.patients = const [],
    this.visitRows = const [],
    this.vitalRows = const [],
    this.diagnosisRows = const [],
    this.noteRows = const [],
    this.prescriptionRows = const [],
    this.labRows = const [],
    this.alerts = const [],
  });

  static const testDoctor = DoctorProfile(
    id: 3,
    name: 'Dr Test Doctor',
    specialization: 'General Medicine',
    registrationNumber: 'TEST-REG-1',
    registrationVerified: true,
  );

  DoctorProfile? profile;
  List<Appointment> appointmentRows;
  List<QueueToken> tokens;
  List<PatientSummary> patients;
  List<Visit> visitRows;
  List<VitalReading> vitalRows;
  List<DiagnosisRecord> diagnosisRows;
  List<ClinicalNoteRecord> noteRows;
  List<Prescription> prescriptionRows;
  List<LabTest> labRows;
  List<SafetyAlert> alerts;

  Object? readError;
  Object? writeError;
  Completer<void>? gate;

  int queueCalls = 0;
  final List<String> searches = [];
  final List<({int token, QueueAction action})> moves = [];
  final List<Map<VitalField, String>> savedVitals = [];
  final List<String> savedDiagnoses = [];
  final List<int> signed = [];
  final List<Map<NoteSection, String>> savedNotes = [];
  final List<PrescriptionDraft> savedPrescriptions = [];

  /// Every Idempotency-Key sent with a prescription, in order (retries included).
  final List<String> prescriptionKeys = [];
  final Map<String, Prescription> _prescriptionsByKey = {};
  final List<String> orderedTests = [];
  final List<String> visitStatuses = [];

  Future<T> _read<T>(T value) async {
    if (readError != null) throw readError!;
    return value;
  }

  Future<void> _write() async {
    await gate?.future;
    if (writeError != null) throw writeError!;
  }

  @override
  Future<DoctorProfile?> myProfile({
    required int hospitalId,
    required int userId,
  }) => _read(profile);

  @override
  Future<List<Appointment>> appointments({DateTime? date, String? status}) =>
      _read([
        for (final a in appointmentRows)
          if ((date == null || a.date == date) &&
              (status == null || a.status == status))
            a,
      ]);

  @override
  Future<List<QueueToken>> queue({DateTime? date}) {
    queueCalls++;
    return _read(tokens);
  }

  @override
  Future<QueueToken> moveToken(int tokenId, QueueAction action) async {
    moves.add((token: tokenId, action: action));
    await _write();
    final token = tokens.firstWhere((t) => t.id == tokenId);
    final status = switch (action) {
      QueueAction.call => 'Called',
      QueueAction.startConsultation => 'In Consultation',
      QueueAction.complete => 'Completed',
      QueueAction.skip => 'Skipped',
      QueueAction.noShow => 'No Show',
    };
    final moved = QueueToken(
      id: token.id,
      tokenNumber: token.tokenNumber,
      status: status,
      patientName: token.patientName,
      visitId: token.visitId,
    );
    tokens = [for (final t in tokens) t.id == tokenId ? moved : t];
    return moved;
  }

  @override
  Future<List<PatientSummary>> searchPatients(String query) {
    searches.add(query);
    return _read([
      for (final p in patients)
        if (p.name.toLowerCase().contains(query.toLowerCase())) p,
    ]);
  }

  @override
  Future<PatientSummary> patient(int id) async {
    if (readError != null) throw readError!;
    return patients.firstWhere((p) => p.id == id);
  }

  @override
  Future<List<TimelineEvent>> timeline(int patientId) => _read(const []);

  @override
  Future<List<Visit>> visits({int? patientId, String? status}) => _read([
    for (final v in visitRows)
      if (patientId == null || v.patientId == patientId) v,
  ]);

  @override
  Future<Visit> visit(int id) => _read(visitRows.firstWhere((v) => v.id == id));

  @override
  Future<Visit> setVisitStatus(int id, String status) async {
    visitStatuses.add(status);
    await _write();
    final v = visitRows.firstWhere((v) => v.id == id);
    final updated = Visit(
      id: v.id,
      status: status,
      patientId: v.patientId,
      patientName: v.patientName,
      doctorId: v.doctorId,
      hospitalId: v.hospitalId,
    );
    visitRows = [for (final row in visitRows) row.id == id ? updated : row];
    return updated;
  }

  @override
  Future<List<VitalReading>> vitals(int visitId) => _read([
    for (final v in vitalRows)
      if (v.visitId == visitId) v,
  ]);

  @override
  Future<VitalReading> addVitals(
    int visitId,
    Map<VitalField, String> values, {
    String comments = '',
  }) async {
    savedVitals.add(values);
    await _write();
    final reading = VitalReading(
      id: 900 + savedVitals.length,
      visitId: visitId,
      values: values,
    );
    vitalRows = [...vitalRows, reading];
    return reading;
  }

  @override
  Future<List<DiagnosisRecord>> diagnoses(int visitId) => _read([
    for (final d in diagnosisRows)
      if (d.visitId == visitId) d,
  ]);

  @override
  Future<DiagnosisRecord> addDiagnosis({
    required int visitId,
    required String name,
    String? icd10Code,
    required String type,
    String remarks = '',
  }) async {
    savedDiagnoses.add(name);
    await _write();
    final record = DiagnosisRecord(
      id: 800 + savedDiagnoses.length,
      name: name,
      visitId: visitId,
    );
    diagnosisRows = [...diagnosisRows, record];
    return record;
  }

  @override
  Future<DiagnosisRecord> signDiagnosis(int id) async {
    signed.add(id);
    await _write();
    return diagnosisRows.firstWhere((d) => d.id == id);
  }

  @override
  Future<List<ClinicalNoteRecord>> notes(int visitId) => _read([
    for (final n in noteRows)
      if (n.visitId == visitId) n,
  ]);

  @override
  Future<ClinicalNoteRecord> addNote(
    int visitId,
    Map<NoteSection, String> sections,
  ) async {
    savedNotes.add(sections);
    await _write();
    final note = ClinicalNoteRecord(
      id: 700 + savedNotes.length,
      visitId: visitId,
      sections: sections,
    );
    noteRows = [...noteRows, note];
    return note;
  }

  @override
  Future<ClinicalNoteRecord> signNote(int id) async {
    signed.add(id);
    await _write();
    return noteRows.firstWhere((n) => n.id == id);
  }

  @override
  Future<List<Icd10Code>> icd10(String query) => _read(const [
    Icd10Code(code: 'I10', description: 'Essential (primary) hypertension'),
  ]);

  @override
  Future<List<SafetyAlert>> safetyCheck({
    required int hospitalId,
    required int patientId,
    required List<String> medicines,
  }) => _read(alerts);

  @override
  Future<Prescription> createPrescription(
    PrescriptionDraft draft, {
    required String idempotencyKey,
  }) async {
    prescriptionKeys.add(idempotencyKey);
    await _write();
    // Like the server: a key that already wrote a prescription returns it.
    final earlier = _prescriptionsByKey[idempotencyKey];
    if (earlier != null) return earlier;
    savedPrescriptions.add(draft);
    final rx = Prescription(
      id: 600 + savedPrescriptions.length,
      status: PrescriptionDraft.newStatus,
      visitId: draft.visitId,
      patientId: draft.patientId,
      doctorName: profile?.name,
      items: [
        for (final line in draft.lines)
          PrescriptionItem(
            name: line.name,
            dosage: line.dosage,
            frequency: line.frequency,
          ),
      ],
    );
    prescriptionRows = [...prescriptionRows, rx];
    _prescriptionsByKey[idempotencyKey] = rx;
    return rx;
  }

  @override
  Future<List<Prescription>> prescriptions({int? patientId}) => _read([
    for (final rx in prescriptionRows)
      if (patientId == null || rx.patientId == patientId) rx,
  ]);

  @override
  Future<List<LabTest>> labTests({int? patientId}) => _read([
    for (final test in labRows)
      if (patientId == null || test.patientId == patientId) test,
  ]);

  @override
  Future<LabTest> orderLabTest({
    required int hospitalId,
    required int patientId,
    required int visitId,
    required int doctorId,
    required String name,
    required String priority,
  }) async {
    orderedTests.add(name);
    await _write();
    final test = LabTest(
      id: 500 + orderedTests.length,
      name: name,
      status: 'Ordered',
      patientId: patientId,
      visitId: visitId,
    );
    labRows = [...labRows, test];
    return test;
  }
}
