import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/dashboard/dashboard_stats.dart';

import '../../support/test_app.dart';

void main() {
  group('DashboardStats.fromJson', () {
    test(
      'reads counts, money and recent patients from the real response shape',
      () {
        final stats = DashboardStats.fromJson(statsJson);

        expect(stats.count('patients', 'today'), 12);
        expect(stats.bedsOccupied, 41);
        expect(stats.money('billing', 'today_revenue'), 18500);
        expect(stats.recentPatients.first.patientId, 'P101');
        expect(
          stats.recentPatients.first.createdAt,
          DateTime.utc(2026, 11, 10, 9, 30),
        );
      },
    );

    test('a missing figure is 0 and withheld money stays null', () {
      final stats = DashboardStats.fromJson({
        'statistics': {
          'billing': {'today_revenue': null},
        },
      });

      expect(stats.count('queue', 'waiting'), 0);
      expect(stats.money('billing', 'today_revenue'), isNull);
      expect(stats.recentPatients, isEmpty);
    });

    test('rejects a body that is not an object', () {
      expect(() => DashboardStats.fromJson([]), throwsFormatException);
    });
  });

  testWidgets('guest home: a locked department says which roles may open it', (
    tester,
  ) async {
    await pumpApp(tester, testServices());

    await tester.scrollUntilVisible(find.text('Wards and beds'), 300);
    await tester.tap(find.text('Wards and beds'));
    await tester.pumpAndSettle();

    expect(find.text('You are not eligible for this work'), findsOneWidget);
    expect(
      find.textContaining('Admin, Doctor, Nurse, Hospital Manager'),
      findsOneWidget,
    );
  });

  testWidgets('staff dashboard: greeting, real figures and attention items', (
    tester,
  ) async {
    final repository = FakeDashboardRepository(
      stats: DashboardStats.fromJson(statsJson),
    );
    await pumpApp(
      tester,
      testServices(session: staffSession(), dashboard: repository),
      size: desktopSize,
    );

    expect(repository.requestedHospitals, [7]);
    expect(find.textContaining(', Asha'), findsOneWidget);
    expect(find.textContaining('Test General Hospital'), findsWidgets);
    expect(find.text('12'), findsOneWidget);
    expect(find.text('1,250 registered in total'), findsOneWidget);
    expect(find.text('Now serving token 17'), findsOneWidget);
    expect(find.text('41 occupied of 50'), findsOneWidget);
    expect(find.text('1 active emergency case'), findsOneWidget);
    expect(find.text('2 urgent lab tests'), findsOneWidget);
    expect(find.text('Test Patient One'), findsOneWidget);
    expect(find.text('₹18,500'), findsOneWidget);
    expect(find.text('Register patient'), findsWidgets);
  });

  testWidgets(
    'staff dashboard: a role home shows only its own tiles and actions',
    (tester) async {
      final repository = FakeDashboardRepository(
        stats: DashboardStats.fromJson(statsJson),
      );
      final session = staffSession(
        role: 'Lab Staff',
        permissions: {'Dashboard.View', 'Laboratory.View'},
      );
      await pumpApp(
        tester,
        testServices(session: session, dashboard: repository),
      );

      expect(find.textContaining('Laboratory today'), findsOneWidget);
      expect(find.text('Lab tests pending'), findsOneWidget);
      expect(find.text('Patients registered today'), findsNothing);
      expect(find.text('Lab worklist'), findsOneWidget);
      expect(find.text('Create invoice'), findsNothing);
    },
  );

  testWidgets(
    'staff dashboard: a failed load shows a safe message and retries',
    (tester) async {
      final repository = FakeDashboardRepository(
        error: const ApiException(
          kind: ApiErrorKind.forbidden,
          statusCode: 403,
        ),
      );
      await pumpApp(
        tester,
        testServices(session: staffSession(), dashboard: repository),
      );

      expect(
        find.text('Dashboard figures could not be loaded'),
        findsOneWidget,
      );
      expect(
        find.text(
          'Your role does not have access to this in the selected hospital.',
        ),
        findsOneWidget,
      );

      repository
        ..error = null
        ..stats = DashboardStats.fromJson(statsJson);
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();

      expect(find.text('Dashboard figures could not be loaded'), findsNothing);
      expect(repository.requestedHospitals, [7, 7]);
    },
  );
}
