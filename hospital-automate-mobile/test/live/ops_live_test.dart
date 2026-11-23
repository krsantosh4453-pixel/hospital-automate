// Opt-in end-to-end check of the Emergency, IPD and Hospital modules against
// a REAL backend, using the app's own API client and repositories (no fakes).
//
// Only for a throwaway test server with synthetic data: seed_demo, then a
// scratch fixture with a free bed, a bedless admission of demo.patient and a
// second hospital the demo logins do not belong to, whose ids are written to
// HMS_LIVE_OPS_SEED ({hospital, patient, admission, free_bed, free_bed_2,
// other_hospital, other_admission, other_er_visit}). Run:
//   HMS_LIVE_ORIGIN=http://127.0.0.1:8137 HMS_LIVE_PASSWORD=… \
//   HMS_LIVE_OPS_SEED=…/ops.json flutter test test/live/ops_live_test.dart
// It registers, triages and discharges one ER visit and allocates a bed and
// starts a discharge on the seeded admission. Never point it at real data.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/emergency/data/emergency_models.dart';
import 'package:hms_mobile/features/emergency/data/emergency_repository.dart';
import 'package:hms_mobile/features/hospital/data/hospital_repository.dart';
import 'package:hms_mobile/features/ipd/data/ipd_models.dart';
import 'package:hms_mobile/features/ipd/data/ipd_repository.dart';
import 'package:hms_mobile/features/nursing/data/nursing_repository.dart';

final _env = Platform.environment;
final _origin = _env['HMS_LIVE_ORIGIN'];
final _password = _env['HMS_LIVE_PASSWORD'];
final _seedPath = _env['HMS_LIVE_OPS_SEED'];

Matcher _apiError(ApiErrorKind kind) =>
    throwsA(isA<ApiException>().having((e) => e.kind, 'kind', kind));

/// One signed-in login with its own client, acting in [hospitalId].
class _Login {
  _Login(String origin) {
    api = ApiClient(
      config: ApiConfig(origin: origin),
      accessToken: () async => token,
      hospitalId: () => hospitalId,
      log: (_) {},
    );
  }

  late final ApiClient api;
  String? token;
  int? hospitalId;
  int? userId;
  String? role;

  Future<_Login> signIn(String username, String password) async {
    final auth = ApiAuthRepository(api);
    token = (await auth.staffPasswordLogin(
      username,
      password,
      DeviceInfo(
        deviceId: 'live-test-$username',
        platform: 'other',
        appVersion: 'live-test',
      ),
    )).access;
    final contexts = await auth.meContexts();
    expect(contexts.accountType, AccountType.staff);
    final context = contexts.hospitals.single;
    hospitalId = context.id;
    role = context.role;
    userId = (await auth.staffMe()).id;
    return this;
  }

  EmergencyRepository get er => ApiEmergencyRepository(api);
  IpdRepository get ipd => ApiIpdRepository(api);
  HospitalRepository get hospital => ApiHospitalRepository(api);
}

