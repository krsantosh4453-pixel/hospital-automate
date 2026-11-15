// Opt-in end-to-end check of the doctor module against a REAL backend, using
// the app's own API client and repositories (no fakes).
//
// Only for a throwaway test server with synthetic data: seed_demo, then a
// fresh Waiting visit + queue token of demo.patient with demo.doctor1 whose
// ids are written to HMS_LIVE_DOCTOR_SEED ({visit, token, patient,
// other_patient, hospital}). Run:
//   HMS_LIVE_ORIGIN=http://127.0.0.1:8137 HMS_LIVE_PASSWORD=… \
//   HMS_LIVE_DOCTOR_SEED=…/ids.json flutter test test/live/doctor_live_test.dart
// It writes vitals, a note, a diagnosis, a prescription and a lab order on that
// synthetic visit. Never point it at a server with real patients.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/patient/data/patient_repository.dart';

final _env = Platform.environment;
final _origin = _env['HMS_LIVE_ORIGIN'];
final _password = _env['HMS_LIVE_PASSWORD'];
final _seedPath = _env['HMS_LIVE_DOCTOR_SEED'];

const _device = DeviceInfo(
  deviceId: 'live-test-doctor',
  platform: 'other',
  appVersion: 'live-test',
);
const _medicine = 'E2E Mobile Medicine 250';

Matcher _apiError(ApiErrorKind kind) =>
    throwsA(isA<ApiException>().having((e) => e.kind, 'kind', kind));

