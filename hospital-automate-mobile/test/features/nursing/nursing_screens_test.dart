import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/nursing/data/nursing_models.dart';

import '../../support/test_app.dart';

// Synthetic data only.
const nursePermissions = {
  'Dashboard.View',
  'Nurses.View',
  'IPD.View',
  'Queue.View',
  'Emergency.View',
};

SessionState nurseSession({String role = 'Nurse'}) => SessionState(
  user: const SessionUser(id: 91, displayName: 'nurse.test', firstName: 'Test'),
  hospitals: [
    HospitalContext(
      id: 1,
      name: 'Test General Hospital',
      role: role,
      permissions: nursePermissions,
    ),
  ],
  activeHospitalId: 1,
);

const testPatient = PatientSummary(
  id: 11,
  name: 'Test Ward Patient',
  uhid: 'UH-0011',
  age: 64,
  gender: 'Female',
);

const stay = Admission(
  id: 3,
  status: 'Admitted',
  patientId: 11,
  patientName: 'Test Ward Patient',
  wardName: 'Ward A',
  bedNumber: 'B4',
  doctorName: 'Dr Test',
);

final dueDose = Dose(
  id: 9,
  status: Dose.scheduled,
  medicineName: 'Synthetic Paracetamol',
  dose: '500 mg',
  route: 'Oral',
  patientId: 11,
  patientName: 'Test Ward Patient',
  scheduledAt: DateTime(2026, 11, 15, 9),
);

MedicationOrder orderWith(List<Dose> doses) => MedicationOrder(
  id: 2,
  medicineName: 'Synthetic Paracetamol',
  isActive: true,
  dose: '500 mg',
  route: 'Oral',
  frequency: 'TID',
  doses: doses,
);

FakeNursingRepository wardRepo() => FakeNursingRepository(
  patients: const [testPatient],
  admissionRows: const [stay],
  orderRows: [
    orderWith([dueDose]),
  ],
);

