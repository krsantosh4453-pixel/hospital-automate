import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/routing/app_router.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

import '../../support/test_app.dart';

// Synthetic records only.
final upcoming = Appointment(
  id: 12,
  status: AppointmentStatus.scheduled,
  date: DateTime(2030, 1, 15),
  time: '10:30',
  doctorName: 'Dr Upcoming Test',
  hospitalName: 'Test General Hospital',
);
final cancelled = Appointment(
  id: 13,
  status: AppointmentStatus.cancelled,
  date: DateTime(2026, 1, 2),
  time: '09:00',
  doctorName: 'Dr Cancelled Test',
);
final prescription = Prescription(
  id: 5,
  status: 'Confirmed',
  createdAt: DateTime(2026, 11, 10),
  doctorName: 'Dr Rx Test',
  items: const [
    PrescriptionItem(
      name: 'Test Medicine 500',
      dosage: '1 tablet',
      frequency: 'Twice a day',
      duration: '5 days',
      instructions: 'After food',
    ),
  ],
);
final labTest = LabTest(
  id: 8,
  name: 'Test Panel',
  status: 'Released',
  releasedAt: DateTime(2026, 11, 10, 9),
  result: const LabResultData(
    values: {'Value A': '5.1'},
    referenceRanges: {'Value A': '4-6'},
  ),
);
final invoice = Invoice(
  id: 9,
  status: 'Partially Paid',
  invoiceNumber: 'INV-TEST-1',
  createdAt: DateTime(2026, 11, 10),
  totalAmount: 1000,
  totalPaid: 400,
  balanceDue: 600,
  payments: [
    InvoicePayment(
      kind: 'payment',
      amount: 400,
      method: 'Cash',
      receiptNumber: 'R-1',
      paidAt: DateTime(2026, 11, 10, 10),
    ),
  ],
);
const waitingToken = QueueToken(
  id: 2,
  tokenNumber: 14,
  status: 'Waiting',
  queuePosition: 3,
  estimatedWaitMinutes: 25,
  doctorName: 'Dr Upcoming Test',
);

Future<FakePatientRepository> pumpPatient(
  WidgetTester tester,
  String location, {
  FakePatientRepository? repository,
}) async {
  final repo = repository ?? FakePatientRepository();
  await pumpApp(
    tester,
    testServices(session: patientSession(), patient: repo),
    location: location,
  );
  return repo;
}

/// Opens every patient page with records on screen; fails on any overflow.
Future<void> expectPatientPagesLayOut(WidgetTester tester, Size size) async {
  final repo = FakePatientRepository(
    appointmentRows: [upcoming, cancelled],
    tokens: const [waitingToken],
    prescriptionRows: [prescription],
    labRows: [labTest],
    invoiceRows: [invoice],
  );
  for (final path in [
    '/',
    '/patient/appointments',
    '/patient/appointments/book',
    '/patient/queue',
    '/patient/prescriptions',
    '/patient/lab-results',
    '/patient/bills',
    '/patient/documents',
    '/patient/notifications',
  ]) {
    await pumpApp(
      tester,
      testServices(session: patientSession(), patient: repo),
      size: size,
      location: path,
    );
    expect(tester.takeException(), isNull, reason: path);
  }
}

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

