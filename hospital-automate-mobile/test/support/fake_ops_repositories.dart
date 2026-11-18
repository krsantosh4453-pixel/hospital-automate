import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/emergency/data/emergency_models.dart';
import 'package:hms_mobile/features/emergency/data/emergency_repository.dart';
import 'package:hms_mobile/features/hospital/data/hospital_models.dart';
import 'package:hms_mobile/features/hospital/data/hospital_repository.dart';
import 'package:hms_mobile/features/ipd/data/ipd_models.dart';
import 'package:hms_mobile/features/ipd/data/ipd_repository.dart';

// Synthetic data only: no real patients, staff or hospitals.

/// In-memory ER: records every write; [failWith] makes the next write throw.
class FakeEmergencyRepository implements EmergencyRepository {
  FakeEmergencyRepository({
    this.visitList = const [],
    this.board = const ErDashboard(
      statusCounts: {},
      triageCounts: {},
      totalActive: 0,
    ),
    this.patients = const [],
    this.doctorList = const [],
  });

  List<EmergencyVisit> visitList;
  ErDashboard board;
  List<PatientSummary> patients;
  List<DoctorOption> doctorList;
  Object? loadError;
  Object? failWith;
  final List<String> calls = [];
  final List<Map<String, Object?>> registrations = [];

  Future<void> _write(String call) async {
    calls.add(call);
    final error = failWith;
    if (error != null) {
      failWith = null;
      throw error;
    }
  }

  EmergencyVisit _find(int id) => visitList.firstWhere((v) => v.id == id);

  EmergencyVisit _withStatus(int id, String status) {
    final v = _find(id);
    final updated = EmergencyVisit(
      id: v.id,
      status: status,
      triageLevel: v.triageLevel,
      visitNumber: v.visitNumber,
      patientId: v.patientId,
      patientName: v.patientName,
      arrivalTime: v.arrivalTime,
      triage: v.triage,
      notes: v.notes,
    );
    visitList = [for (final x in visitList) x.id == id ? updated : x];
    return updated;
  }

  @override
  Future<ErDashboard> dashboard() async {
    if (loadError != null) throw loadError!;
    return board;
  }

  @override
  Future<List<EmergencyVisit>> visits({String? status}) async {
    if (loadError != null) throw loadError!;
    return visitList;
  }

  @override
  Future<EmergencyVisit> visit(int id) async {
    if (loadError != null) throw loadError!;
    return _find(id);
  }

  @override
  Future<void> register({
    required int patientId,
    required String triageLevel,
    String remarks = '',
  }) async {
    await _write('register');
    registrations.add({
      'patient': patientId,
      'triage_level': triageLevel,
      'remarks': remarks,
    });
  }

  @override
  Future<EmergencyVisit> startTriage(int id) async {
    await _write('start_triage:$id');
    return _withStatus(id, ErStatus.triage);
  }

  @override
  Future<EmergencyVisit> completeTriage(int id, TriageDraft draft) async {
    await _write('complete_triage:$id:${draft.triageLevel}');
    return _withStatus(id, ErStatus.waiting);
  }

  @override
  Future<EmergencyVisit> startConsultation(int id, {int? doctorId}) async {
    await _write('start_consultation:$id:$doctorId');
    return _withStatus(id, ErStatus.underConsultation);
  }

  @override
  Future<ErNote> addNote(int id, String note) async {
    await _write('add_note:$id');
    return ErNote(id: 1, note: note);
  }

  @override
  Future<EmergencyVisit> discharge(
    int id, {
    required String diagnosis,
    required String followUp,
  }) async {
    await _write('discharge:$id');
    return _withStatus(id, ErStatus.discharged);
  }

  @override
  Future<EmergencyVisit> refer(
    int id, {
    required String referredTo,
    required String diagnosis,
    required String followUp,
  }) async {
    await _write('refer:$id:$referredTo');
    return _withStatus(id, ErStatus.referred);
  }

  @override
  Future<List<PatientSummary>> searchPatients(String query) async {
    calls.add('search:$query');
    return patients;
  }

  @override
  Future<List<DoctorOption>> doctors() async => doctorList;

  /// Bodies sent to `add_vitals`, as the real repository builds them.
  final List<Map<String, Object?>> vitalsSent = [];

  @override
  Future<ErVitals> addVitals(
    int id,
    Map<ErVitalField, String> values, {
    int? recordedBy,
  }) async {
    await _write('add_vitals:$id');
    vitalsSent.add(vitalsBody(values, recordedBy: recordedBy));
    return const ErVitals(id: 1);
  }