Future<FakeNursingRepository> pumpNurse(
  WidgetTester tester,
  String location, {
  FakeNursingRepository? repository,
  SessionState? session,
  AppLanguage language = AppLanguage.en,
}) async {
  final repo = repository ?? wardRepo();
  await pumpApp(
    tester,
    testServices(
      session: session ?? nurseSession(),
      nursing: repo,
      language: language,
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

Future<void> enter(WidgetTester tester, Finder field, String text) async {
  await tester.ensureVisible(field);
  await tester.pumpAndSettle();
  await tester.enterText(field, text);
  await tester.pump();
}

void main() {
  group('nurse home', () {
    testWidgets('shows the profile, today\'s duty and what needs attention', (
      tester,
    ) async {
      await pumpNurse(
        tester,
        '/',
        repository: FakeNursingRepository(
          admissionRows: const [
            stay,
            Admission(
              id: 4,
              status: 'Admitted',
              patientId: 12,
              patientName: 'Test Bedless Patient',
            ),
          ],
          wardDutyRows: const [
            DutyAssignment(id: 1, shift: 'Morning', wardName: 'Ward A'),
          ],
          dueRows: [
            Dose(
              id: 8,
              status: Dose.scheduled,
              medicineName: 'Synthetic Ceftriaxone',
              patientId: 11,
              patientName: 'Test Ward Patient',
              isDelayed: true,
              scheduledAt: DateTime(2026, 11, 15, 6),
            ),
          ],
          taskRows: const [
            CareTask(
              id: 1,
              type: 'Vitals',
              description: 'Synthetic hourly vitals',
              status: 'Pending',
              priority: 'Stat',
              patientId: 11,
              patientName: 'Test Ward Patient',
            ),
          ],
        ),
      );
      expect(find.text('My nurse profile'), findsOneWidget);
      expect(find.text('Test Nurse'), findsWidgets);
      expect(find.text('Morning · Ward A'), findsOneWidget);
      expect(
        find.text('Needs attention on the ward', skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.textContaining('Synthetic Ceftriaxone', skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.textContaining('Test Bedless Patient', skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.textContaining('Synthetic hourly vitals', skipOffstage: false),
        findsWidgets,
      );
      expect(
        find.textContaining('no inbox for staff', skipOffstage: false),
        findsOneWidget,
      );
    });

    testWidgets('a missing nurse profile is said plainly, not invented', (
      tester,
    ) async {
      final repo = FakeNursingRepository()..profile = null;
      await pumpNurse(tester, '/', repository: repo);
      expect(find.textContaining('No nurse profile is linked'), findsOneWidget);
    });

    testWidgets('is shown in Hindi', (tester) async {
      await pumpNurse(tester, '/', language: AppLanguage.hi);
      expect(find.text('मेरी नर्स प्रोफ़ाइल'), findsOneWidget);
    });

    testWidgets('other roles do not get the nurse panel', (tester) async {
      await pumpNurse(tester, '/', session: nurseSession(role: 'Receptionist'));
      expect(find.text('My nurse profile'), findsNothing);
    });
  });

  group('ward patients', () {
    testWidgets('lists stays and assignments, searches and filters', (
      tester,
    ) async {
      await pumpNurse(
        tester,
        '/nurses',
        repository: FakeNursingRepository(
          admissionRows: const [
            stay,
            Admission(
              id: 4,
              status: 'Admitted',
              patientId: 12,
              patientName: 'Test Bedless Patient',
            ),
          ],
          patientDutyRows: const [
            DutyAssignment(
              id: 1,
              shift: 'Night',
              patientId: 13,
              patientName: 'Test Assigned Patient',
            ),
          ],
        ),
      );
      expect(find.text('Test Ward Patient'), findsOneWidget);
      expect(find.text('Test Bedless Patient'), findsOneWidget);
      expect(find.text('Test Assigned Patient'), findsOneWidget);

      await tapVisible(
        tester,
        find.widgetWithText(ChoiceChip, 'Assigned to me'),
      );
      expect(find.text('Test Ward Patient'), findsNothing);
      expect(find.text('Test Assigned Patient'), findsOneWidget);

      await tapVisible(tester, find.widgetWithText(ChoiceChip, 'All'));
      await tester.enterText(find.byType(TextField).first, 'b4');
      await tester.pumpAndSettle();
      expect(find.text('Test Ward Patient'), findsOneWidget);
      expect(find.text('Test Bedless Patient'), findsNothing);
    });

    testWidgets('an empty duty explains where patients come from', (
      tester,
    ) async {
      await pumpNurse(tester, '/nurses', repository: FakeNursingRepository());
      expect(find.text('No patients on your duty'), findsOneWidget);
    });

    testWidgets('a failed load shows an error with retry', (tester) async {
      final repo = FakeNursingRepository()
        ..readError = const ApiException(kind: ApiErrorKind.network);
      await pumpNurse(tester, '/nurses', repository: repo);
      expect(find.text('Try again'), findsOneWidget);
      repo.readError = null;
      repo.admissionRows = const [stay];
      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();
      expect(find.text('Test Ward Patient'), findsOneWidget);
    });

    testWidgets('a receptionist keeps the placeholder at /nurses', (
      tester,
    ) async {
      await pumpNurse(
        tester,
        '/nurses',
        session: nurseSession(role: 'Receptionist'),
      );
      expect(find.textContaining('not in the mobile app yet'), findsOneWidget);
    });
  });

  group('ward record', () {
    testWidgets('shows identity and stay; saves vitals on the stay once', (
      tester,
    ) async {
      final repo = await pumpNurse(tester, '/nurses/patients/11');
      expect(find.text('Test Ward Patient'), findsWidgets);
      expect(find.textContaining('UH-0011'), findsWidgets);
      expect(find.text('Ward A · Bed B4'), findsOneWidget);

      // Validation: half a blood pressure is refused before sending.
      await enter(
        tester,
        find.byKey(const ValueKey('ward-vital-systolic_bp')),
        '120',
      );
      await tapVisible(tester, find.byKey(const Key('save-ward-vitals')));
      expect(
        find.textContaining('both systolic and diastolic'),
        findsOneWidget,
      );
      expect(repo.savedWardVitals, isEmpty);

      await enter(
        tester,
        find.byKey(const ValueKey('ward-vital-diastolic_bp')),
        '80',
      );
      await enter(
        tester,
        find.byKey(const ValueKey('ward-vital-heart_rate')),
        '72',
      );
      repo.gate = Completer<void>();
      final save = find.byKey(const Key('save-ward-vitals'));
      await tester.ensureVisible(save);
      await tester.tap(save);
      await tester.pump();
      await tester.tap(save, warnIfMissed: false); // a second tap while saving
      await tester.pump();
      expect(repo.savedWardVitals, hasLength(1));
      repo.gate!.complete();
      await tester.pumpAndSettle();
      expect(repo.savedWardVitals.single, {'bp': '120/80', 'pulse': '72'});
      expect(find.text('Vitals saved by the hospital system.'), findsOneWidget);
      expect(find.textContaining('Blood pressure: 120/80'), findsOneWidget);
    });

    testWidgets(
      'earlier vitals show on first open, without Try again (BUG-08)',
      (tester) async {
        final repo = wardRepo()
          ..assessmentRows = [
            NursingAssessment(
              id: 501,
              type: NursingAssessment.vitalsType,
              patientId: testPatient.id,
              admissionId: stay.id,
              vitals: const {'pulse': '88'},
              nurseName: 'Synthetic Nurse',
              assessedAt: DateTime(2026, 11, 15, 8),
            ),
          ];
        await pumpNurse(tester, '/nurses/patients/11', repository: repo);
        await tester.pumpAndSettle();
        expect(find.textContaining('88', skipOffstage: false), findsWidgets);
        expect(find.text('Something went wrong. Try again.'), findsNothing);
      },
    );

    testWidgets('signing out on a ward record opens the start page (BUG-09)', (
      tester,
    ) async {
      await pumpNurse(tester, '/nurses/patients/11');
      final menu = find.byWidgetPredicate(
        (w) => w is Tooltip && (w.message ?? '').startsWith('Profile menu for'),
      );
      await tester.tap(menu.first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Logout'));
      await tester.pumpAndSettle();
      expect(find.text('Your care, organised in one place'), findsOneWidget);
      expect(
        find.text('Your session has ended. Please sign in again.'),
        findsNothing,
      );
    });

    testWidgets('a typed 37.1 is saved as 37.1 (finding 7)', (tester) async {
      final repo = await pumpNurse(tester, '/nurses/patients/11');
      await enter(
        tester,
        find.byKey(const ValueKey('ward-vital-temperature')),
        '37.1',
      );
      await tapVisible(tester, find.byKey(const Key('save-ward-vitals')));
      expect(repo.savedWardVitals.single, {'temperature': '37.1'});
      expect(find.textContaining('37.1'), findsWidgets);
    });

    testWidgets(
      'the MAR names the ordering doctor, never a login (finding 1)',
      (tester) async {
        final repo = wardRepo()
          ..orderRows = [
            MedicationOrder(
              id: 2,
              medicineName: 'Synthetic Paracetamol',
              isActive: true,
              dose: '500 mg',
              route: 'Oral',
              frequency: 'TID',
              orderedByName: 'Dr Synthetic Mehta',
              doses: [dueDose],
            ),
            const MedicationOrder(
              id: 3,
              medicineName: 'Synthetic Ondansetron',
              isActive: true,
              frequency: 'TID',
            ),
          ];
        await pumpNurse(tester, '/nurses/patients/11', repository: repo);
        expect(
          find.textContaining(
            'Ordered by: Dr Synthetic Mehta',
            skipOffstage: false,
          ),
          findsOneWidget,
        );
        // An order without a name shows no "Ordered by" line, and no crash.
        expect(
          find.textContaining('Ordered by:', skipOffstage: false),
          findsOneWidget,
        );
      },
    );

    testWidgets('server-side limits show next to the field', (tester) async {
      final repo = await pumpNurse(tester, '/nurses/patients/11');
      await enter(tester, find.byKey(const ValueKey('ward-vital-spo2')), '120');
      await tapVisible(tester, find.byKey(const Key('save-ward-vitals')));
      expect(find.text('Above the allowed maximum.'), findsOneWidget);
      expect(repo.savedWardVitals, isEmpty);
    });

    testWidgets('a note is saved and appears; notes are never editable', (
      tester,
    ) async {
      final repo = await pumpNurse(tester, '/nurses/patients/11');
      await tapVisible(tester, find.byKey(const Key('save-nursing-note')));
      expect(find.text('Write the note first.'), findsOneWidget);
      await enter(
        tester,
        find.descendant(
          of: find.byKey(const Key('note-text')),
          matching: find.byType(TextField),
        ),
        'Synthetic: comfortable, no pain.',
      );
      await tapVisible(tester, find.byKey(const Key('save-nursing-note')));
      expect(repo.savedNotes.single.type, 'Progress');
      expect(repo.savedNotes.single.admissionId, 3);
      expect(find.text('Synthetic: comfortable, no pain.'), findsOneWidget);
      expect(find.textContaining('cannot be edited'), findsOneWidget);
    });

    testWidgets(
      'a dose is confirmed against the patient, then shown as given',
      (tester) async {
        final repo = await pumpNurse(tester, '/nurses/patients/11');
        await tapVisible(tester, find.byKey(const Key('dose-9-administer')));
        expect(find.text('Record this dose as given?'), findsOneWidget);
        expect(find.textContaining('UH-0011'), findsWidgets);
        expect(find.text('500 mg'), findsWidgets);

        await tapVisible(tester, find.text('Cancel'));
        expect(repo.recordedDoses, isEmpty);

        await tapVisible(tester, find.byKey(const Key('dose-9-administer')));
        await tapVisible(tester, find.byKey(const Key('confirm-dose')));
        expect(repo.recordedDoses.single.action.name, 'administer');
        expect(
          find.textContaining('confirmed by the hospital system'),
          findsOneWidget,
        );
        expect(find.byKey(const Key('dose-9-administer')), findsNothing);
      },
    );

    testWidgets('holding a dose needs a reason', (tester) async {
      final repo = await pumpNurse(tester, '/nurses/patients/11');
      await tapVisible(tester, find.byKey(const Key('dose-9-hold')));
      final confirm = tester.widget<Widget>(
        find.byKey(const Key('confirm-dose')),
      );
      expect(confirm, isNotNull);
      await tester.tap(
        find.byKey(const Key('confirm-dose')),
        warnIfMissed: false,
      );
      await tester.pumpAndSettle();
      expect(repo.recordedDoses, isEmpty);
      await tester.enterText(
        find.byKey(const Key('dose-reason')),
        'Nil by mouth',
      );
      await tester.pump();
      await tapVisible(tester, find.byKey(const Key('confirm-dose')));
      expect(repo.recordedDoses.single.reason, 'Nil by mouth');
    });

    testWidgets('a dose refused by the server is not shown as given', (
      tester,
    ) async {
      final repo = wardRepo()
        ..writeError = const ApiException(
          kind: ApiErrorKind.validation,
          statusCode: 400,
        );
      await pumpNurse(tester, '/nurses/patients/11', repository: repo);
      await tapVisible(tester, find.byKey(const Key('dose-9-administer')));
      await tapVisible(tester, find.byKey(const Key('confirm-dose')));
      expect(find.textContaining('This dose was not recorded'), findsOneWidget);
      expect(find.byKey(const Key('dose-9-administer')), findsOneWidget);
      expect(
        find.textContaining('confirmed by the hospital system'),
        findsNothing,
      );
    });

    testWidgets(
      'a patient outside the nurse\'s care shows the server refusal',
      (tester) async {
        final repo = wardRepo()
          ..readError = const ApiException(
            kind: ApiErrorKind.notFound,
            statusCode: 404,
          );
        await pumpNurse(tester, '/nurses/patients/11', repository: repo);
        expect(find.text('Try again'), findsOneWidget);
        expect(find.text('Test Ward Patient'), findsNothing);
      },
    );

    testWidgets('fits a small phone without overflow', (tester) async {
      await pumpApp(
        tester,
        testServices(session: nurseSession(), nursing: wardRepo()),
        size: smallPhoneSize,
        location: '/nurses/patients/11',
      );
      expect(tester.takeException(), isNull);
    });
  });

  group('H-10 as-needed (PRN) doses', () {
    MedicationOrder prnOrder({int? interval = 240, int? max = 3}) =>
        MedicationOrder(
          id: 4,
          medicineName: 'Synthetic Ibuprofen',
          isActive: true,
          dose: '400 mg',
          route: 'Oral',
          frequency: 'PRN',
          prnMinIntervalMinutes: interval,
          prnMaxDosesPer24h: max,
        );

    FakeNursingRepository prnRepo({int? interval = 240, int? max = 3}) =>
        FakeNursingRepository(
          patients: const [testPatient],
          admissionRows: const [stay],
          orderRows: [
            orderWith([dueDose]),
            prnOrder(interval: interval, max: max),
          ],
        );

    testWidgets('a PRN dose is confirmed against the patient and recorded', (
      tester,
    ) async {
      final repo = await pumpNurse(
        tester,
        '/nurses/patients/11',
        repository: prnRepo(),
      );
      expect(
        find.textContaining('At least 4 h between doses · At most 3 doses'),
        findsOneWidget,
      );
      // Only the as-needed order offers Give dose.
      expect(find.byKey(const Key('prn-4')), findsOneWidget);
      expect(find.byKey(const Key('prn-2')), findsNothing);

      await tapVisible(tester, find.byKey(const Key('prn-4')));
      expect(find.text('Give this as-needed dose now?'), findsOneWidget);
      expect(find.textContaining('UH-0011'), findsWidgets);
      await tapVisible(tester, find.text('Cancel'));
      expect(repo.prnDoses, isEmpty);

      await tapVisible(tester, find.byKey(const Key('prn-4')));
      await tester.enterText(find.byKey(const Key('prn-notes')), 'Pain 6/10');
      await tapVisible(tester, find.byKey(const Key('confirm-prn')));
      expect(repo.prnDoses.single, (order: 4, notes: 'Pain 6/10'));
      expect(
        find.textContaining('confirmed by the hospital system'),
        findsOneWidget,
      );
    });

    testWidgets('a dose too soon is refused in the order\'s own words', (
      tester,
    ) async {
      final repo = prnRepo()
        ..writeError = const ApiException(
          kind: ApiErrorKind.conflict,
          statusCode: 409,
          flags: {'prn_min_interval', 'prn_limit'},
        );
      await pumpNurse(tester, '/nurses/patients/11', repository: repo);
      await tapVisible(tester, find.byKey(const Key('prn-4')));
      await tapVisible(tester, find.byKey(const Key('confirm-prn')));
      expect(
        find.textContaining('too soon after the last dose'),
        findsOneWidget,
      );
      expect(find.textContaining('one dose every 4 h'), findsOneWidget);
      expect(
        find.textContaining('confirmed by the hospital system'),
        findsNothing,
      );
    });

    testWidgets('a dose over the daily maximum is refused', (tester) async {
      final repo = prnRepo()
        ..writeError = const ApiException(
          kind: ApiErrorKind.conflict,
          statusCode: 409,
          flags: {'prn_max_per_24h', 'prn_limit'},
        );
      await pumpNurse(tester, '/nurses/patients/11', repository: repo);
      await tapVisible(tester, find.byKey(const Key('prn-4')));
      await tapVisible(tester, find.byKey(const Key('confirm-prn')));
      expect(
        find.textContaining('at most 3 doses in 24 hours'),
        findsOneWidget,
      );
    });

    testWidgets('an order without limits says so', (tester) async {
      await pumpNurse(
        tester,
        '/nurses/patients/11',
        repository: prnRepo(interval: null, max: null),
      );
      expect(find.text('No dose limits set by the doctor'), findsOneWidget);
    });
  });

  group('H-10 PRN helpers', () {
    test('as-needed words match the server', () {
      for (final f in ['PRN', 'sos', 'PRN Q6H', 'as needed']) {
        expect(isPrnFrequency(f), isTrue, reason: f);
      }
      for (final f in ['TID', 'Q8H', '', null]) {
        expect(isPrnFrequency(f), isFalse, reason: '$f');
      }
    });

    test('the interval is shown in hours', () {
      expect(prnIntervalHours(240), '4');
      expect(prnIntervalHours(90), '1.5');
      expect(prnIntervalHours(20), '0.33');
    });
  });
}
