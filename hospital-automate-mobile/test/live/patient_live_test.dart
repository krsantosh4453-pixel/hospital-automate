// Opt-in end-to-end check of the patient module against a REAL backend,
// using the app's own API client and repositories (no fakes).
//
// Only for a throwaway test server seeded with synthetic data, e.g.
//   DJANGO_SETTINGS_MODULE=config.settings.e2e manage.py seed_demo --password=…
// then:
//   HMS_LIVE_ORIGIN=http://127.0.0.1:8137 HMS_LIVE_PASSWORD=… \
//     flutter test test/live/patient_live_test.dart
// It books one appointment for the demo patient. Never point it at a
// server with real patients. Skipped when the variables are not set.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/features/patient/data/patient_repository.dart';

final _origin = Platform.environment['HMS_LIVE_ORIGIN'];
final _password = Platform.environment['HMS_LIVE_PASSWORD'];
final _email =
    Platform.environment['HMS_LIVE_PATIENT_EMAIL'] ??
    'demo.patient@example.test';

const _device = DeviceInfo(
  deviceId: 'live-test-device',
  platform: 'other',
  appVersion: 'live-test',
);

void main() {
  final skip = _origin == null || _password == null
      ? 'Set HMS_LIVE_ORIGIN and HMS_LIVE_PASSWORD to run against a test server'
      : null;

  String? accessToken;
  int? hospitalId;
  late ApiClient api;
  late ApiPatientRepository patients;
  late int patientId;

  setUpAll(() {
    if (skip != null) return;
    api = ApiClient(
      config: ApiConfig(origin: _origin!),
      accessToken: () async => accessToken,
      hospitalId: () => hospitalId,
      log: (_) {},
    );
    patients = ApiPatientRepository(api);
  });

  test('1. signs in through the patient email flow', () async {
    final auth = ApiAuthRepository(api);
    final tokens = await auth.patientEmailLogin(_email, _password!, _device);
    accessToken = tokens.access;

    final contexts = await auth.meContexts();
    expect(contexts.accountType, AccountType.patient);
    expect(contexts.hospitals, isNotEmpty);
    hospitalId = contexts.hospitals.first.id;

    final user = await patients.profile(AccountType.patient);
    patientId = user.patient!.id;
    expect(user.patient!.emailVerified, isTrue);
  }, skip: skip);

  test(
    '2. books a free slot once, even when the request is repeated',
    () async {
      final hospitals = (await patients.bookingOptions()).hospitals;
      expect(hospitals.map((h) => h.id), contains(hospitalId));
      final doctors = (await patients.bookingOptions(hospitalId: hospitalId))
          .doctors;
      expect(doctors, isNotEmpty);

      final day = DateTime.now().add(const Duration(days: 2));
      BookingRequest? request;
      for (final doctor in doctors) {
        final slots = (await patients.bookingOptions(
          hospitalId: hospitalId,
          doctorId: doctor.id,
          date: day,
        )).freeSlots;
        if (slots.isNotEmpty) {
          request = BookingRequest(
            doctorId: doctor.id,
            date: day,
            time: slots.first.time,
            reason: 'Mobile live test',
          );
          break;
        }
      }
      expect(request, isNotNull, reason: 'no free slot in two days');

      final key = ApiClient.newIdempotencyKey();
      final first = await patients.book(request!, key);
      final replay = await patients.book(request, key);
      expect(replay.id, first.id, reason: 'same key must not book twice');
      expect(first.status, AppointmentStatus.scheduled);

      final mine = await patients.appointments();
      expect(mine.where((a) => a.id == first.id), hasLength(1));
      expect(mine.every((a) => a.patientId == patientId), isTrue);
    },
    skip: skip,
  );

  test('3. reads only this patient\'s records in every module', () async {
    final prescriptions = await patients.prescriptions();
    expect(
      prescriptions.expand((p) => p.items).map((i) => i.name),
      contains('E2E Test Medicine 500'),
    );

    final labs = await patients.labTests();
    expect(labs.map((l) => l.name), contains('E2E Test Panel'));
    expect(
      labs.map((l) => l.name),
      isNot(contains('E2E Pending Panel')),
      reason: 'unreleased tests must stay hidden from the patient',
    );
    expect(labs.every((l) => l.status == 'Released'), isTrue);

    final invoices = await patients.invoices();
    final bill = invoices.firstWhere(
      (i) => i.items.any((line) => line.description == 'E2E Consultation'),
    );
    expect(bill.balanceDue, 600);
    expect(bill.payments.single.amount, 400);

    final tokens = await patients.queueTokens();
    expect(tokens, isA<List<Object>>());

    final documents = await patients.documents();
    expect(documents, isA<List<Object>>());
  }, skip: skip);

  test('4. marks a notification read on the server', () async {
    final before = await patients.notifications();
    final note = before.firstWhere((n) => n.title == 'E2E token called');

    await patients.markNotificationRead(note.id);

    final after = await patients.notifications();
    expect(after.firstWhere((n) => n.id == note.id).isRead, isTrue);
  }, skip: skip);

  test('5. cannot reach other patients or other hospitals', () async {
    // Asking for another patient's id still returns only this patient's rows.
    for (final otherId in [1, 2, 3, 4, patientId + 1]) {
      if (otherId == patientId) continue;
      final rows = await api.get<Object?>(
        'appointments/',
        query: {'patient': otherId},
        decode: (json) => json,
      );
      final results = rows is Map ? rows['results'] as List : rows as List;
      expect(
        results.every((row) => (row as Map)['patient'] == patientId),
        isTrue,
        reason: 'patient=$otherId leaked other rows',
      );
    }
    // A hospital the patient is not registered at is refused.
    await expectLater(
      patients.bookingOptions(hospitalId: 999999),
      throwsA(isA<ApiException>()),
    );
    // A patient may not write appointments directly (only book/).
    await expectLater(
      api.post('appointments/', body: {'doctor': 1}, decode: (_) {}),
      throwsA(isA<ApiException>().having((e) => e.statusCode, 'status', 403)),
    );
  }, skip: skip);

  test('6. after sign-out (no token) every patient endpoint refuses', () async {
    accessToken = null;
    for (final call in <Future<Object?> Function()>[
      patients.appointments,
      patients.prescriptions,
      patients.labTests,
      patients.invoices,
      patients.notifications,
      () => patients.profile(AccountType.patient),
    ]) {
      await expectLater(
        call(),
        throwsA(
          isA<ApiException>().having(
            (e) => e.kind,
            'kind',
            ApiErrorKind.unauthorized,
          ),
        ),
      );
    }
  }, skip: skip);
}
