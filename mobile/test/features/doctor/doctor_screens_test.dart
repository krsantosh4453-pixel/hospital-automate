import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/routing/app_router.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/patient/data/appointment_models.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

import '../../support/test_app.dart';

// Synthetic data only.
const doctorPermissions = {
  'Dashboard.View',
  'Patients.View',
  'Appointments.View',
  'Queue.View',
  'Doctors.View',
  'Laboratory.View',
  'Prescriptions.View',
};

SessionState doctorSession({String role = 'Doctor'}) => SessionState(
  user: const SessionUser(id: 90, displayName: 'dr.test', firstName: 'Test'),
  hospitals: [
    HospitalContext(
      id: 1,
      name: 'Test General Hospital',
      role: role,
      permissions: doctorPermissions,
    ),
  ],
  activeHospitalId: 1,
);

const openVisit = Visit(
  id: 5,
  status: Visit.inConsultation,
  patientId: 2,
  patientName: 'Test Patient Two',
  doctorId: 3,
  hospitalId: 1,
  visitType: 'OPD',
);

const waitingToken = QueueToken(
  id: 11,
  tokenNumber: 7,
  status: 'Waiting',
  patientName: 'Test Patient Two',
  visitId: 5,
);

Future<FakeDoctorRepository> pumpDoctor(
  WidgetTester tester,
  String location, {
  FakeDoctorRepository? repository,
  SessionState? session,
}) async {
  final repo = repository ?? FakeDoctorRepository();
  await pumpApp(
    tester,
    testServices(session: session ?? doctorSession(), doctor: repo),
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
  await tester.enterText(field, text);
  await tester.pump();
}

Finder inputOf(String key) => find.descendant(
  of: find.byKey(ValueKey(key)),
  matching: find.byType(TextField),
);

void main() {
  group('dashboard', () {
    testWidgets('shows the doctor profile and today\'s real figures', (
      tester,
    ) async {
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      await pumpDoctor(
        tester,
        '/',
        repository: FakeDoctorRepository(
          tokens: const [
            waitingToken,
            QueueToken(
              id: 12,
              tokenNumber: 5,
              status: 'In Consultation',
              patientName: 'Test Patient One',
            ),
          ],
          appointmentRows: [
            Appointment(
              id: 1,
              status: 'Scheduled',
              date: today,
              time: '10:30',
              patientName: 'Test Patient Two',
            ),
          ],
        ),
      );

      expect(find.text('My doctor profile'), findsOneWidget);
      expect(find.text('Dr Test Doctor'), findsOneWidget);
      expect(find.text('#5'), findsOneWidget); // now serving
      expect(
        find.textContaining('Test Patient Two · Scheduled'),
        findsOneWidget,
      );
      expect(find.textContaining('no inbox for staff'), findsOneWidget);
    });

    testWidgets('an unavailable part says so without hiding the others', (
      tester,
    ) async {
      await pumpDoctor(
        tester,
        '/',
        repository: FakeDoctorRepository(profile: null),
      );

      expect(
        find.textContaining('No doctor profile is linked'),
        findsOneWidget,
      );
      expect(find.text('Nobody waiting'), findsNothing);
      expect(find.text('No appointments today'), findsOneWidget);
    });
  });

  group('role protection', () {
    testWidgets('other staff keep the placeholder at the doctor paths', (
      tester,
    ) async {
      await pumpDoctor(
        tester,
        '/queue',
        session: doctorSession(role: 'Receptionist'),
      );

      expect(find.text('Now serving (0)'), findsNothing);
      expect(find.textContaining('mobile'), findsWidgets);
    });

    test('patients and visitors cannot reach doctor pages', () {
      final patient = SessionState(
        user: const SessionUser(
          displayName: 'p',
          accountType: AccountType.patient,
        ),
        hospitals: const [HospitalContext(id: 1, name: 'H')],
        activeHospitalId: 1,
      );
      expect(redirectFor(patient, '/consultation/5'), '/');
      expect(redirectFor(patient, '/patients/2'), '/');
      expect(
        redirectFor(SessionState.signedOut, '/consultation/5'),
        isNull,
      ); // shows "sign in required"
    });

    test('a doctor without patient access is refused the patient record', () {
      final noPatients = SessionState(
        user: const SessionUser(id: 90, displayName: 'd'),
        hospitals: const [
          HospitalContext(
            id: 1,
            name: 'H',
            role: 'Doctor',
            permissions: {'Queue.View'},
          ),
        ],
        activeHospitalId: 1,
      );
      expect(redirectFor(noPatients, '/patients/2'), startsWith('/?denied='));
    });
  });

  group('queue', () {
    testWidgets('calls a waiting patient and shows the server\'s new status', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/queue',
        repository: FakeDoctorRepository(tokens: const [waitingToken]),
      );

      await tapVisible(tester, find.byKey(const ValueKey('queue-11-call')));

      expect(repo.moves.single.action, QueueAction.call);
      expect(find.text('Called (1)'), findsOneWidget);
    });

    testWidgets('a second tap while a move is running sends nothing more', (
      tester,
    ) async {
      final repo = FakeDoctorRepository(tokens: const [waitingToken])
        ..gate = Completer<void>();
      await pumpDoctor(tester, '/queue', repository: repo);

      final call = find.byKey(const ValueKey('queue-11-call'));
      await tester.ensureVisible(call);
      await tester.tap(call);
      await tester.pump();
      await tester.tap(call, warnIfMissed: false);
      await tester.pump();

      expect(repo.moves, hasLength(1));
      repo.gate!.complete();
      await tester.pumpAndSettle();
    });

    testWidgets('skip asks first and does nothing when cancelled', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/queue',
        repository: FakeDoctorRepository(tokens: const [waitingToken]),
      );

      await tapVisible(tester, find.byKey(const ValueKey('queue-11-skip')));
      expect(find.text('Skip this token?'), findsOneWidget);
      await tapVisible(tester, find.text('Cancel').last);

      expect(repo.moves, isEmpty);
    });

    testWidgets('polling stops in the background and resumes on return', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/queue',
        repository: FakeDoctorRepository(tokens: const [waitingToken]),
      );
      final first = repo.queueCalls;
      await tester.pump(const Duration(seconds: 31));
      await tester.pumpAndSettle();
      expect(repo.queueCalls, first + 1);

      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      await tester.pump(const Duration(seconds: 95));
      await tester.pumpAndSettle();
      expect(repo.queueCalls, first + 1, reason: 'no polling while hidden');

      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpAndSettle();
      expect(repo.queueCalls, first + 2, reason: 'refreshes on return');
    });
  });

  group('patients', () {
    testWidgets('searches only from two letters and opens the record', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/patients',
        repository: FakeDoctorRepository(
          patients: const [
            PatientSummary(id: 2, name: 'Test Patient Two', uhid: 'UH-2'),
          ],
        ),
      );

      await tester.enterText(find.byKey(const Key('patient-search')), 'T');
      await tester.pump(const Duration(milliseconds: 500));
      expect(repo.searches, isEmpty);

      await tester.enterText(find.byKey(const Key('patient-search')), 'Test');
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pumpAndSettle();
      expect(repo.searches, ['Test']);

      await tapVisible(tester, find.text('Test Patient Two'));
      expect(find.text('Patient profile'), findsOneWidget);
    });

    testWidgets('a patient outside the doctor\'s care is refused', (
      tester,
    ) async {
      final repo = FakeDoctorRepository()
        ..readError = const ApiException(
          kind: ApiErrorKind.notFound,
          statusCode: 404,
        );
      await pumpDoctor(tester, '/patients/99', repository: repo);

      expect(find.text('You cannot open this record'), findsOneWidget);
    });
  });

  group('consultation', () {
    FakeDoctorRepository consultation({Visit visit = openVisit}) =>
        FakeDoctorRepository(visitRows: [visit]);

    testWidgets('invalid vitals are refused before anything is sent', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(),
      );

      await enter(tester, inputOf('vital-pain_score'), '11');
      await tapVisible(tester, find.byKey(const Key('save-vitals')));

      expect(repo.savedVitals, isEmpty);
      expect(find.text('Above the allowed maximum.'), findsOneWidget);
    });

    testWidgets('valid vitals are saved and listed from the server', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(),
      );

      await enter(tester, inputOf('vital-temperature'), '36.8');
      await enter(tester, inputOf('vital-heart_rate'), '72');
      await tapVisible(tester, find.byKey(const Key('save-vitals')));

      expect(repo.savedVitals.single, {
        VitalField.temperature: '36.8',
        VitalField.heartRate: '72',
      });
      expect(find.text('Vitals saved by the hospital system.'), findsOneWidget);
    });

    testWidgets('an empty note is refused; a failed save keeps the text', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(),
      );

      await tapVisible(tester, find.byKey(const Key('save-note')));
      expect(find.text('Write at least one part of the note.'), findsOneWidget);
      expect(repo.savedNotes, isEmpty);

      repo.writeError = networkError;
      await enter(tester, inputOf('note-plan'), 'Synthetic plan');
      await tapVisible(tester, find.byKey(const Key('save-note')));
      expect(find.text('Synthetic plan'), findsOneWidget);

      repo.writeError = null;
      await tapVisible(tester, find.byKey(const Key('save-note')));
      expect(repo.savedNotes.last, {NoteSection.plan: 'Synthetic plan'});
    });

    testWidgets('a diagnosis is added; signing asks first', (tester) async {
      final repo = FakeDoctorRepository(
        visitRows: const [openVisit],
        diagnosisRows: const [
          DiagnosisRecord(
            id: 31,
            name: 'Test Diagnosis',
            visitId: 5,
            recordedBy: 90,
          ),
        ],
      );
      await pumpDoctor(tester, '/consultation/5', repository: repo);

      await enter(tester, inputOf('diagnosis-name'), 'Another Test Diagnosis');
      await tapVisible(tester, find.byKey(const Key('save-diagnosis')));
      expect(repo.savedDiagnoses, ['Another Test Diagnosis']);

      await tapVisible(tester, find.text('Sign').first);
      expect(find.text('Sign this record?'), findsOneWidget);
      // The dialog's confirm button is the last "Sign" on screen.
      await tapVisible(tester, find.text('Sign').last);
      expect(repo.signed, [31]);
    });

    testWidgets('a high safety alert needs a reason before saving', (
      tester,
    ) async {
      final repo = FakeDoctorRepository(
        visitRows: const [openVisit],
        alerts: const [
          SafetyAlert(
            type: 'allergy',
            severity: 'high',
            message: 'Synthetic allergy alert',
            medicines: ['Test Med'],
          ),
        ],
      );
      await pumpDoctor(tester, '/consultation/5', repository: repo);

      await enter(tester, inputOf('medicine-name-0'), 'Test Med');
      final save = find.byKey(const Key('save-prescription'));
      await tester.ensureVisible(save);
      await tester.pumpAndSettle();
      await tester.tap(save);
      // The save button keeps its spinner while the review is open, so pump
      // frames (letting the sheet slide in) instead of waiting to settle.
      for (var i = 0; i < 5; i++) {
        await tester.pump(const Duration(milliseconds: 200));
      }
      expect(find.text('Synthetic allergy alert'), findsOneWidget);

      final confirm = find.byKey(const Key('confirm-prescription'));
      await tester.enterText(find.byKey(const Key('override-reason')), 'short');
      await tester.pump();
      // Disabled below 10 characters: the tap reaches the button but does nothing.
      await tester.tap(confirm, warnIfMissed: false);
      await tester.pump();
      expect(
        repo.savedPrescriptions,
        isEmpty,
        reason: 'reason shorter than 10',
      );

      await tester.enterText(
        find.byKey(const Key('override-reason')),
        'Benefit outweighs the risk',
      );
      await tester.pump();
      await tester.tap(confirm);
      await tester.pumpAndSettle();

      expect(
        repo.savedPrescriptions.single.overrideReason,
        'Benefit outweighs the risk',
      );
      expect(find.textContaining('Prescription #601 saved'), findsOneWidget);
    });

    testWidgets('a failed prescription save is retried with the same key', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(),
      );

      // The first try fails (say the answer was lost); the lines stay.
      repo.writeError = networkError;
      await enter(tester, inputOf('medicine-name-0'), 'Test Med');
      await tapVisible(tester, find.byKey(const Key('save-prescription')));
      expect(repo.savedPrescriptions, isEmpty);

      repo.writeError = null;
      await tapVisible(tester, find.byKey(const Key('save-prescription')));
      expect(repo.savedPrescriptions, hasLength(1));
      expect(repo.prescriptionKeys, hasLength(2));
      expect(repo.prescriptionKeys.last, repo.prescriptionKeys.first);

      // A new prescription after a successful save is a new request.
      await enter(tester, inputOf('medicine-name-0'), 'Second Med');
      await tapVisible(tester, find.byKey(const Key('save-prescription')));
      expect(repo.savedPrescriptions, hasLength(2));
      expect(repo.prescriptionKeys.last, isNot(repo.prescriptionKeys.first));
    });

    testWidgets('a prescription without a medicine name is refused', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(),
      );

      await tapVisible(tester, find.byKey(const Key('save-prescription')));

      expect(find.text('Medicine 1: enter the name.'), findsOneWidget);
      expect(repo.savedPrescriptions, isEmpty);
    });

    testWidgets('a closed visit is read-only', (tester) async {
      await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(
          visit: const Visit(
            id: 5,
            status: Visit.completed,
            patientId: 2,
            doctorId: 3,
            hospitalId: 1,
          ),
        ),
      );
      expect(find.byKey(const Key('save-vitals')), findsNothing);
      expect(find.textContaining('This visit is closed'), findsOneWidget);
    });

    testWidgets("another doctor's open visit is read-only", (tester) async {
      await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(
          visit: const Visit(
            id: 5,
            status: Visit.inConsultation,
            patientId: 2,
            doctorId: 99,
            hospitalId: 1,
          ),
        ),
      );
      expect(find.byKey(const Key('save-prescription')), findsNothing);
      expect(find.textContaining("another doctor's visit"), findsOneWidget);
    });

    testWidgets('completing the visit asks first, then saves the status', (
      tester,
    ) async {
      final repo = await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(),
      );

      await tapVisible(tester, find.byKey(const Key('complete-visit')));
      expect(find.text('Complete this consultation?'), findsOneWidget);
      // The dialog's confirm button is the last "Complete consultation" on screen.
      await tapVisible(tester, find.text('Complete consultation').last);

      expect(repo.visitStatuses, [Visit.completed]);
      expect(find.byKey(const Key('save-vitals')), findsNothing);
    });

    testWidgets('a lab test is ordered on the visit', (tester) async {
      final repo = await pumpDoctor(
        tester,
        '/consultation/5',
        repository: consultation(),
      );

      await enter(tester, inputOf('lab-test-name'), 'Synthetic CBC');
      await tapVisible(tester, find.byKey(const Key('order-lab')));

      expect(repo.orderedTests, ['Synthetic CBC']);
      expect(find.text('Synthetic CBC'), findsOneWidget);
    });
  });

  testWidgets('doctor pages lay out at the suite standards', (tester) async {
    for (final (size, scale) in [(phoneSize, 2.0), (smallPhoneSize, 1.0)]) {
      tester.platformDispatcher.textScaleFactorTestValue = scale;
      for (final path in [
        '/',
        '/queue',
        '/appointments',
        '/patients',
        '/consultation',
        '/consultation/5',
        '/prescription',
        '/laboratory',
      ]) {
        await pumpApp(
          tester,
          testServices(
            session: doctorSession(),
            doctor: FakeDoctorRepository(
              visitRows: const [openVisit],
              tokens: const [waitingToken],
            ),
          ),
          size: size,
          location: path,
        );
        expect(
          tester.takeException(),
          isNull,
          reason: '$path at $size ×$scale',
        );
      }
    }
    tester.platformDispatcher.clearTextScaleFactorTestValue();
  });
}
