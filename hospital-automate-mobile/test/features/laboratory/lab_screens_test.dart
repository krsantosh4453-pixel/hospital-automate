import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/dashboard/dashboard_stats.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

import '../../support/test_app.dart';
import 'lab_logic_test.dart' show roleSession;

// Synthetic data only.
const labStaffPermissions = {
  'Dashboard.View',
  'Laboratory.View',
  'Laboratory.Add',
  'Laboratory.Edit',
  'Reports.View',
};

SessionState labStaff() => roleSession('Lab Staff', labStaffPermissions);
SessionState labManager() =>
    roleSession('Hospital Manager', {'Dashboard.View', 'Laboratory.View'});

final labStats = DashboardStats.fromJson(const {
  'statistics': {
    'laboratory': {'total': 42, 'pending': 9, 'completed': 30, 'urgent': 2},
  },
});

List<LabTest> sampleOrders() => [
  LabTest(
    id: 5,
    name: 'Complete Blood Count',
    status: 'Ordered',
    priority: 'Urgent',
    patientName: 'Test Patient One',
    testDate: DateTime(2026, 11, 15),
  ),
  LabTest(
    id: 6,
    name: 'Lipid Profile',
    status: 'Result Entered',
    priority: 'Normal',
    patientName: 'Test Patient Two',
    testDate: DateTime(2026, 11, 14),
    sample: const LabSample(sampleId: 'LAB-SYN-6', sampleType: 'Blood'),
    result: const LabResultData(text: 'Total cholesterol 180 mg/dL'),
  ),
  LabTest(
    id: 7,
    name: 'Thyroid Profile',
    status: 'Released',
    patientName: 'Test Patient Three',
    testDate: DateTime(2026, 11, 10),
  ),
];

