import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';
import 'package:hms_mobile/features/reception/data/reception_repository.dart';

import '../../support/test_app.dart';

// BUG-01 / BUG-04, synthetic data only.

class FakeReceptionRepository implements ReceptionRepository {
  Object? registerError;
  Object? linkError;
  final List<({NewPatientDraft draft, int hospital, bool confirmNew})>
  registered = [];
  final List<(String, DateTime)> linked = [];
  final List<int> checkedIn = [];

  @override
  Future<PatientSummary> registerPatient(
    NewPatientDraft draft,
    int hospitalId, {
    bool confirmNew = false,
  }) async {
    registered.add((
      draft: draft,
      hospital: hospitalId,
      confirmNew: confirmNew,
    ));
    final error = registerError;
    if (error != null) {
      registerError = null; // the second try (register anyway) succeeds
      throw error;
    }
    return PatientSummary(id: 50, name: draft.name, uhid: 'TGH-2026-000050');
  }

  @override
  Future<PatientSummary> linkPatient(String phone, DateTime dateOfBirth) async {
    linked.add((phone, dateOfBirth));
    if (linkError != null) throw linkError!;
    return const PatientSummary(
      id: 51,
      name: 'Synthetic Portal Patient',
      uhid: 'TGH-2026-000051',
    );
  }

  @override
  Future<QueueToken> checkIn(int appointmentId) async {
    checkedIn.add(appointmentId);
    return const QueueToken(id: 9, tokenNumber: 12, status: 'Waiting');
  }
}

Future<FakeReceptionRepository> pumpReception(
  WidgetTester tester,
  String location, {
  FakeDoctorRepository? doctor,
  FakeReceptionRepository? reception,
}) async {
  final repo = reception ?? FakeReceptionRepository();
  await pumpApp(
    tester,
    testServices(
      session: staffSession(role: 'Receptionist'),
      doctor: doctor ?? FakeDoctorRepository(),
      reception: repo,
    ),
    location: location,
  );
  return repo;
}

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> typeInto(WidgetTester tester, String key, String text) async {
  final field = find.descendant(
    of: find.byKey(ValueKey(key)),
    matching: find.byType(TextField),
  );
  await tester.ensureVisible(field);
  await tester.enterText(field, text);
  await tester.pump();
}

/// Types [day] (MM/DD/YYYY) into the date picker opened by [key].
Future<void> pickDate(WidgetTester tester, String key, String day) async {
  await tapVisible(tester, find.byKey(ValueKey(key)));
  final input = find.descendant(
    of: find.byType(DatePickerDialog),
    matching: find.byType(TextField),
  );
  await tester.enterText(input, day);
  await tester.tap(find.text('OK'));
  await tester.pumpAndSettle();
}