  /// Admission id [admitToIpd] answers with.
  int admissionIdToCreate = 77;

  @override
  Future<ErAdmission> admitToIpd(int id, {required int bedId}) async {
    await _write('admit_to_ipd:$id:$bedId');
    _withStatus(id, ErStatus.admitted);
    return ErAdmission(admissionId: admissionIdToCreate);
  }
}

class FakeIpdRepository implements IpdRepository {
  FakeIpdRepository({
    this.admissionList = const [],
    this.overviewData = const IpdOverview(),
    this.free = const [],
    this.board = const BedBoard(beds: [], complete: true),
    DischargeReadiness? readinessData,
    this.summary,
  }) : readinessData = readinessData ?? const DischargeReadiness(ready: false);

  List<IpdAdmission> admissionList;
  IpdOverview overviewData;
  List<AvailableBed> free;
  BedBoard board;
  DischargeReadiness readinessData;
  DischargeSummaryRecord? summary;
  Object? summaryError;
  Object? failWith;
  final List<String> calls = [];
  final List<int> overviewHospitals = [];

  Future<void> _write(String call) async {
    calls.add(call);
    final error = failWith;
    if (error != null) {
      failWith = null;
      throw error;
    }
  }

  IpdAdmission _find(int id) => admissionList.firstWhere((a) => a.id == id);

  IpdAdmission _withStatus(int id, String status) {
    final a = _find(id);
    final updated = IpdAdmission(
      id: a.id,
      status: status,
      patientName: a.patientName,
      admissionDate: a.admissionDate,
      currentBed: status == AdmissionStatus.discharged ? null : a.currentBed,
      bedHistory: a.bedHistory,
    );
    admissionList = [for (final x in admissionList) x.id == id ? updated : x];
    return updated;
  }

  @override
  Future<IpdOverview> overview(int hospitalId) async {
    overviewHospitals.add(hospitalId);
    return overviewData;
  }

  @override
  Future<List<IpdAdmission>> admissions({
    String? status,
    int? patientId,
  }) async => [
    for (final a in admissionList)
      if (patientId == null || a.patientId == patientId) a,
  ];

  @override
  Future<IpdAdmission> admission(int id) async => _find(id);

  @override
  Future<DischargeReadiness> readiness(int admissionId) async => readinessData;

  @override
  Future<List<AvailableBed>> availableBeds(int hospitalId) async {
    calls.add('available_beds:$hospitalId');
    return free;
  }

  @override
  Future<BedBoard> bedBoard() async => board;

  @override
  Future<void> allocateBed(int admissionId, int bedId) =>
      _write('allocate_bed:$admissionId:$bedId');

  @override
  Future<void> transferBed(int admissionId, int bedId) =>
      _write('transfer:$admissionId:$bedId');

  @override
  Future<IpdAdmission> initiateDischarge(int admissionId) async {
    await _write('initiate_discharge:$admissionId');
    return _withStatus(admissionId, AdmissionStatus.dischargeInitiated);
  }

  @override
  Future<IpdAdmission> completeDischarge(int admissionId) async {
    await _write('complete_discharge:$admissionId');
    return _withStatus(admissionId, AdmissionStatus.discharged);
  }

  @override
  Future<DischargeSummaryRecord?> dischargeSummary(int admissionId) async {
    if (summaryError != null) throw summaryError!;
    return summary;
  }
}

class FakeHospitalRepository implements HospitalRepository {
  FakeHospitalRepository({
    this.info = const {},
    this.departmentList = const [],
    this.wardList = const [],
    this.staffList = const [],
  });

  /// Hospital records by id; a missing id throws like a 404 would.
  Map<int, HospitalInfo> info;
  List<Department> departmentList;
  List<Ward> wardList;
  List<StaffMember> staffList;
  Object? staffError;
  final List<int> requestedHospitals = [];
  final List<String> staffSearches = [];

  @override
  Future<HospitalInfo> hospital(int id) async {
    requestedHospitals.add(id);
    final record = info[id];
    if (record == null) throw StateError('no hospital $id');
    return record;
  }

  @override
  Future<List<Department>> departments() async => departmentList;

  @override
  Future<List<Ward>> wards() async => wardList;

  @override
  Future<List<StaffMember>> staff({String search = ''}) async {
    staffSearches.add(search);
    if (staffError != null) throw staffError!;
    return staffList;
  }
}