void main() {
  final skip = _origin == null || _password == null || _seedPath == null
      ? 'Set HMS_LIVE_ORIGIN, HMS_LIVE_PASSWORD and HMS_LIVE_OPS_SEED to run'
      : null;

  late Map<String, Object?> seed;
  late _Login nurse;
  late _Login doctor;
  late _Login manager;
  late _Login desk;
  late int visitId;

  int seedId(String key) => seed[key]! as int;

  setUpAll(() async {
    if (skip != null) return;
    seed = Map<String, Object?>.from(
      jsonDecode(File(_seedPath!).readAsStringSync()) as Map,
    );
    final origin = _origin!;
    final password = _password!;
    nurse = await _Login(origin).signIn('demo.nurse', password);
    doctor = await _Login(origin).signIn('demo.doctor1', password);
    manager = await _Login(origin).signIn('demo.manager', password);
    desk = await _Login(origin).signIn('demo.desk.main', password);
  });

  group('emergency', () {
    test('1. roles: nurse and doctor at the seeded hospital', () {
      expect(nurse.role, 'Nurse');
      expect(doctor.role, 'Doctor');
      expect(nurse.hospitalId, seedId('hospital'));
    }, skip: skip);

    test('2. a receptionist and a manager may not register', () async {
      for (final login in [desk, manager]) {
        await expectLater(
          login.er.register(
            patientId: seedId('patient'),
            triageLevel: 'Urgent',
          ),
          _apiError(ApiErrorKind.forbidden),
        );
      }
    }, skip: skip);

    test('3. a nurse registers; the visit appears once stored', () async {
      final before = await nurse.er.visits();
      await nurse.er.register(
        patientId: seedId('patient'),
        triageLevel: 'Urgent',
        remarks: 'E2E mobile ER visit',
      );
      final after = await nurse.er.visits();
      final added = after
          .where((v) => before.every((b) => b.id != v.id))
          .toList();
      expect(added, hasLength(1));
      expect(added.single.status, ErStatus.registered);
      expect(added.single.triageLevel, 'Urgent');
      visitId = added.single.id;
      final board = await nurse.er.dashboard();
      expect(board.totalActive, greaterThanOrEqualTo(1));
    }, skip: skip);

    test('4. an invalid move is refused; triage then waiting', () async {
      await expectLater(
        nurse.er.completeTriage(
          visitId,
          const TriageDraft(chiefComplaint: 'E2E pain', triageLevel: 'Urgent'),
        ),
        _apiError(ApiErrorKind.validation),
      );
      expect((await nurse.er.startTriage(visitId)).status, ErStatus.triage);
      final waiting = await nurse.er.completeTriage(
        visitId,
        const TriageDraft(
          chiefComplaint: 'E2E pain',
          triageLevel: 'Emergency',
          painScore: 5,
          glasgowComaScale: 15,
        ),
      );
      expect(waiting.status, ErStatus.waiting);
      expect(waiting.triageLevel, 'Emergency');
      final note = await nurse.er.addNote(visitId, 'E2E mobile note');
      expect(note.note, 'E2E mobile note');
    }, skip: skip);

    test('5. the doctor takes the visit and discharges it once', () async {
      final profile = await ApiDoctorRepository(doctor.api)
          .myProfile(hospitalId: doctor.hospitalId!, userId: doctor.userId!);
      final started = await doctor.er.startConsultation(
        visitId,
        doctorId: profile!.id,
      );
      expect(started.status, ErStatus.underConsultation);
      expect(started.attendingDoctorId, profile.id);
      final done = await doctor.er.discharge(
        visitId,
        diagnosis: 'E2E diagnosis',
        followUp: 'E2E follow-up',
      );
      expect(done.status, ErStatus.discharged);
      await expectLater(
        doctor.er.discharge(visitId, diagnosis: '', followUp: ''),
        _apiError(ApiErrorKind.validation),
      );
    }, skip: skip);

    test("6. another hospital's ER visit is not reachable", () async {
      await expectLater(
        nurse.er.visit(seedId('other_er_visit')),
        _apiError(ApiErrorKind.notFound),
      );
      final ids = (await nurse.er.visits()).map((v) => v.id);
      expect(ids, isNot(contains(seedId('other_er_visit'))));
    }, skip: skip);

    test('6b. vitals under the nurse, then admission to a free bed', () async {
      final before = await nurse.er.visits();
      await nurse.er.register(
        patientId: seedId('patient'),
        triageLevel: 'Urgent',
      );
      final visit = (await nurse.er.visits()).firstWhere(
        (v) => before.every((b) => b.id != v.id),
      );
      final profile = await ApiNursingRepository(
        nurse.api,
        ApiDoctorRepository(nurse.api),
      ).myProfile(hospitalId: nurse.hospitalId!, userId: nurse.userId!);
      final vitals = await nurse.er.addVitals(visit.id, {
        ErVitalField.systolic: '118',
        ErVitalField.temperature: '37.4',
      }, recordedBy: profile!.id);
      expect(vitals.systolic, 118);
      expect(vitals.temperature, '37.40');
      expect(vitals.recordedByName, isNotNull);

      // Admission is refused until the doctor has the patient.
      await expectLater(
        doctor.er.admitToIpd(visit.id, bedId: seedId('free_bed_2')),
        _apiError(ApiErrorKind.validation),
      );
      await nurse.er.startTriage(visit.id);
      await nurse.er.completeTriage(
        visit.id,
        const TriageDraft(chiefComplaint: 'E2E admit', triageLevel: 'Urgent'),
      );
      await doctor.er.startConsultation(visit.id);
      final occupied = (await manager.ipd.bedBoard()).beds.firstWhere(
        (b) => b.status == BedStatus.occupied,
      );
      await expectLater(
        doctor.er.admitToIpd(visit.id, bedId: occupied.id),
        _apiError(ApiErrorKind.validation),
      );
      final admission = await doctor.er.admitToIpd(
        visit.id,
        bedId: seedId('free_bed_2'),
      );
      expect((await doctor.er.visit(visit.id)).status, ErStatus.admitted);
      final stay = await doctor.ipd.admission(admission.admissionId);
      expect(stay.currentBed?.bedId, seedId('free_bed_2'));
      final free = await nurse.ipd.availableBeds(nurse.hospitalId!);
      expect(free.map((b) => b.id), isNot(contains(seedId('free_bed_2'))));
    }, skip: skip);
  });

  group('ipd', () {
    test('7. overview and lists come from the server', () async {
      final overview = await nurse.ipd.overview(nurse.hospitalId!);
      expect(overview.admitted, greaterThanOrEqualTo(1));
      expect(overview.availableBeds, greaterThanOrEqualTo(1));
      final admissions = await nurse.ipd.admissions();
      expect(admissions.map((a) => a.id), contains(seedId('admission')));
      final free = await nurse.ipd.availableBeds(nurse.hospitalId!);
      expect(free.map((b) => b.id), contains(seedId('free_bed')));
      final board = await manager.ipd.bedBoard();
      expect(board.complete, isTrue);
      expect(board.count(BedStatus.occupied), greaterThanOrEqualTo(2));
    }, skip: skip);

    test('8. a bed is allocated once; occupied beds are refused', () async {
      final admissionId = seedId('admission');
      final occupied = (await manager.ipd.bedBoard()).beds.firstWhere(
        (b) => b.status == BedStatus.occupied,
      );
      await expectLater(
        nurse.ipd.allocateBed(admissionId, occupied.id),
        _apiError(ApiErrorKind.validation),
      );
      await nurse.ipd.allocateBed(admissionId, seedId('free_bed'));
      final admission = await nurse.ipd.admission(admissionId);
      expect(admission.currentBed?.bedId, seedId('free_bed'));
      await expectLater(
        nurse.ipd.allocateBed(admissionId, seedId('free_bed')),
        _apiError(ApiErrorKind.validation),
      );
      await expectLater(
        nurse.ipd.transferBed(admissionId, occupied.id),
        _apiError(ApiErrorKind.validation),
      );
      final after = await nurse.ipd.admission(admissionId);
      expect(after.currentBed?.bedId, seedId('free_bed'));
    }, skip: skip);

    test('9. a manager may read but not discharge', () async {
      await expectLater(
        manager.ipd.initiateDischarge(seedId('admission')),
        _apiError(ApiErrorKind.forbidden),
      );
    }, skip: skip);

    test('10. discharge starts but cannot complete while not ready', () async {
      final admissionId = seedId('admission');
      final started = await nurse.ipd.initiateDischarge(admissionId);
      expect(started.status, AdmissionStatus.dischargeInitiated);
      final readiness = await nurse.ipd.readiness(admissionId);
      expect(readiness.ready, isFalse);
      expect(readiness.checklist, isNotEmpty);
      await expectLater(
        nurse.ipd.completeDischarge(admissionId),
        _apiError(ApiErrorKind.validation),
      );
      final after = await nurse.ipd.admission(admissionId);
      expect(after.status, AdmissionStatus.dischargeInitiated);
    }, skip: skip);

    test('11. a nurse cannot read discharge summaries; a doctor can', () async {
      await expectLater(
        nurse.ipd.dischargeSummary(seedId('admission')),
        _apiError(ApiErrorKind.forbidden),
      );
      expect(await doctor.ipd.dischargeSummary(seedId('admission')), isNull);
    }, skip: skip);

    test("12. another hospital's admission is not reachable", () async {
      await expectLater(
        nurse.ipd.admission(seedId('other_admission')),
        _apiError(ApiErrorKind.notFound),
      );
      // Naming a hospital the login does not belong to is refused.
      nurse.hospitalId = seedId('other_hospital');
      try {
        await expectLater(
          nurse.ipd.admissions(),
          _apiError(ApiErrorKind.forbidden),
        );
      } finally {
        nurse.hospitalId = seedId('hospital');
      }
    }, skip: skip);
  });

  group('hospital', () {
    test('13. a manager reads the hospital, departments and staff', () async {
      final info = await manager.hospital.hospital(manager.hospitalId!);
      expect(info.id, seedId('hospital'));
      expect(info.name, isNotEmpty);
      final departments = await manager.hospital.departments();
      expect(
        departments.map((d) => d.name),
        containsAll(['Cardiology', 'Orthopaedics']),
      );
      final staff = await manager.hospital.staff();
      expect(staff.map((s) => s.role), contains('Nurse'));
      final wards = await manager.hospital.wards();
      expect(wards.map((w) => w.name), contains('Ward A'));
    }, skip: skip);

    test('14. a nurse may not list staff or open another hospital', () async {
      await expectLater(
        nurse.hospital.staff(),
        _apiError(ApiErrorKind.forbidden),
      );
      await expectLater(
        manager.hospital.hospital(seedId('other_hospital')),
        _apiError(ApiErrorKind.notFound),
      );
    }, skip: skip);
  });
}
