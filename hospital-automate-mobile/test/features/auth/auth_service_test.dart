import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/core/security/token_store.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_service.dart';

import '../../support/fake_auth_repository.dart';

void main() {
  late FakeAuthRepository repo;
  late InMemoryTokenStore store;
  late SessionController session;
  late AuthService auth;

  setUp(() {
    repo = FakeAuthRepository();
    store = InMemoryTokenStore();
    session = SessionController(tokenStore: store);
    auth = AuthService(
      repository: repo,
      session: session,
      store: store,
      appVersion: '1.0.0+1',
      platform: TargetPlatform.android,
    );
  });

  const unauthorized = ApiException(
    kind: ApiErrorKind.unauthorized,
    statusCode: 401,
    serverMessage: 'Invalid credentials.',
  );

  group('staff sign-in', () {
    test(
      'falls back to password sign-in when the server reports OTP unavailable',
      () async {
        final result = await auth.staffSignIn('dr.test', 'secret');

        expect(result, isA<StaffSignedIn>());
        expect(repo.calls, [
          'staffStartOtp',
          'staffPasswordLogin',
          'meContexts',
          'staffMe',
        ]);
        expect(session.status, SessionStatus.signedIn);
        expect(session.state.user!.displayName, 'Test Doctor');
        expect(session.activeHospitalId, 7);
        expect(session.state.activeRole, 'Doctor');
        expect(await store.readAccessToken(), 'access-1');
        expect(await store.readRefreshToken(), 'refresh-1');
      },
    );

    test(
      'skips the code step when the server has codes off (finding 5)',
      () async {
        repo.loginOptions = const StaffLoginOptions(
          otpRequired: false,
          otpAvailable: false,
        );

        final result = await auth.staffSignIn('dr.test', 'secret');

        expect(result, isA<StaffSignedIn>());
        expect(repo.loginOptionsCalls, 1);
        expect(repo.calls, isNot(contains('staffStartOtp')));
        expect(repo.calls.first, 'staffPasswordLogin');
        expect(session.state.activeRole, 'Doctor');
      },
    );

    test('a wrong password is still refused when codes are off', () async {
      repo
        ..loginOptions = const StaffLoginOptions(
          otpRequired: false,
          otpAvailable: false,
        )
        ..staffPasswordError = unauthorized;

      await expectLater(
        auth.staffSignIn('dr.test', 'bad'),
        throwsA(unauthorized),
      );
      expect(session.status, isNot(SessionStatus.signedIn));
      expect(await store.readAccessToken(), isNull);
    });

    test('a server that requires codes keeps the code step', () async {
      repo
        ..loginOptions = const StaffLoginOptions(
          otpRequired: true,
          otpAvailable: true,
        )
        ..staffStartOtpError = null;

      final result = await auth.staffSignIn('dr.test', 'secret');

      expect(result, isA<StaffOtpNeeded>());
      expect(repo.calls, ['staffStartOtp']);
      expect(session.status, isNot(SessionStatus.signedIn));
    });

    test('unreadable options keep the code-first flow', () async {
      repo.loginOptionsError = const ApiException(kind: ApiErrorKind.network);

      await auth.staffSignIn('dr.test', 'secret');

      expect(repo.calls.first, 'staffStartOtp');
    });

    test('sends device details but no password in what it records', () async {
      await auth.staffSignIn('dr.test', 'secret');

      final body = repo.sent.first;
      expect(body['platform'], 'android');
      expect(body['app_version'], '1.0.0+1');
      expect(body['device_id'], matches(RegExp(r'^[0-9a-f]{32}$')));
      expect(body.values, isNot(contains('secret')));
    });

    test('asks for the SMS code when the server starts OTP', () async {
      repo.staffStartOtpError = null;

      final result = await auth.staffSignIn('dr.test', 'secret');

      expect(result, isA<StaffOtpNeeded>());
      expect((result as StaffOtpNeeded).challenge.maskedPhone, '******3210');
      expect(session.status, SessionStatus.signedOut);
      expect(await store.readAccessToken(), isNull);

      await auth.staffVerifyOtp(result.challenge, '123456');
      expect(session.status, SessionStatus.signedIn);
    });

    test('a wrong password is passed on and stores nothing', () async {
      repo.staffStartOtpError = unauthorized;

      await expectLater(
        auth.staffSignIn('dr.test', 'wrong'),
        throwsA(unauthorized),
      );

      expect(repo.calls, [
        'staffStartOtp',
      ], reason: 'no password fallback for a 401');
      expect(await store.readAccessToken(), isNull);
      expect(session.state.isSignedIn, isFalse);
    });

    test('a wrong SMS code keeps the person signed out', () async {
      repo.staffStartOtpError = null;
      repo.otpVerifyError = const ApiException(
        kind: ApiErrorKind.unauthorized,
        statusCode: 401,
      );
      final result =
          await auth.staffSignIn('dr.test', 'secret') as StaffOtpNeeded;

      await expectLater(
        auth.staffVerifyOtp(result.challenge, '000000'),
        throwsA(isA<ApiException>()),
      );
      expect(session.state.isSignedIn, isFalse);
    });
  });

  group('patient sign-in', () {
    test(
      'phone OTP signs a patient in with their profile and hospitals',
      () async {
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

        final delivery = await auth.patientRequestOtp('9000000001');
        await auth.patientVerifyOtp('9000000001', '123456');

        expect(delivery.printedOnServer, isTrue);
        expect(session.state.isPatient, isTrue);
        expect(session.state.user!.patient!.name, 'Test Patient One');
        expect(
          repo.calls,
          containsAllInOrder([
            'patientRequestOtp',
            'patientVerifyOtp',
            'meContexts',
            'patientMe',
          ]),
        );
      },
    );

    test('an invalid or expired code signs nobody in', () async {
      repo.patientOtpVerifyError = const ApiException(
        kind: ApiErrorKind.unauthorized,
        statusCode: 401,
        serverMessage: 'OTP has expired.',
      );

      await expectLater(
        auth.patientVerifyOtp('9000000001', '123456'),
        throwsA(isA<ApiException>()),
      );
      expect(session.state.isSignedIn, isFalse);
      expect(await store.readAccessToken(), isNull);
    });
  });

  group('completing a sign-in', () {
    test(
      'drops the tokens again when the account view cannot be loaded',
      () async {
        repo.meContextsError = const ApiException(
          kind: ApiErrorKind.server,
          statusCode: 500,
        );

        await expectLater(
          auth.completeSignIn(const AuthTokens(access: 'a', refresh: 'r')),
          throwsA(isA<ApiException>()),
        );
        expect(await store.readAccessToken(), isNull);
      },
    );

    test('refuses accounts the app does not serve (platform staff)', () async {
      repo.contexts = const MeContexts(accountType: null, hospitals: []);

      await expectLater(
        auth.completeSignIn(const AuthTokens(access: 'a', refresh: 'r')),
        throwsA(isA<UnsupportedAccountException>()),
      );
      expect(await store.readRefreshToken(), isNull);
    });
  });

  group('restore after restart', () {
    test('with no stored tokens the app is signed out', () async {
      await auth.restore();

      expect(session.status, SessionStatus.signedOut);
      expect(repo.calls, isEmpty);
    });

    test('stored tokens and hospital come back', () async {
      await store.save(const AuthTokens(access: 'a', refresh: 'r'));
      await store.saveHospitalId(9);

      await auth.restore();

      expect(session.status, SessionStatus.signedIn);
      expect(session.activeHospitalId, 9);
      expect(session.state.activeRole, 'Nurse');
    });

    test('tokens the server refuses are dropped and the person is told the session ended', () async {
      await store.save(const AuthTokens(access: 'a', refresh: 'r'));
      repo.meContextsError = const ApiException(
        kind: ApiErrorKind.unauthorized,
        statusCode: 401,
      );

      await auth.restore();

      expect(session.status, SessionStatus.signedOut);
      expect(session.sessionExpired, isTrue);
      expect(await store.readRefreshToken(), isNull);
    });

    test('an unreachable server keeps the tokens and offers a retry', () async {
      await store.save(const AuthTokens(access: 'a', refresh: 'r'));
      repo.meContextsError = const ApiException(kind: ApiErrorKind.network);

      await auth.restore();

      expect(session.status, SessionStatus.restoreFailed);
      expect(await store.readRefreshToken(), 'r');
    });
  });

  group('sign-out', () {
    test(
      'signs the device out on the server, then clears tokens and hospital',
      () async {
        await auth.staffSignIn('dr.test', 'secret');

        await auth.signOut();

        expect(repo.calls.last, 'logout');
        expect(session.state.isSignedIn, isFalse);
        expect(await store.readAccessToken(), isNull);
        expect(await store.readHospitalId(), isNull);
      },
    );

    test('still clears locally when the server cannot be reached', () async {
      await auth.staffSignIn('dr.test', 'secret');
      repo.logoutError = const ApiException(kind: ApiErrorKind.network);

      await auth.signOut();

      expect(session.state.isSignedIn, isFalse);
      expect(await store.readRefreshToken(), isNull);
    });

    test('revoking this device signs it out here too', () async {
      await auth.staffSignIn('dr.test', 'secret');

      await auth.revokeSession(
        const DeviceSessionInfo(id: 's-1', platform: 'android', current: true),
      );

      expect(repo.calls, contains('revokeSession:s-1'));
      expect(session.state.isSignedIn, isFalse);
    });
  });

  group('token refresh', () {
    test(
      'stores the rotated pair and is shared by concurrent callers',
      () async {
        await store.save(
          const AuthTokens(access: 'old', refresh: 'old-refresh'),
        );

        final outcomes = await Future.wait([
          auth.refresh('old'),
          auth.refresh('old'),
          auth.refresh('old'),
        ]);

        expect(outcomes, everyElement(RefreshOutcome.refreshed));
        expect(repo.calls.where((c) => c == 'refresh'), hasLength(1));
        expect(await store.readAccessToken(), 'access-1');
        expect(await store.readRefreshToken(), 'refresh-1');
      },
    );

    test(
      'a token another request already renewed is not renewed again',
      () async {
        await store.save(const AuthTokens(access: 'new', refresh: 'r'));

        expect(await auth.refresh('old'), RefreshOutcome.refreshed);
        expect(repo.calls, isEmpty);
      },
    );

    test(
      'a refused refresh token is rejected; a network failure is not',
      () async {
        await store.save(const AuthTokens(access: 'old', refresh: 'r'));
        repo.refreshError = const ApiException(
          kind: ApiErrorKind.unauthorized,
          statusCode: 401,
        );
        expect(await auth.refresh('old'), RefreshOutcome.rejected);

        repo.refreshError = const ApiException(kind: ApiErrorKind.network);
        expect(await auth.refresh('old'), RefreshOutcome.failed);
      },
    );

    test('an expired session is signed out and flagged', () async {
      await auth.staffSignIn('dr.test', 'secret');

      await auth.onSessionExpired();

      expect(session.state.isSignedIn, isFalse);
      expect(session.sessionExpired, isTrue);
    });
  });

  group('sign-out closes signed-in requests (finding 6)', () {
    test(
      'closed before the server is told, reopened by the next sign-in',
      () async {
        await auth.staffSignIn('dr.test', 'secret');
        expect(session.isClosing, isFalse);

        bool? closingDuringLogout;
        repo.onLogout = () => closingDuringLogout = session.isClosing;
        await auth.signOut();

        expect(closingDuringLogout, isTrue);
        expect(session.isClosing, isTrue);
        expect(await store.readAccessToken(), isNull);

        await auth.staffSignIn('dr.test', 'secret');
        expect(session.isClosing, isFalse);
        expect(session.status, SessionStatus.signedIn);
      },
    );

    test('a session the server ended closes requests too', () async {
      await auth.staffSignIn('dr.test', 'secret');
      await session.signOut(expired: true);
      expect(session.isClosing, isTrue);
    });
  });
}
