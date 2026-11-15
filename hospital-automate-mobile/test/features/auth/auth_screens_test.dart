import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/core/security/token_store.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/google_identity.dart';
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

    testWidgets(
      'SMS unavailable: "Verify using Email" opens the email code step',
      (tester) async {
        repo.patientOtpRequestError = const ApiException(
          kind: ApiErrorKind.unavailable,
          statusCode: 503,
          serverMessage: 'SMS OTP service is not configured.',
        );
        await openApp(tester, '/patient-login');

        expect(find.text('Verify using Email'), findsNothing);
        await type(tester, 'Mobile number', '9000000001');
        await tapButton(tester, 'Send OTP');
        await tapButton(tester, 'Verify using Email');

        expect(find.text('Send Email OTP'), findsOneWidget);
        await type(tester, 'Email', 'patient.one@example.test');
        await tapButton(tester, 'Send Email OTP');
        expect(repo.calls, contains('requestEmailOtp'));
        expect(
          find.text(
            'If this email has a patient account, a verification code was sent to it.',
          ),
          findsOneWidget,
        );
      },
    );
  });

  group('Google sign-in', () {
    late FakeGoogleIdentity google;

    setUp(() {
      google = FakeGoogleIdentity();
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

    Future<void> openWithGoogle(WidgetTester tester) => pumpApp(
      tester,
      testServices(
        authRepository: repo,
        dashboard: dashboard,
        tokenStore: store,
        google: google,
      ),
      location: '/patient-login',
      size: phoneSize,
    );

    testWidgets('the Google token signs a patient in', (tester) async {
      await openWithGoogle(tester);
      await tapButton(tester, 'Continue with Google');

      expect(
        repo.calls,
        containsAllInOrder(['googleLogin', 'meContexts', 'patientMe']),
      );
      expect(repo.sent.last['credential'], 'google-id-token');
      expect(repo.sent.last['platform'], 'android');
      expect(find.text('My profile'), findsOneWidget);
    });

    testWidgets('closing Google\'s picker changes nothing', (tester) async {
      google.idToken = null;
      await openWithGoogle(tester);
      await tapButton(tester, 'Continue with Google');

      expect(google.requests, 1);
      expect(repo.calls, isNot(contains('googleLogin')));
      expect(find.text('Continue with Google'), findsOneWidget);
    });

    testWidgets('an unregistered app build is explained', (tester) async {
      google.failure = const GoogleSignInFailure(misconfigured: true);
      await openWithGoogle(tester);
      await tapButton(tester, 'Continue with Google');

      expect(
        find.text(
          'Google sign-in is not set up for this app yet. Use another sign-in method.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('a staff Google account is sent to staff sign-in', (
      tester,
    ) async {
      repo.googleLoginError = const ApiException(
        kind: ApiErrorKind.forbidden,
        statusCode: 403,
        serverMessage: 'Staff accounts must sign in with username, password and the SMS code.',
      );
      await openWithGoogle(tester);
      await tapButton(tester, 'Continue with Google');

      expect(await store.readAccessToken(), isNull);
      expect(find.text('Continue with Google'), findsOneWidget);
    });

    testWidgets('not offered without Google, nor on the Family tab', (
      tester,
    ) async {
      await openApp(tester, '/patient-login');
      expect(find.text('Continue with Google'), findsNothing);

      await openWithGoogle(tester);
      expect(find.text('Continue with Google'), findsOneWidget);
      await tapButton(tester, 'Family');
      expect(find.text('Continue with Google'), findsNothing);
    });
  });

  group('family (proxy) sign-in', () {
    setUp(() {
      repo.contexts = const MeContexts(
        accountType: AccountType.proxy,
        hospitals: [
          HospitalContext(
            id: 7,
            name: 'Test General Hospital',
            role: 'Patient',
          ),
        ],
      );
    });

    Future<void> codeStep(WidgetTester tester) async {
      await openApp(tester, '/patient-login');
      await tapButton(tester, 'Family');
      expect(find.text('Family member or caregiver'), findsOneWidget);
      await type(tester, 'Your mobile number', '9000000002');
      await tapButton(tester, 'Send OTP');
      await type(tester, '6-digit code', '123456');
      await tapButton(tester, 'Verify & Continue');
    }

    testWidgets('one grant: the code opens that patient view-only', (
      tester,
    ) async {
      await codeStep(tester);

      expect(
        repo.calls,
        containsAllInOrder([
          'proxyRequestOtp',
          'proxyVerifyOtp',
          'proxyLogin:41',
          'meContexts',
          'patientMe',
        ]),
      );
      expect(repo.sent.last['ticket'], 'signed-ticket');
      expect(repo.sent.last['platform'], isNotEmpty);
      expect(await store.readAccessToken(), isNotNull);
      expect(find.text('Family member or caregiver'), findsNothing);
    });

    testWidgets('several grants: choose whose records to open', (tester) async {
      repo.proxyGrants = const [
        ProxyGrantChoice(
          id: 41,
          patientName: 'Test Patient One',
          relationship: 'Son',
        ),
        ProxyGrantChoice(
          id: 42,
          patientName: 'Test Patient Two',
          relationship: 'Daughter',
        ),
      ];
      await codeStep(tester);

      expect(find.text('Whose records do you want to view?'), findsOneWidget);
      expect(find.text('You: Daughter'), findsOneWidget);
      await tapButton(tester, 'Test Patient Two');

      expect(repo.calls, contains('proxyLogin:42'));
      expect(repo.calls, isNot(contains('proxyLogin:41')));
    });

    testWidgets('a refused grant is explained and nothing is stored', (
      tester,
    ) async {
      repo.proxyLoginError = const ApiException(
        kind: ApiErrorKind.forbidden,
        statusCode: 403,
        serverMessage:
            'This family access is not available for your mobile number.',
      );
      await codeStep(tester);

      expect(
        find.text(
          'This family access is not available for your mobile number.',
        ),
        findsOneWidget,
      );
      expect(await store.readAccessToken(), isNull);
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
