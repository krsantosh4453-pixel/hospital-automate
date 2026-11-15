import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/features/patient/data/patient_repository.dart';

import '../../support/test_app.dart';

/// A repository whose HTTP answers come from [routes] (path → body, status).
({ApiPatientRepository repo, FakeAdapter adapter}) repositoryWith(
  Map<String, (Object body, int status)> Function(RequestOptions) routes, {
  int? hospitalId = 7,
}) {
  final adapter = FakeAdapter((options) async {
    final answer = routes(options)[options.uri.path];
    if (answer == null) return jsonBody('{"detail":"Not found."}', 404);
    return jsonBody(jsonEncode(answer.$1), answer.$2);
  });
  final api = ApiClient(
    config: testConfig,
    accessToken: () async => 'access-token',
    hospitalId: () => hospitalId,
    adapter: adapter,
    log: (_) {},
  );
  return (repo: ApiPatientRepository(api), adapter: adapter);
}

const appointmentJson = {
  'id': 12,
  'hospital': 7,
  'patient': 41,
  'doctor': 3,
  'appointment_date': '2026-11-20',
  'appointment_time': '10:30:00',
  'status': 'Scheduled',
  'reason': 'Follow-up',
  'slot_seat': 1,
  'patient_name': 'Test Patient',
  'doctor_name': 'Dr Test Doctor',
  'hospital_name': 'Test General Hospital',
};