void main() {
  group('reception patients', () {
    testWidgets('search lists the server\'s patients with their ID and age', (
      tester,
    ) async {
      final doctor = FakeDoctorRepository(
        patients: const [
          PatientSummary(
            id: 3,
            name: 'Synthetic Kavya',
            uhid: 'TGH-2026-000003',
            age: 34,
          ),
        ],
      );
      await pumpReception(tester, '/patients', doctor: doctor);

      await typeInto(tester, 'reception-search', 'kavya');
      await tapVisible(
        tester,
        find.byKey(const Key('reception-search-submit')),
      );

      expect(doctor.searches, ['kavya']);
      expect(find.textContaining('TGH-2026-000003'), findsOneWidget);
      expect(find.textContaining('34 y'), findsOneWidget);
    });

    testWidgets('a new patient needs a date of birth, then gets a UHID', (
      tester,
    ) async {
      final repo = await pumpReception(tester, '/patients');
      await typeInto(tester, 'reception-name', 'Synthetic Walk In');
      await typeInto(tester, 'reception-phone', '9000003001');

      await tapVisible(tester, find.byKey(const Key('reception-register')));
      expect(find.text('Enter your date of birth.'), findsOneWidget);
      expect(repo.registered, isEmpty);

      await pickDate(tester, 'reception-dob', '04/03/2001');
      await tapVisible(tester, find.byKey(const Key('reception-register')));

      expect(repo.registered.single.hospital, 7);
      expect(repo.registered.single.draft.dateOfBirth, DateTime(2001, 4, 3));
      expect(find.textContaining('TGH-2026-000050'), findsOneWidget);
    });

    testWidgets('a patient-app account is linked instead of registered twice', (
      tester,
    ) async {
      final repo = FakeReceptionRepository()
        ..registerError = const ApiException(
          kind: ApiErrorKind.conflict,
          statusCode: 409,
          flags: {'portal_account'},
        );
      await pumpReception(tester, '/patients', reception: repo);
      await typeInto(tester, 'reception-name', 'Synthetic Portal Patient');
      await typeInto(tester, 'reception-phone', '9000003002');
      await pickDate(tester, 'reception-dob', '01/20/1985');

      await tapVisible(tester, find.byKey(const Key('reception-register')));
      expect(
        find.textContaining('already has a patient app account'),
        findsOneWidget,
      );
      expect(find.byKey(const Key('reception-register-anyway')), findsNothing);

      // The link form now holds the same number and date of birth.
      await tapVisible(tester, find.byKey(const Key('reception-link')));

      expect(repo.linked.single, ('9000003002', DateTime(1985, 1, 20)));
      expect(find.textContaining('TGH-2026-000051'), findsOneWidget);
    });

    testWidgets('a possible duplicate can be registered anyway, on purpose', (
      tester,
    ) async {
      final repo = FakeReceptionRepository()
        ..registerError = const ApiException(
          kind: ApiErrorKind.conflict,
          statusCode: 409,
        );
      await pumpReception(tester, '/patients', reception: repo);
      await typeInto(tester, 'reception-name', 'Synthetic Sibling');
      await typeInto(tester, 'reception-phone', '9000003003');
      await pickDate(tester, 'reception-dob', '06/01/2015');
      await tapVisible(tester, find.byKey(const Key('reception-register')));

      await tapVisible(
        tester,
        find.byKey(const Key('reception-register-anyway')),
      );

      expect([for (final r in repo.registered) r.confirmNew], [false, true]);
    });

    testWidgets('linking nobody says so', (tester) async {
      final repo = FakeReceptionRepository()
        ..linkError = const ApiException(
          kind: ApiErrorKind.notFound,
          statusCode: 404,
          flags: {'not_found'},
        );
      await pumpReception(tester, '/patients', reception: repo);
      await typeInto(tester, 'reception-link-phone', '9000003004');
      await pickDate(tester, 'reception-link-dob', '02/02/1990');

      await tapVisible(tester, find.byKey(const Key('reception-link')));

      expect(find.textContaining('Register them as new'), findsOneWidget);
    });
  });

  group('reception appointments and queue', () {
    testWidgets('a scheduled booking today is checked in and gets a token', (
      tester,
    ) async {
      final doctor = FakeDoctorRepository(
        appointmentRows: [
          Appointment(
            id: 21,
            status: AppointmentStatus.scheduled,
            patientName: 'Synthetic Booked',
            date: DateUtils.dateOnly(DateTime.now()),
            time: '10:00',
            doctorName: 'Dr Test',
          ),
          Appointment(
            id: 22,
            status: AppointmentStatus.checkedIn,
            patientName: 'Synthetic Waiting',
            date: DateUtils.dateOnly(DateTime.now()),
            time: '10:15',
          ),
        ],
      );
      final repo = await pumpReception(tester, '/appointments', doctor: doctor);

      expect(find.byKey(const ValueKey('check-in-22')), findsNothing);
      await tapVisible(tester, find.byKey(const ValueKey('check-in-21')));

      expect(repo.checkedIn, [21]);
      expect(find.textContaining('Token #12'), findsOneWidget);
    });

    testWidgets('the queue is shown without the doctor\'s moves', (
      tester,
    ) async {
      final doctor = FakeDoctorRepository(
        tokens: [
          QueueToken(
            id: 31,
            tokenNumber: 4,
            status: 'Waiting',
            patientName: 'Synthetic Queue Patient',
            visitId: 8,
            tokenDate: DateTime.now(),
          ),
        ],
      );
      await pumpReception(tester, '/queue', doctor: doctor);

      expect(find.text('Synthetic Queue Patient'), findsOneWidget);
      expect(find.text('Call'), findsNothing);
      expect(find.text('Open consultation'), findsNothing);
    });
  });

  group('patient registration (BUG-01, BUG-04)', () {
    testWidgets('sign-up asks for a date of birth and a hospital', (
      tester,
    ) async {
      final auth = FakeAuthRepository();
      await pumpApp(
        tester,
        testServices(authRepository: auth),
        location: '/register',
      );

      final fields = find.byType(TextField);
      await tester.enterText(fields.at(0), 'Synthetic Meera');
      await tester.enterText(fields.at(1), 'meera@example.test');
      await tester.enterText(fields.at(2), '9000003010');
      await tester.enterText(fields.at(3), 'correct-horse-42');
      await tester.enterText(fields.at(4), 'correct-horse-42');
      await tapVisible(tester, find.text('Create Account'));
      expect(find.text('Enter your date of birth.'), findsOneWidget);
      expect(auth.registrations, isEmpty);

      await pickDate(tester, 'register-dob', '04/02/1990');
      await tapVisible(tester, find.text('Create Account'));
      expect(
        find.text('Choose the hospital you want to register at.'),
        findsOneWidget,
      );

      await tapVisible(tester, find.byKey(const Key('register-hospital')));
      await tester.tap(find.text('City Hospital, Patna').last);
      await tester.pumpAndSettle();
      await tapVisible(tester, find.text('Create Account'));

      final sent = auth.registrations.single.toJson();
      expect(sent['date_of_birth'], '1990-04-02');
      expect(sent['hospital'], '1');
    });

    testWidgets('a patient at no hospital joins one from booking', (
      tester,
    ) async {
      final auth = FakeAuthRepository();
      await pumpApp(
        tester,
        testServices(
          session: patientSession(),
          authRepository: auth,
          patient: FakePatientRepository(options: const BookingOptions()),
        ),
        location: '/patient/appointments/book',
      );

      await tapVisible(tester, find.byKey(const Key('join-hospital')));
      await tester.tap(find.text('City Hospital, Patna').last);
      await tester.pumpAndSettle();
      await tapVisible(tester, find.byKey(const Key('join-hospital-submit')));

      expect(auth.joined, [1]);
    });
  });
}
