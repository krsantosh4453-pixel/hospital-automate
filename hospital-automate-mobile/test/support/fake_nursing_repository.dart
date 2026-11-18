import 'dart:async';

import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/nursing/data/nursing_models.dart';
import 'package:hms_mobile/features/nursing/data/nursing_repository.dart';

/// In-memory [NursingRepository] for widget tests. Synthetic data only. Set
/// [readError] / [writeError] to make calls fail; [gate] holds writes open
/// so a test can tap again while one is in flight.
class FakeNursingRepository implements NursingRepository {
  FakeNursingRepository({
    this.profile = testNurse,
    this.patients = const [],
    this.admissionRows = const [],
    this.visitRows = const [],
    this.wardDutyRows = const [],
    this.patientDutyRows = const [],
    this.assessmentRows = const [],
    this.noteRows = const [],
    this.taskRows = const [],
    this.dueRows = const [],
    this.orderRows = const [],
  });

  static const testNurse = NurseProfile(
    id: 5,
    name: 'Test Nurse',
    department: 'General Ward',
    qualification: 'BSc Nursing',
  );

  NurseProfile? profile;
  List<PatientSummary> patients;
  List<Admission> admissionRows;
  List<Visit> visitRows;
  List<DutyAssignment> wardDutyRows;
  List<DutyAssignment> patientDutyRows;
  List<NursingAssessment> assessmentRows;
  List<NursingNote> noteRows;
  List<CareTask> taskRows;
  List<Dose> dueRows;
  List<MedicationOrder> orderRows;

  Object? readError;
  Object? writeError;
  Completer<void>? gate;

  final List<Map<String, String>> savedWardVitals = [];
  final List<Map<VitalField, String>> savedVisitVitals = [];
  final List<({String type, String text, int? admissionId})> savedNotes = [];
  final List<({int dose, DoseAction action, String reason})> recordedDoses =
      [];
  final List<int> completedTasks = [];

  Future<T> _read<T>(T value) async {
    if (readError != null) throw readError!;
    return value;
  }

  Future<void> _write() async {
    await gate?.future;
    if (writeError != null) throw writeError!;
  }

  @override
  Future<NurseProfile?> myProfile({
    required int hospitalId,
    required int userId,
  }) => _read(profile);

  @override
  Future<List<DutyAssignment>> wardDuties({
    required int nurseId,
    required DateTime day,
  }) => _read(wardDutyRows);

  @override
  Future<List<DutyAssignment>> patientDuties({
    required int nurseId,
    required DateTime day,
  }) => _read(patientDutyRows);

  @override
  Future<List<Admission>> admissions({int? patientId}) => _read([
    for (final a in admissionRows)
      if (patientId == null || a.patientId == patientId) a,
  ]);

  @override
  Future<PatientSummary> patient(int id) async {
    if (readError != null) throw readError!;
    return patients.firstWhere((p) => p.id == id);
  }

  @override
  Future<List<Visit>> openVisits(int patientId) => _read([
    for (final v in visitRows)
      if (v.patientId == patientId && v.isOpen) v,
  ]);

  @override
  Future<List<NursingAssessment>> assessments(int patientId) => _read([
    for (final a in assessmentRows)
      if (a.patientId == patientId) a,
  ]);

  @override
  Future<NursingAssessment> addWardVitals({
    required int hospitalId,
    required int patientId,
    required int admissionId,
    required Map<String, String> vitals,
  }) async {
    savedWardVitals.add(vitals);
    await _write();
    final saved = NursingAssessment(
      id: 900 + savedWardVitals.length,
      type: NursingAssessment.vitalsType,
      patientId: patientId,
      admissionId: admissionId,
      vitals: vitals,
      nurseName: profile?.name,
      assessedAt: DateTime(2026, 11, 15, 10),
    );
    assessmentRows = [saved, ...assessmentRows];
    return saved;
  }

  @override
  Future<List<VitalReading>> visitVitals(int visitId) => _read(const []);

  @override
  Future<VitalReading> addVisitVitals(
    int visitId,
    Map<VitalField, String> values,
  ) async {
    savedVisitVitals.add(values);
    await _write();
    return VitalReading(id: 1, visitId: visitId, values: values);
  }

  @override
  Future<List<NursingNote>> notes({int? patientId}) => _read([
    for (final n in noteRows)
      if (patientId == null || n.patientId == patientId) n,
  ]);

  @override
  Future<NursingNote> addNote({
    required int hospitalId,
    required int patientId,
    int? admissionId,
    required String type,
    required String text,
  }) async {
    savedNotes.add((type: type, text: text, admissionId: admissionId));
    await _write();
    final note = NursingNote(
      id: 700 + savedNotes.length,
      type: type,
      text: text.trim(),
      patientId: patientId,
      admissionId: admissionId,
      nurseName: profile?.name,
      createdAt: DateTime(2026, 11, 15, 10),
    );
    noteRows = [note, ...noteRows];
    return note;
  }

  @override
  Future<List<CareTask>> careTasks({int? patientId, int? nurseId}) => _read([
    for (final task in taskRows)
      if (patientId == null || task.patientId == patientId) task,
  ]);

  @override
  Future<CareTask> startTask(int id) async {
    await _write();
    return taskRows.firstWhere((t) => t.id == id);
  }

  @override
  Future<CareTask> completeTask(int id, {String notes = ''}) async {
    completedTasks.add(id);
    await _write();
    taskRows = [for (final t in taskRows) if (t.id != id) t];
    return CareTask(
      id: id,
      type: 'Other',
      description: '',
      status: 'Completed',
      priority: 'Routine',
    );
  }

  @override
  Future<List<Dose>> dueDoses(int hospitalId) => _read(dueRows);

  @override
  Future<List<MedicationOrder>> medicationOrders(int patientId) =>
      _read(orderRows);

  @override
  Future<Dose> recordDose(
    int doseId,
    DoseAction action, {
    String reason = '',
  }) async {
    recordedDoses.add((dose: doseId, action: action, reason: reason));
    await _write();
    final status = switch (action) {
      DoseAction.administer => 'Administered',
      DoseAction.hold => 'Held',
      DoseAction.refuse => 'Refused',
      DoseAction.missed => 'Missed',
    };
    Dose? recorded;
    orderRows = [
      for (final order in orderRows)
        MedicationOrder(
          id: order.id,
          medicineName: order.medicineName,
          isActive: order.isActive,
          dose: order.dose,
          route: order.route,
          frequency: order.frequency,
          doses: [
            for (final d in order.doses)
              if (d.id == doseId)
                recorded = Dose(
                  id: d.id,
                  status: status,
                  medicineName: d.medicineName,
                  dose: d.dose,
                  route: d.route,
                  scheduledAt: d.scheduledAt,
                  recordedAt: DateTime(2026, 11, 15, 9, 5),
                  givenByName: profile?.name,
                )
              else
                d,
          ],
        ),
    ];
    return recorded!;
  }
}