void main() {
  group('patient dashboard', () {
    testWidgets('shows the patient\'s real records and figures', (
      tester,
    ) async {
      await pumpPatient(
        tester,
        '/',
        repository: FakePatientRepository(
          appointmentRows: [upcoming, cancelled],
          prescriptionRows: [prescription],
          labRows: [labTest],
          invoiceRows: [invoice],
          tokens: const [waitingToken],
        ),
      );

      expect(find.text('Dr Upcoming Test'), findsWidgets);
      expect(find.text('14'), findsOneWidget); // the active token
      expect(find.text('Test Panel'), findsOneWidget);
      expect(find.text('Dr Rx Test'), findsOneWidget);
      expect(find.text('₹600.00'), findsOneWidget); // outstanding balance hint
      expect(
        find.text('Showing records at Test General Hospital'),
        findsOneWidget,
      );
    });

    testWidgets('shows empty states when the patient has no records', (
      tester,
    ) async {
      await pumpPatient(tester, '/');

      expect(find.text('No upcoming appointments'), findsOneWidget);
      expect(find.text('No prescriptions yet'), findsOneWidget);
      expect(find.text('No lab reports yet'), findsOneWidget);
    });

    testWidgets('when nothing can be loaded it says so and shows no records', (
      tester,
    ) async {
      final repo = FakePatientRepository(appointmentRows: [upcoming])
        ..listError = networkError;
      await pumpPatient(tester, '/', repository: repo);

      expect(
        find.text(
          'Your records could not be loaded. Check your connection and try again.',
        ),
        findsOneWidget,
      );
      expect(find.text('Dr Upcoming Test'), findsNothing);
    });
  });

  group('appointments', () {
    testWidgets('lists bookings and filters cancelled ones', (tester) async {
      await pumpPatient(
        tester,
        '/patient/appointments',
        repository: FakePatientRepository(
          appointmentRows: [upcoming, cancelled],
        ),
      );

      expect(find.text('Dr Upcoming Test'), findsOneWidget);
      expect(find.text('Dr Cancelled Test'), findsOneWidget);

      await tapVisible(tester, find.widgetWithText(ChoiceChip, 'Cancelled'));

      expect(find.text('Dr Upcoming Test'), findsNothing);
      expect(find.text('Dr Cancelled Test'), findsOneWidget);
    });

    testWidgets('a network failure shows a retry that reloads', (tester) async {
      final repo = FakePatientRepository(appointmentRows: [upcoming])
        ..listError = networkError;
      await pumpPatient(tester, '/patient/appointments', repository: repo);

      expect(find.text('Try again'), findsOneWidget);
      repo.listError = null;
      await tapVisible(tester, find.text('Try again'));

      expect(find.text('Dr Upcoming Test'), findsOneWidget);
      expect(repo.appointmentCalls, 2);
    });
  });

  group('booking', () {
    Future<void> chooseDoctorAndSlot(WidgetTester tester) async {
      // The patient's selected hospital is chosen for them and shown.
      expect(
        find.descendant(
          of: find.byKey(const ValueKey('booking-hospital-7')),
          matching: find.text('Test General Hospital'),
        ),
        findsOneWidget,
      );
      await tapVisible(tester, find.byKey(const Key('booking-doctor-7')));
      await tester.tap(find.text('Dr Test Doctor — General').last);
      await tester.pumpAndSettle();
      // 10:15 is full on the server, so only 10:00 is offered.
      expect(find.widgetWithText(ChoiceChip, '10:15'), findsNothing);
      await tapVisible(tester, find.widgetWithText(ChoiceChip, '10:00'));
    }

    testWidgets('books a free slot and shows the server\'s confirmation', (
      tester,
    ) async {
      final repo = await pumpPatient(tester, '/patient/appointments/book');

      await chooseDoctorAndSlot(tester);
      await tapVisible(tester, find.byKey(const Key('booking-submit')));

      expect(repo.bookings.single.request.doctorId, 3);
      expect(repo.bookings.single.request.time, '10:00');
      expect(find.text('Appointment booked'), findsOneWidget);
      expect(find.text('#501'), findsOneWidget);
    });

    testWidgets('a second tap while booking sends no second request', (
      tester,
    ) async {
      final repo = FakePatientRepository()..bookGate = Completer<void>();
      await pumpPatient(tester, '/patient/appointments/book', repository: repo);
      await chooseDoctorAndSlot(tester);

      final submit = find.byKey(const Key('booking-submit'));
      await tester.ensureVisible(submit);
      await tester.tap(submit);
      await tester.pump();
      await tester.tap(submit, warnIfMissed: false);
      await tester.pump();

      expect(repo.bookings, hasLength(1));
      repo.bookGate!.complete();
      await tester.pumpAndSettle();
      expect(find.text('Appointment booked'), findsOneWidget);
    });

    testWidgets('a retry after a network failure reuses the idempotency key', (
      tester,
    ) async {
      final repo = FakePatientRepository()..bookError = networkError;
      await pumpPatient(tester, '/patient/appointments/book', repository: repo);
      await chooseDoctorAndSlot(tester);

      await tapVisible(tester, find.byKey(const Key('booking-submit')));
      expect(find.text('Appointment booked'), findsNothing);
      repo.bookError = null;
      await tapVisible(tester, find.byKey(const Key('booking-submit')));

      expect(repo.bookings, hasLength(2));
      expect(repo.bookings[0].key, repo.bookings[1].key);
      expect(find.text('Appointment booked'), findsOneWidget);
    });

    testWidgets('a slot taken meanwhile (409) is explained, not confirmed', (
      tester,
    ) async {
      final repo = FakePatientRepository()
        ..bookError = const ApiException(
          kind: ApiErrorKind.conflict,
          statusCode: 409,
        );
      await pumpPatient(tester, '/patient/appointments/book', repository: repo);
      await chooseDoctorAndSlot(tester);

      await tapVisible(tester, find.byKey(const Key('booking-submit')));

      expect(
        find.text(
          'This time was just booked by someone else. Please choose another time.',
        ),
        findsOneWidget,
      );
      expect(find.text('Appointment booked'), findsNothing);
    });
  });

  testWidgets('queue shows the token and asks again on the poll interval', (
    tester,
  ) async {
    final repo = await pumpPatient(
      tester,
      '/patient/queue',
      repository: FakePatientRepository(tokens: const [waitingToken]),
    );

    expect(find.text('14'), findsOneWidget);
    expect(find.text('#3'), findsOneWidget);
    expect(find.text('25 min'), findsOneWidget);
    expect(find.textContaining('Wait times are estimates'), findsOneWidget);
    final calls = repo.queueCalls;

    await tester.pump(const Duration(seconds: 31));
    await tester.pumpAndSettle();

    expect(repo.queueCalls, calls + 1);
  });

  group('queue after the consultation (BUG-02)', () {
    QueueToken token(String status, {DateTime? day}) => QueueToken(
      id: 3,
      tokenNumber: 3,
      status: status,
      queuePosition: 2,
      estimatedWaitMinutes: 15,
      tokenDate: day ?? DateTime.now(),
      doctorName: 'Dr Upcoming Test',
    );

    testWidgets('a completed token leaves no waiting information', (
      tester,
    ) async {
      await pumpPatient(
        tester,
        '/patient/queue',
        repository: FakePatientRepository(tokens: [token('Completed')]),
      );

      expect(find.text('No active token'), findsOneWidget);
      expect(find.text('#2'), findsNothing);
      expect(find.textContaining('Wait times are estimates'), findsNothing);
    });

    testWidgets('in consultation shows no position and no "stay nearby"', (
      tester,
    ) async {
      await pumpPatient(
        tester,
        '/patient/queue',
        repository: FakePatientRepository(tokens: [token('In Consultation')]),
      );

      expect(
        find.textContaining('consultation is in progress'),
        findsOneWidget,
      );
      expect(find.text('#2'), findsNothing);
      expect(find.textContaining("don't miss your call"), findsNothing);
    });

    testWidgets('a token left open on an earlier day is not shown', (
      tester,
    ) async {
      final yesterday = DateTime.now().subtract(const Duration(days: 1));
      await pumpPatient(
        tester,
        '/patient/queue',
        repository: FakePatientRepository(
          tokens: [token('Waiting', day: yesterday)],
        ),
      );

      expect(find.text('No active token'), findsOneWidget);
    });
  });

  testWidgets('prescriptions show each medicine as the doctor wrote it', (
    tester,
  ) async {
    await pumpPatient(
      tester,
      '/patient/prescriptions',
      repository: FakePatientRepository(prescriptionRows: [prescription]),
    );

    expect(find.text('Test Medicine 500'), findsOneWidget);
    expect(find.text('Frequency: Twice a day'), findsOneWidget);
    expect(find.text('Instructions: After food'), findsOneWidget);
  });

  testWidgets('a released lab report opens with its values and range', (
    tester,
  ) async {
    await pumpPatient(
      tester,
      '/patient/lab-results',
      repository: FakePatientRepository(labRows: [labTest]),
    );

    await tapVisible(tester, find.text('Test Panel'));

    expect(find.text('5.1 · Reference range: 4-6'), findsOneWidget);
  });

  testWidgets('bills show the balance and the payment history', (tester) async {
    await pumpPatient(
      tester,
      '/patient/bills',
      repository: FakePatientRepository(invoiceRows: [invoice]),
    );

    expect(find.text('₹600.00'), findsOneWidget);
    expect(find.text('Bills are paid at the hospital'), findsOneWidget);
    await tapVisible(tester, find.text('INV-TEST-1'));

    expect(find.text('Payment history'), findsOneWidget);
    expect(find.text('₹400.00 (R-1)'), findsOneWidget);
  });

  testWidgets(
    'opening an unread notification marks it read and opens its page',
    (tester) async {
      final repo = await pumpPatient(
        tester,
        '/patient/notifications',
        repository: FakePatientRepository(
          notificationRows: [
            PatientNotification(
              id: 31,
              title: 'Your token was called',
              message: 'Please go to room 2.',
              type: 'patient_called',
              isRead: false,
              createdAt: DateTime(2026, 11, 12, 9),
            ),
          ],
        ),
      );

      await tapVisible(tester, find.text('Your token was called'));

      expect(repo.markedRead, [31]);
      expect(find.text('No active token'), findsOneWidget); // the queue page
    },
  );

  // The suite's layout standards (responsive_layout_test.dart): a phone at
  // 200% text and the smallest phone at normal text.
  for (final (size, scale) in [(phoneSize, 2.0), (smallPhoneSize, 1.0)]) {
    testWidgets('every patient page lays out at $size, text ×$scale', (
      tester,
    ) async {
      tester.platformDispatcher.textScaleFactorTestValue = scale;
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      await expectPatientPagesLayOut(tester, size);
    });
  }

  group('access', () {
    test('signed-out visitors cannot open patient pages', () {
      for (final path in [
        '/patient/appointments/book',
        '/patient/notifications',
        '/patient/profile',
        '/patient/bills',
      ]) {
        expect(
          redirectFor(SessionState.signedOut, path),
          '/patient-login',
          reason: path,
        );
      }
    });

    test('staff are sent away from patient pages', () {
      expect(redirectFor(staffSession(), '/patient/notifications'), '/');
      expect(redirectFor(staffSession(), '/patient/appointments/book'), '/');
    });

    testWidgets('switching hospital reloads records for the new hospital', (
      tester,
    ) async {
      final repo = FakePatientRepository(appointmentRows: [upcoming]);
      final services = testServices(
        session: patientSession(
          hospitals: const [
            HospitalContext(
              id: 7,
              name: 'Test General Hospital',
              role: 'Patient',
            ),
            HospitalContext(
              id: 8,
              name: 'Second Test Hospital',
              role: 'Patient',
            ),
          ],
        ),
        patient: repo,
      );
      await pumpApp(tester, services, location: '/patient/appointments');
      expect(repo.appointmentCalls, 1);

      await services.session.selectHospital(8);
      await tester.pumpAndSettle();

      expect(repo.appointmentCalls, 2);
    });
  });
}
