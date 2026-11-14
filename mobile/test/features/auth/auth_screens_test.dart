import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/core/security/token_store.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/dashboard/dashboard_stats.dart';
import 'package:hms_mobile/features/navigation/sidebar.dart';

import '../../support/test_app.dart';

void main() {
  late FakeAuthRepository repo;
  late FakeDashboardRepository dashboard;
  late InMemoryTokenStore store;

  setUp(() {
    repo = FakeAuthRepository();
    dashboard = FakeDashboardRepository(
      stats: DashboardStats.fromJson(statsJson),
    );
    store = InMemoryTokenStore();
  });

  Future<void> openApp(
    WidgetTester tester,
    String location, {
    Size size = phoneSize,
  }) => pumpApp(
    tester,
    testServices(authRepository: repo, dashboard: dashboard, tokenStore: store),
    location: location,
    size: size,
  );

  /// The input under the visible label "[label] *" (all sign-in fields are required).
  Finder input(String label) => find.descendant(
    of: find
        .ancestor(of: find.text('$label *'), matching: find.byType(Column))
        .first,
    matching: find.byType(EditableText),
  );

  Future<void> type(WidgetTester tester, String label, String text) async {
    await tester.enterText(input(label).first, text);
  }

  Future<void> tapButton(WidgetTester tester, String label) async {
    final target = find.text(label).last;
    await tester.ensureVisible(target);
    await tester.tap(target);
    await tester.pumpAndSettle();
  }

  group('staff sign-in', () {
    testWidgets('password sign-in (OTP unavailable) opens the role dashboard', (
      tester,
    ) async {
      await openApp(tester, '/staff-login');
      expect(find.text('STAFF PORTAL'), findsOneWidget);

      await type(tester, 'Username or email', 'dr.test');
      await type(tester, 'Password', 'secret');
      await tapButton(tester, 'Continue');

      expect(
        repo.calls,
        containsAllInOrder([
          'staffStartOtp',
          'staffPasswordLogin',
          'meContexts',
          'staffMe',
        ]),
      );
      expect(
        find.textContaining('Your clinic today'),
        findsOneWidget,
        reason: 'Doctor role home',
      );
      expect(dashboard.requestedHospitals, [7]);
    });

    testWidgets(
      'a wrong password shows the credentials message and stays put',
      (tester) async {
        repo.staffStartOtpError = const ApiException(
          kind: ApiErrorKind.unauthorized,
          statusCode: 401,
          serverMessage: 'Invalid credentials.',
        );
        await openApp(tester, '/staff-login');

        await type(tester, 'Username or email', 'dr.test');
        await type(tester, 'Password', 'wrong');
        await tapButton(tester, 'Continue');

        expect(
          find.text('The username, email or password is not correct.'),
          findsOneWidget,
        );
        expect(
          find.text('Your session has ended. Please sign in again.'),
          findsNothing,
        );
        expect(find.text('STAFF PORTAL'), findsOneWidget);
      },
    );

    testWidgets('when the server sends an SMS code, the code step signs in', (
      tester,
    ) async {
      repo.staffStartOtpError = null;
      await openApp(tester, '/staff-login');

      await type(tester, 'Username or email', 'dr.test');
      await type(tester, 'Password', 'secret');
      await tapButton(tester, 'Continue');

      expect(
        find.text('We sent a 6-digit code to your mobile (******3210).'),
        findsOneWidget,
      );
      await type(tester, '6-digit code', '123456');
      await tapButton(tester, 'Verify and continue');

      expect(repo.calls, contains('staffVerifyOtp'));
      expect(find.textContaining('Your clinic today'), findsOneWidget);
    });

    testWidgets('the menu shows only what the role may view', (tester) async {
      await openApp(tester, '/staff-login');
      await type(tester, 'Username or email', 'dr.test');
      await type(tester, 'Password', 'secret');
      await tapButton(tester, 'Continue');

      await tester.tap(find.byTooltip('Open navigation'));
      await tester.pumpAndSettle();
      final sidebar = find.byType(Sidebar);

      expect(
        find.descendant(of: sidebar, matching: find.text('Patients')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: sidebar, matching: find.text('Queue')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: sidebar, matching: find.text('Billing')),
        findsNothing,
      );
      expect(
        find.descendant(of: sidebar, matching: find.text('ADMINISTRATION')),
        findsNothing,
      );
    });
  });

  group('patient sign-in', () {
    setUp(() {
      repo.contexts = const MeContexts(
        accountType: AccountType.patient,
        hospitals: [
          HospitalContext(
            id: 7,
            name: 'Test General Hospital',
            role: 'Patient',
          ),
        ],
      );
    });

    testWidgets(
      'mobile OTP: request, the development notice, verify, patient home',
      (tester) async {
        await openApp(tester, '/patient-login');

        await type(tester, 'Mobile number', '9000000001');
        await tapButton(tester, 'Send OTP');
        expect(
          find.text(
            'Development server: the code is printed in the server log, not sent by SMS.',
          ),
          findsOneWidget,
        );

        await type(tester, '6-digit code', '123456');
        await tapButton(tester, 'Verify & Continue');

        expect(
          repo.calls,
          containsAllInOrder([
            'patientRequestOtp',
            'patientVerifyOtp',
            'patientMe',
          ]),
        );
        expect(find.text('My profile'), findsOneWidget);
        expect(find.text('Test Patient One'), findsWidgets);

        await tester.tap(find.byTooltip('Open navigation'));
        await tester.pumpAndSettle();
        expect(
          find.descendant(
            of: find.byType(Sidebar),
            matching: find.text('My Bills'),
          ),
          findsOneWidget,
        );
        expect(
          find.descendant(
            of: find.byType(Sidebar),
            matching: find.text('Patients'),
          ),
          findsNothing,
        );
      },
    );

    testWidgets('an expired code is explained', (tester) async {
      repo.patientOtpVerifyError = const ApiException(
        kind: ApiErrorKind.unauthorized,
        statusCode: 401,
        serverMessage: 'OTP has expired.',
      );
      await openApp(tester, '/patient-login');

      await type(tester, 'Mobile number', '9000000001');
      await tapButton(tester, 'Send OTP');
      await type(tester, '6-digit code', '123456');
      await tapButton(tester, 'Verify & Continue');

      expect(
        find.text('The code has expired. Ask for a new one.'),
        findsOneWidget,
      );
    });
  });

  testWidgets('switching hospital in the header reloads the dashboard for it', (
    tester,
  ) async {
    await openApp(tester, '/staff-login', size: desktopSize);
    await type(tester, 'Username or email', 'dr.test');
    await type(tester, 'Password', 'secret');
    await tapButton(tester, 'Continue');

    await tester.tap(find.bySemanticsLabel('Hospital: Test General Hospital'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Test City Clinic').last);
    await tester.pumpAndSettle();

    expect(dashboard.requestedHospitals, [7, 9]);
    expect(await store.readHospitalId(), 9);
    expect(
      find.textContaining('Your ward today'),
      findsOneWidget,
      reason: 'Nurse at the second hospital',
    );
  });

  testWidgets('signing out from the profile menu clears the session', (
    tester,
  ) async {
    await openApp(tester, '/staff-login', size: desktopSize);
    await type(tester, 'Username or email', 'dr.test');
    await type(tester, 'Password', 'secret');
    await tapButton(tester, 'Continue');

    await tester.tap(find.byTooltip('Profile menu for Test Doctor'));
    await tester.pumpAndSettle();
    expect(find.text('Acting as Doctor'), findsWidgets);
    await tester.tap(find.text('Logout'));
    await tester.pumpAndSettle();

    expect(repo.calls.last, 'logout');
    expect(await store.readAccessToken(), isNull);
    expect(find.text('Your care, organised in one place'), findsOneWidget);
  });

  testWidgets('after the server ends a session, sign-in says why', (
    tester,
  ) async {
    final services = testServices(
      authRepository: repo,
      dashboard: dashboard,
      tokenStore: store,
    );
    await services.session.signOut(expired: true);
    await pumpApp(tester, services, location: '/staff-login');

    expect(
      find.text('Your session has ended. Please sign in again.'),
      findsOneWidget,
    );
    expect(services.session.status, SessionStatus.signedOut);
  });
}