void main() {
  test(
    'appointments are read from the paged list, following next pages',
    () async {
      final setup = repositoryWith(
        (options) => {
          '/api/v1/appointments/': options.uri.queryParameters['page'] == '2'
              ? (
                  {
                    'count': 2,
                    'next': null,
                    'results': [
                      {...appointmentJson, 'id': 13, 'status': 'Completed'},
                    ],
                  },
                  200,
                )
              : (
                  {
                    'count': 2,
                    'next': 'http://x/api/v1/appointments/?page=2',
                    'results': [appointmentJson],
                  },
                  200,
                ),
        },
      );

      final rows = await setup.repo.appointments();

      expect(rows.map((a) => a.id), [12, 13]);
      final first = rows.first;
      expect(first.time, '10:30');
      expect(first.date, DateTime(2026, 11, 20));
      expect(first.doctorName, 'Dr Test Doctor');
      expect(first.isUpcoming, isTrue);
      expect(rows.last.isUpcoming, isFalse);
      final request = setup.adapter.requests.first;
      expect(request.method, 'GET');
      expect(request.headers['Authorization'], 'Bearer access-token');
      expect(request.headers['X-Hospital-ID'], '7');
      // The server decides whose records these are; no patient id is sent.
      expect(request.uri.queryParameters.containsKey('patient'), isFalse);
    },
  );

  test(
    'booking posts to appointments/book/ with the idempotency key',
    () async {
      final setup = repositoryWith(
        (_) => {'/api/v1/appointments/book/': (appointmentJson, 201)},
      );

      final booked = await setup.repo.book(
        BookingRequest(
          doctorId: 3,
          date: DateTime(2026, 11, 20),
          time: '10:30',
          reason: ' Follow-up ',
        ),
        'key-123',
      );

      expect(booked.id, 12);
      final request = setup.adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.headers['Idempotency-Key'], 'key-123');
      expect(request.data, {
        'doctor': 3,
        'appointment_date': '2026-11-20',
        'appointment_time': '10:30',
        'reason': 'Follow-up',
      });
    },
  );

  test('a taken slot (409) surfaces as a conflict', () async {
    final setup = repositoryWith(
      (_) => {
        '/api/v1/appointments/book/': (
          {'error': 'This slot was just booked. Please choose another time.'},
          409,
        ),
      },
    );

    await expectLater(
      setup.repo.book(
        BookingRequest(
          doctorId: 3,
          date: DateTime(2026, 11, 20),
          time: '10:30',
        ),
        'key-1',
      ),
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
    'booking options send hospital, doctor and date as query parameters',
    () async {
      final setup = repositoryWith(
        (_) => {
          '/api/v1/appointments/booking-options/': (
            {
              'hospitals': [
                {'id': 7, 'name': 'Test General Hospital'},
              ],
              'window_days': 60,
              'doctors': [
                {
                  'id': 3,
                  'name': 'Dr Test Doctor',
                  'specialization': 'General',
                  'availability': 'Mon-Fri',
                },
              ],
              'slots': [
                {
                  'time': '09:00',
                  'available': false,
                  'capacity': 1,
                  'remaining': 0,
                },
                {
                  'time': '09:15',
                  'available': true,
                  'capacity': 1,
                  'remaining': 1,
                },
              ],
            },
            200,
          ),
        },
      );

      final options = await setup.repo.bookingOptions(
        hospitalId: 7,
        doctorId: 3,
        date: DateTime(2026, 11, 20),
      );

      expect(options.hospitals.single.name, 'Test General Hospital');
      expect(options.doctors.single.specialization, 'General');
      expect(options.freeSlots.map((s) => s.time), ['09:15']);
      expect(setup.adapter.requests.single.uri.queryParameters, {
        'hospital': '7',
        'doctor': '3',
        'date': '2026-11-20',
      });
    },
  );

  test('records of every module parse from the serializer shapes', () async {
    final setup = repositoryWith(
      (_) => {
        '/api/v1/clinical/prescriptions/': (
          {
            'next': null,
            'results': [
              {
                'id': 5,
                'status': 'Confirmed',
                'created_at': '2026-11-10T09:00:00Z',
                'doctor_name': 'Dr Test Doctor',
                'hospital_name': 'Test General Hospital',
                'items': [
                  {
                    'id': 1,
                    'name': 'Test Medicine 500',
                    'dosage': '1 tablet',
                    'frequency': 'Twice a day',
                    'duration': '5 days',
                    'quantity': 10,
                    'instructions': 'After food',
                  },
                ],
              },
            ],
          },
          200,
        ),
        '/api/v1/laboratory/': (
          [
            {
              'id': 8,
              'name': 'Test Panel',
              'status': 'Released',
              'test_date': '2026-11-09T08:00:00Z',
              'released_at': '2026-11-10T08:00:00Z',
              'lab_result': {
                'result_data': {'Value A': '5.1'},
                'reference_ranges': {'Value A': '4-6'},
                'abnormal_flags': {},
                'result_text': null,
              },
            },
          ],
          200,
        ),
        '/api/v1/billing/invoices/': (
          {
            'next': null,
            'results': [
              {
                'id': 9,
                'invoice_number': 'INV-TEST-1',
                'status': 'Partially Paid',
                'total_amount': '1000.00',
                'total_paid': '400.00',
                'balance_due': '600.00',
                'items': [
                  {
                    'description': 'Consultation',
                    'quantity': 1,
                    'subtotal': '1000.00',
                  },
                ],
                'payments': [
                  {
                    'kind': 'payment',
                    'amount': '400.00',
                    'payment_method': 'Cash',
                    'receipt_number': 'R-1',
                    'paid_at': '2026-11-10T10:00:00Z',
                  },
                ],
              },
            ],
          },
          200,
        ),
        '/api/v1/encounters/queue-tokens/': (
          {
            'next': null,
            'results': [
              {
                'id': 2,
                'token_number': 14,
                'status': 'Waiting',
                'token_date': '2026-11-12',
                'queue_position': 3,
                'estimated_wait_minutes': 25,
              },
            ],
          },
          200,
        ),
        '/api/v1/documents/': (
          {
            'documents': [
              {
                'id': 4,
                'title': 'Test Report',
                'folder': 'Reports',
                'file_size': 2048,
              },
            ],
            'count': 1,
          },
          200,
        ),
      },
    );

    final prescription = (await setup.repo.prescriptions()).single;
    expect(prescription.isCurrent, isTrue);
    expect(prescription.items.single.frequency, 'Twice a day');

    final lab = (await setup.repo.labTests()).single;
    expect(lab.result!.values, {'Value A': '5.1'});
    expect(lab.result!.referenceRanges, {'Value A': '4-6'});
    expect(lab.result!.flags, isEmpty);

    final invoice = (await setup.repo.invoices()).single;
    expect(invoice.balanceDue, 600);
    expect(invoice.hasBalance, isTrue);
    expect(invoice.payments.single.receiptNumber, 'R-1');

    final token = (await setup.repo.queueTokens()).single;
    expect(token.isActive, isTrue);
    expect(token.estimatedWaitMinutes, 25);

    final document = (await setup.repo.documents()).single;
    expect(document.title, 'Test Report');
  });

  test('marking a notification read posts to its mark_read action', () async {
    final setup = repositoryWith(
      (_) => {
        '/api/v1/notifications/notifications/31/mark_read/': (
          {'id': 31, 'is_read': true},
          200,
        ),
      },
    );

    await setup.repo.markNotificationRead(31);

    final request = setup.adapter.requests.single;
    expect(request.method, 'POST');
    expect(
      request.uri.path,
      '/api/v1/notifications/notifications/31/mark_read/',
    );
  });

  test('the profile is read from auth/patient/me/', () async {
    final setup = repositoryWith(
      (_) => {
        '/api/v1/auth/patient/me/': (
          {
            'patient': {
              'id': 41,
              'name': 'Test Patient',
              'age': 30,
              'phone': '9000000001',
              'phone_verified': true,
            },
            'user': {'id': 90, 'username': 'p41'},
          },
          200,
        ),
      },
    );

    final user = await setup.repo.profile(AccountType.patient);

    expect(user.patient!.id, 41);
    expect(user.patient!.phoneVerified, isTrue);
  });

  test(
    'a refused request (another patient, signed out) becomes an ApiException',
    () async {
      final setup = repositoryWith(
        (_) => {
          '/api/v1/appointments/': (
            {'error': true, 'status_code': 403, 'message': 'Forbidden'},
            403,
          ),
        },
      );

      await expectLater(
        setup.repo.appointments(),
        throwsA(
          isA<ApiException>().having(
            (e) => e.kind,
            'kind',
            ApiErrorKind.forbidden,
          ),
        ),
      );
    },
  );
}
