import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/doctor/ui/doctor_appointments_screen.dart';
import 'package:hms_mobile/features/doctor/ui/order_sections.dart';
import 'package:hms_mobile/features/doctor/ui/queue_board_screen.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';

import '../../support/test_app.dart';

({ApiDoctorRepository repo, FakeAdapter adapter}) doctorRepo(
  Map<String, (Object, int)> Function(RequestOptions) routes,
) {
  final adapter = FakeAdapter((options) async {
    final answer = routes(options)['${options.method} ${options.uri.path}'];
    if (answer == null) return jsonBody('{"detail":"Not found."}', 404);
    return jsonBody(jsonEncode(answer.$1), answer.$2);
  });
  final api = ApiClient(
    config: testConfig,
    accessToken: () async => 'doctor-token',
    hospitalId: () => 1,
    adapter: adapter,
    log: (_) {},
  );
  return (repo: ApiDoctorRepository(api), adapter: adapter);
}

Map<String, Object?> page(List<Map<String, Object?>> rows) => {
  'count': rows.length,
  'next': null,
  'results': rows,
};

void main() {
  group('vital limits follow the server', () {
    test('empty means not measured', () {
      expect(VitalField.temperature.check(''), isNull);
    });
    test('pain score is 0–10', () {
      expect(VitalField.painScore.check('10'), isNull);
      expect(VitalField.painScore.check('11'), VitalError.tooHigh);
    });
    test('integer fields refuse decimals, decimal fields allow two places', () {
      expect(VitalField.heartRate.check('72.5'), VitalError.wholeNumber);
      expect(VitalField.temperature.check('36.85'), isNull);
      expect(VitalField.temperature.check('36.855'), VitalError.tooPrecise);
    });
    test('text and negatives are refused; SpO2 at most 100', () {
      expect(VitalField.weight.check('seventy'), VitalError.notANumber);
      expect(VitalField.weight.check('-1'), VitalError.negative);
      expect(VitalField.spo2.check('101'), VitalError.tooHigh);
    });
  });

  test('queue moves offered match the server transitions', () {
    expect(actionsFor('Waiting'), [
      QueueAction.call,
      QueueAction.skip,
      QueueAction.noShow,
    ]);
    expect(actionsFor('Ready'), contains(QueueAction.startConsultation));
    expect(actionsFor('In Consultation'), [
      QueueAction.complete,
      QueueAction.skip,
    ]);
    expect(actionsFor('Completed'), isEmpty);
    expect(actionsFor('No Show'), isEmpty);
  });

  test('medicine lines need a name and a quantity of at least 1', () {
    final t = AppLocalizationsEn();
    expect(checkLines(t, const []), t.addOneMedicine);
    expect(
      checkLines(t, const [MedicineLine(name: ' ')]),
      t.medicineNameRequired(1),
    );
    expect(
      checkLines(t, const [MedicineLine(name: 'A', quantity: 0)]),
      t.medicineQuantityInvalid(1),
    );
    expect(checkLines(t, const [MedicineLine(name: 'A')]), isNull);
  });

  test('appointment ranges split around today', () {
    final day0 = DateTime(2026, 11, 12);
    final rows = [
      Appointment(
        id: 1,
        status: 'Scheduled',
        date: DateTime(2026, 11, 12),
        time: '10:00',
      ),
      Appointment(id: 2, status: 'Scheduled', date: DateTime(2026, 11, 13)),
      Appointment(id: 3, status: 'Completed', date: DateTime(2026, 11, 1)),
    ];
    expect(
      appointmentsIn(rows, AppointmentRange.today, day0).map((a) => a.id),
      [1],
    );
    expect(
      appointmentsIn(rows, AppointmentRange.upcoming, day0).map((a) => a.id),
      [2],
    );
    expect(appointmentsIn(rows, AppointmentRange.past, day0).map((a) => a.id), [
      3,
    ]);
    expect(
      appointmentsIn(
        rows,
        AppointmentRange.day,
        day0,
        picked: DateTime(2026, 11, 13),
      ).map((a) => a.id),
      [2],
    );
  });

  group('API contract (paths, methods and bodies verified against the server)', () {
    test(
      'vitals of a visit are filtered here, since the server ignores ?visit=',
      () async {
        final setup = doctorRepo(
          (_) => {
            'GET /api/v1/clinical/vitals/': (
              page([
                {
                  'id': 1,
                  'visit': 5,
                  'systolic_bp': 120,
                  'bmi': 22.9,
                  'recorded_at': '2026-11-12T09:00:00Z',
                },
                {'id': 2, 'visit': 6, 'systolic_bp': 140},
              ]),
              200,
            ),
          },
        );

        final rows = await setup.repo.vitals(5);

        expect(rows.map((r) => r.id), [1]);
        expect(rows.single.values[VitalField.systolicBp], '120');
        expect(rows.single.bmi, 22.9);
        expect(setup.adapter.requests.single.uri.queryParameters['visit'], '5');
      },
    );

    test('vitals are posted as numbers, only the ones measured', () async {
      final setup = doctorRepo(
        (_) => {
          'POST /api/v1/clinical/vitals/': ({'id': 9, 'visit': 5}, 201),
        },
      );

      await setup.repo.addVitals(5, {
        VitalField.temperature: '36.8',
        VitalField.heartRate: '72',
      });

      expect(setup.adapter.requests.single.data, {
        'visit': 5,
        'temperature': 36.8,
        'heart_rate': 72,
      });
    });

    test('a queue move posts to the token action', () async {
      final setup = doctorRepo(
        (_) => {
          'POST /api/v1/encounters/queue-tokens/4/start-consultation/': (
            {'id': 4, 'token_number': 7, 'status': 'In Consultation'},
            200,
          ),
        },
      );

      final token = await setup.repo.moveToken(
        4,
        QueueAction.startConsultation,
      );

      expect(token.status, 'In Consultation');
    });

    test(
      'an invalid queue move (400) surfaces as a validation error',
      () async {
        final setup = doctorRepo(
          (_) => {
            'POST /api/v1/encounters/queue-tokens/4/complete/': (
              {'detail': 'Invalid transition from Waiting to Completed'},
              400,
            ),
          },
        );

        await expectLater(
          setup.repo.moveToken(4, QueueAction.complete),
          throwsA(
            isA<ApiException>().having(
              (e) => e.kind,
              'kind',
              ApiErrorKind.validation,
            ),
          ),
        );
      },
    );

    test(
      'a prescription is posted as the web form does, with the override reason',
      () async {
        final setup = doctorRepo(
          (_) => {
            'POST /api/v1/clinical/prescriptions/': (
              {'id': 77, 'status': 'Confirmed', 'visit': 5, 'items': []},
              201,
            ),
          },
        );

        final rx = await setup.repo.createPrescription(
          const PrescriptionDraft(
            hospitalId: 1,
            patientId: 2,
            visitId: 5,
            lines: [
              MedicineLine(name: ' Test Med ', dosage: '1 tab', quantity: 6),
            ],
            overrideReason: 'Benefit outweighs the risk',
          ),
          idempotencyKey: 'synthetic-rx-key',
        );

        expect(rx.id, 77);
        // The server de-duplicates retries by this header.
        expect(
          setup.adapter.requests.single.headers['Idempotency-Key'],
          'synthetic-rx-key',
        );
        expect(setup.adapter.requests.single.data, {
          'hospital': 1,
          'patient': 2,
          'visit': 5,
          'status': 'Confirmed',
          'items': [
            {
              'name': 'Test Med',
              'dosage': '1 tab',
              'frequency': '',
              'duration': '',
              'quantity': 6,
              'instructions': '',
            },
          ],
          'safety_override_reason': 'Benefit outweighs the risk',
        });
      },
    );

    test('editing a signed record (409) is reported as a conflict', () async {
      final setup = doctorRepo(
        (_) => {
          'POST /api/v1/clinical/diagnoses/3/sign/': (
            {'error': true, 'message': 'This record is already signed.'},
            409,
          ),
        },
      );

      await expectLater(
        setup.repo.signDiagnosis(3),
        throwsA(
          isA<ApiException>().having(
            (e) => e.kind,
            'kind',
            ApiErrorKind.conflict,
          ),
        ),
      );
    });

    test(
      'the own profile is the doctors/ row whose user is this login',
      () async {
        final setup = doctorRepo(
          (_) => {
            'GET /api/v1/doctors/': (
              page([
                {'id': 1, 'user': 50, 'name': 'Other Doctor'},
                {
                  'id': 2,
                  'user': 90,
                  'name': 'Dr Test',
                  'registration_verified_at': '2026-01-01T00:00:00Z',
                },
              ]),
              200,
            ),
          },
        );

        final me = await setup.repo.myProfile(hospitalId: 1, userId: 90);

        expect(me!.id, 2);
        expect(me.registrationVerified, isTrue);
        expect(
          setup.adapter.requests.single.uri.queryParameters['hospital'],
          '1',
        );
      },
    );

    test('ICD-10 suggestions come from the terminology endpoint', () async {
      final setup = doctorRepo(
        (_) => {
          'GET /api/v1/terminology/icd10/': (
            {
              'results': [
                {
                  'code': 'I10',
                  'description': 'Essential (primary) hypertension',
                  'billable': true,
                },
              ],
            },
            200,
          ),
        },
      );

      final codes = await setup.repo.icd10('hypert');

      expect(codes.single.code, 'I10');
      expect(setup.adapter.requests.single.uri.queryParameters, {
        'q': 'hypert',
        'limit': '15',
      });
    });

    test('a lab order names the doctor, visit and priority', () async {
      final setup = doctorRepo(
        (_) => {
          'POST /api/v1/laboratory/': (
            {'id': 8, 'name': 'CBC', 'status': 'Ordered'},
            201,
          ),
        },
      );

      final test = await setup.repo.orderLabTest(
        hospitalId: 1,
        patientId: 2,
        visitId: 5,
        doctorId: 3,
        name: 'CBC',
        priority: 'Urgent',
      );

      expect(test.status, 'Ordered');
      expect(setup.adapter.requests.single.data, {
        'hospital': 1,
        'patient': 2,
        'visit': 5,
        'doctor': 3,
        'name': 'CBC',
        'priority': 'Urgent',
      });
    });
  });
}