void main() {
  final skip = _origin == null || _password == null || _seedPath == null
      ? 'Set HMS_LIVE_ORIGIN, HMS_LIVE_PASSWORD and HMS_LIVE_DOCTOR_SEED to run'
      : null;

  late Map<String, Object?> seed;
  late int visitId;
  late int tokenId;
  late int patientId;
  String? token;
  int? hospitalId = 1;
  late ApiClient api;
  late ApiDoctorRepository doctor;

  setUpAll(() {
    if (skip != null) return;
    seed = Map<String, Object?>.from(
      jsonDecode(File(_seedPath!).readAsStringSync()) as Map,
    );
    visitId = seed['visit']! as int;
    tokenId = seed['token']! as int;
    patientId = seed['patient']! as int;
    api = ApiClient(
      config: ApiConfig(origin: _origin!),
      accessToken: () async => token,
      hospitalId: () => hospitalId,
      log: (_) {},
    );
    doctor = ApiDoctorRepository(api);
  });

  late int userId;

  test('1. a doctor signs in and works in their hospital', () async {
    final auth = ApiAuthRepository(api);
    token = (await auth.staffPasswordLogin(
      'demo.doctor1',
      _password!,
      _device,
    )).access;
    final contexts = await auth.meContexts();
    expect(contexts.accountType, AccountType.staff);
    final context = contexts.hospitals.single;
    expect(context.role, 'Doctor');
    hospitalId = context.id;
    userId = (await auth.staffMe()).id!;
  }, skip: skip);

  test(
    '2. dashboard data: own profile, today\'s appointments and queue',
    () async {
      final profile = await doctor.myProfile(
        hospitalId: hospitalId!,
        userId: userId,
      );
      expect(profile, isNotNull);
      final now = DateTime.now();
      await doctor.appointments(date: DateTime(now.year, now.month, now.day));
      final queue = await doctor.queue();
      expect(queue.map((t) => t.id), contains(tokenId));
    },
    skip: skip,
  );

  test('3. queue: an invalid move is refused, then call and start', () async {
    await expectLater(
      doctor.moveToken(tokenId, QueueAction.complete),
      _apiError(ApiErrorKind.validation),
    );
    expect(
      (await doctor.moveToken(tokenId, QueueAction.call)).status,
      'Called',
    );
    expect(
      (await doctor.moveToken(tokenId, QueueAction.startConsultation)).status,
      'In Consultation',
    );
  }, skip: skip);

  test('4. records: own patients found; others refused', () async {
    final found = await doctor.searchPatients('Demo Portal');
    expect(found.map((p) => p.id), contains(patientId));
    expect((await doctor.timeline(patientId)), isA<List<TimelineEvent>>());
    final other = seed['other_patient'] as int?;
    if (other != null) {
      await expectLater(doctor.patient(other), throwsA(isA<ApiException>()));
    }
  }, skip: skip);

  test(
    '5. consultation: vitals, note and diagnosis, signed and final',
    () async {
      expect(
        (await doctor.setVisitStatus(visitId, Visit.inConsultation)).status,
        Visit.inConsultation,
      );

      await doctor.addVitals(visitId, {
        VitalField.temperature: '36.9',
        VitalField.heartRate: '76',
        VitalField.weight: '70',
        VitalField.height: '175',
      });
      final vitals = await doctor.vitals(visitId);
      expect(vitals, isNotEmpty);
      expect(vitals.every((v) => v.visitId == visitId), isTrue);
      expect(vitals.last.bmi, isNotNull, reason: 'BMI comes from the server');
      await expectLater(
        doctor.addVitals(visitId, {VitalField.painScore: '11'}),
        _apiError(ApiErrorKind.validation),
      );

      final note = await doctor.addNote(visitId, {
        NoteSection.chiefComplaint: 'E2E synthetic complaint',
        NoteSection.plan: 'E2E synthetic plan',
      });
      expect(note.isSigned, isFalse);
      expect((await doctor.signNote(note.id)).isSigned, isTrue);
      await expectLater(
        doctor.signNote(note.id),
        _apiError(ApiErrorKind.conflict),
      );

      final codes = await doctor.icd10('hypertension');
      final diagnosis = await doctor.addDiagnosis(
        visitId: visitId,
        name: 'E2E synthetic diagnosis',
        icd10Code: codes.isEmpty ? null : codes.first.code,
        type: 'Provisional',
      );
      expect((await doctor.signDiagnosis(diagnosis.id)).isSigned, isTrue);
    },
    skip: skip,
  );

  test('6. prescription after the safety check, and a lab order', () async {
    final alerts = await doctor.safetyCheck(
      hospitalId: hospitalId!,
      patientId: patientId,
      medicines: [_medicine],
    );
    expect(
      alerts.where((a) => a.isBlocking),
      isEmpty,
      reason: 'synthetic medicine name',
    );
    final draft = PrescriptionDraft(
      hospitalId: hospitalId!,
      patientId: patientId,
      visitId: visitId,
      lines: const [
        MedicineLine(
          name: _medicine,
          dosage: '1 tab',
          frequency: 'Twice a day',
          duration: '3 days',
          quantity: 6,
        ),
      ],
    );
    final key = ApiClient.newIdempotencyKey();
    final rx = await doctor.createPrescription(draft, idempotencyKey: key);
    expect(rx.status, 'Confirmed');
    // A retry with the same key (say the first answer was lost) must return
    // the same prescription, not write a second one.
    final retried = await doctor.createPrescription(draft, idempotencyKey: key);
    expect(retried.id, rx.id);
    final mine = await doctor.prescriptions(patientId: patientId);
    expect(
      mine.where((p) => p.id == rx.id && p.visitId == visitId),
      hasLength(1),
    );

    final profile = await doctor.myProfile(
      hospitalId: hospitalId!,
      userId: userId,
    );
    final lab = await doctor.orderLabTest(
      hospitalId: hospitalId!,
      patientId: patientId,
      visitId: visitId,
      doctorId: profile!.id,
      name: 'E2E Mobile CBC',
      priority: 'Normal',
    );
    expect(lab.status, 'Ordered');
  }, skip: skip);

  test('7. complete the token and the visit', () async {
    expect(
      (await doctor.moveToken(tokenId, QueueAction.complete)).status,
      'Completed',
    );
    expect(
      (await doctor.setVisitStatus(visitId, Visit.completed)).status,
      Visit.completed,
    );
  }, skip: skip);

  test(
    '8. the patient sees the prescription, not the unreleased lab order',
    () async {
      String? patientToken;
      final patientApi = ApiClient(
        config: ApiConfig(origin: _origin!),
        accessToken: () async => patientToken,
        hospitalId: () => hospitalId,
        log: (_) {},
      );
      patientToken = (await ApiAuthRepository(patientApi).patientEmailLogin(
        'demo.patient@example.test',
        _password!,
        _device,
      )).access;
      final patient = ApiPatientRepository(patientApi);

      final prescriptions = await patient.prescriptions();
      expect(
        prescriptions.expand((p) => p.items).map((i) => i.name),
        contains(_medicine),
      );
      final labs = await patient.labTests();
      expect(labs.map((l) => l.name), isNot(contains('E2E Mobile CBC')));
    },
    skip: skip,
  );

  test('9. another hospital and no token are both refused', () async {
    hospitalId = 999999;
    await expectLater(doctor.visits(), throwsA(isA<ApiException>()));
    hospitalId = seed['hospital'] as int?;
    token = null;
    await expectLater(doctor.visits(), _apiError(ApiErrorKind.unauthorized));
    await expectLater(
      doctor.patient(patientId),
      _apiError(ApiErrorKind.unauthorized),
    );
  }, skip: skip);
}