Future<FakeLabRepository> pumpLab(
  WidgetTester tester,
  String location, {
  SessionState? session,
  FakeLabRepository? repository,
  AppLanguage language = AppLanguage.en,
}) async {
  final repo = repository ?? FakeLabRepository(tests: sampleOrders());
  await pumpApp(
    tester,
    testServices(
      session: session ?? labStaff(),
      laboratory: repo,
      dashboard: FakeDashboardRepository(stats: labStats),
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

Finder textFieldIn(String key) => find.descendant(
  of: find.byKey(ValueKey(key)),
  matching: find.byType(TextField),
);

void main() {
  group('lab desk', () {
    testWidgets('shows the server counts and the worklist by stage', (
      tester,
    ) async {
      final repo = await pumpLab(tester, '/laboratory');
      expect(find.text('42'), findsOneWidget); // total, from the server
      expect(find.text('9'), findsOneWidget);
      expect(find.text('Complete Blood Count'), findsOneWidget);
      expect(find.text('Lipid Profile'), findsOneWidget);
      expect(repo.statusQueries, isNotEmpty);

      await tapVisible(tester, find.byKey(const Key('lab-queue-inProgress')));
      expect(find.text('Lipid Profile'), findsOneWidget);
      expect(find.text('Complete Blood Count'), findsNothing);
    });

    testWidgets('search narrows by patient or sample number', (tester) async {
      await pumpLab(tester, '/laboratory');
      await tester.enterText(textFieldIn('lab-search'), 'LAB-SYN-6');
      await tester.pumpAndSettle();
      expect(find.text('Lipid Profile'), findsOneWidget);
      expect(find.text('Thyroid Profile'), findsNothing);
    });

    testWidgets('a failed load shows an error with retry', (tester) async {
      final repo = FakeLabRepository(
        tests: sampleOrders(),
        loadError: const ApiException(kind: ApiErrorKind.network),
      );
      await pumpLab(tester, '/laboratory', repository: repo);
      expect(find.text('Try again'), findsWidgets);
      repo.loadError = null;
      await tapVisible(tester, find.text('Try again').first);
      expect(find.text('Complete Blood Count'), findsOneWidget);
    });

    testWidgets('a hospital manager sees the list but no new order', (
      tester,
    ) async {
      await pumpLab(tester, '/laboratory', session: labManager());
      expect(find.text('Complete Blood Count'), findsOneWidget);
      expect(find.byKey(const Key('new-lab-order')), findsNothing);
    });

    testWidgets('doctors keep their own list of ordered tests', (tester) async {
      await pumpApp(
        tester,
        testServices(
          session: roleSession('Doctor', {'Laboratory.View', 'Laboratory.Add'}),
        ),
        location: '/laboratory',
      );
      expect(find.byKey(const Key('lab-find-sample')), findsNothing);
    });

    testWidgets('stage labels are shown in Hindi', (tester) async {
      await pumpLab(tester, '/laboratory', language: AppLanguage.hi);
      expect(find.textContaining('संग्रह बाकी'), findsOneWidget);
      expect(find.text('Complete Blood Count'), findsOneWidget);
    });
  });

  group('order detail', () {
    testWidgets('lab staff collect a sample with what they recorded', (
      tester,
    ) async {
      final repo = await pumpLab(tester, '/laboratory/5');
      await tapVisible(tester, find.byKey(const Key('lab-next-step')));
      expect(find.text('Sample type'), findsOneWidget);
      await tester.enterText(textFieldIn('sample-id'), 'BAR-0042');
      await tapVisible(tester, find.byKey(const Key('lab-step-submit')));

      final sent = repo.steps.single;
      expect(sent.id, 5);
      expect(sent.body['sample_type'], 'Blood');
      expect(sent.body['container_type'], 'EDTA');
      expect(sent.body['sample_id'], 'BAR-0042');
      // Shown as the server now has it (read back after the step).
      expect(find.text('Sample collected'), findsWidgets);
      expect(
        find.textContaining('saved by the hospital system'),
        findsOneWidget,
      );
    });

    testWidgets('verifying asks first and sends nothing when backed out', (
      tester,
    ) async {
      final repo = await pumpLab(tester, '/laboratory/6');
      expect(find.text('Total cholesterol 180 mg/dL'), findsOneWidget);
      expect(find.text('Awaiting verification'), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('lab-next-step')));
      expect(find.textContaining('Verify only after checking'), findsOneWidget);
      await tapVisible(tester, find.text('Cancel').last);
      expect(repo.steps, isEmpty);

      await tapVisible(tester, find.byKey(const Key('lab-next-step')));
      await tapVisible(tester, find.text('Verify result').last);
      expect(repo.steps.single.step.name, 'verify');
    });

    testWidgets('a result cannot be entered empty', (tester) async {
      final repo = FakeLabRepository(
        tests: [
          const LabTest(id: 8, name: 'Blood Sugar', status: 'Processing'),
        ],
      );
      await pumpLab(tester, '/laboratory/8', repository: repo);
      await tapVisible(tester, find.byKey(const Key('lab-next-step')));
      await tapVisible(tester, find.byKey(const Key('lab-step-submit')));
      expect(find.text('Enter the result.'), findsOneWidget);
      expect(repo.steps, isEmpty);
    });

    testWidgets('a step the server refuses says so and reloads', (
      tester,
    ) async {
      final repo = FakeLabRepository(tests: sampleOrders())
        ..failNext = const ApiException(
          kind: ApiErrorKind.validation,
          statusCode: 400,
        );
      await pumpLab(tester, '/laboratory/6', repository: repo);
      await tapVisible(tester, find.byKey(const Key('lab-next-step')));
      await tapVisible(tester, find.text('Verify result').last);
      expect(find.textContaining('refused this step'), findsOneWidget);
    });

    testWidgets('a manager is told the step is for other roles', (
      tester,
    ) async {
      await pumpLab(tester, '/laboratory/5', session: labManager());
      expect(find.byKey(const Key('lab-next-step')), findsNothing);
      expect(find.byKey(const Key('lab-cancel')), findsNothing);
      expect(find.textContaining('cannot do it'), findsOneWidget);
    });

    testWidgets('a released order offers no step and no cancel', (
      tester,
    ) async {
      await pumpLab(tester, '/laboratory/7');
      expect(find.byKey(const Key('lab-next-step')), findsNothing);
      expect(find.byKey(const Key('lab-cancel')), findsNothing);
    });

    testWidgets('cancelling asks first', (tester) async {
      final repo = await pumpLab(tester, '/laboratory/5');
      await tapVisible(tester, find.byKey(const Key('lab-cancel')));
      await tapVisible(tester, find.text('Cancel order').last);
      expect(repo.cancelled, [5]);
    });
  });

  group('new order', () {
    const patient = PatientSummary(
      id: 41,
      name: 'Test Patient Lab',
      uhid: 'UH-41',
      age: 30,
    );

    testWidgets('patient, test and review, then one order only', (
      tester,
    ) async {
      final repo = FakeLabRepository(tests: sampleOrders(), patients: [patient])
        ..gate = Completer<void>();
      await pumpLab(tester, '/laboratory/new', repository: repo);

      await tapVisible(tester, find.byKey(const Key('lab-order-review')));
      expect(find.text('Choose the patient first.'), findsOneWidget);

      await tester.enterText(textFieldIn('record-picker-search'), 'Tes');
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();
      expect(repo.lookups, ['Tes']);
      await tapVisible(tester, find.text('Test Patient Lab'));
      await tapVisible(tester, find.text('Lipid Profile'));
      await tapVisible(tester, find.byKey(const Key('lab-order-review')));
      expect(find.text('UH-41'), findsOneWidget);

      final submit = find.byKey(const Key('lab-order-submit'));
      await tester.ensureVisible(submit);
      await tester.tap(submit);
      await tester.pump();
      await tester.tap(submit, warnIfMissed: false);
      await tester.pump();
      repo.gate!.complete();
      await tester.pumpAndSettle();

      expect(repo.created, hasLength(1));
      expect(repo.created.single.patientId, 41);
      expect(repo.created.single.testName, 'Lipid Profile');
      expect(repo.created.single.hospitalId, 7);
      expect(find.text('Laboratory order'), findsOneWidget); // its detail page
    });

    testWidgets('an unanswered order blocks a second blind attempt', (
      tester,
    ) async {
      final repo = FakeLabRepository(patients: [patient])
        ..failNext = const ApiException(kind: ApiErrorKind.timeout);
      await pumpLab(tester, '/laboratory/new', repository: repo);
      await tester.enterText(textFieldIn('record-picker-search'), 'Test');
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();
      await tapVisible(tester, find.text('Test Patient Lab'));
      await tester.enterText(textFieldIn('lab-order-test-name'), 'Urine R/E');
      await tapVisible(tester, find.byKey(const Key('lab-order-review')));
      await tapVisible(tester, find.byKey(const Key('lab-order-submit')));

      expect(find.textContaining('may have been placed'), findsOneWidget);
      // The submit button is now disabled: tapping it sends nothing.
      await tester.tap(
        find.byKey(const Key('lab-order-submit')),
        warnIfMissed: false,
      );
      await tester.pumpAndSettle();
      expect(
        repo.created,
        isEmpty,
      ); // the failed one never counted, none resent
    });

    testWidgets('a nurse cannot place orders', (tester) async {
      await pumpLab(
        tester,
        '/laboratory/new',
        session: roleSession('Nurse', {'Laboratory.View', 'Laboratory.Edit'}),
      );
      expect(find.byKey(const Key('lab-order-review')), findsNothing);
      expect(
        find.textContaining('cannot place laboratory orders'),
        findsOneWidget,
      );
    });
  });
}
