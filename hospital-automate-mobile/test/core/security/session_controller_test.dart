import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/core/security/token_store.dart';

import '../../support/test_app.dart';

void main() {
  test('a signed-out session can view nothing', () {
    const state = SessionState.signedOut;

    expect(state.isSignedIn, isFalse);
    expect(state.canView(null), isFalse);
    expect(state.canView('Patients'), isFalse);
  });

  test(
    'canView follows the server permissions of the active hospital only',
    () {
      final state = staffSession(
        role: 'Receptionist',
        permissions: {'Patients.View', 'Billing.Add'},
      );

      expect(state.canView(null), isTrue);
      expect(state.canView('Patients'), isTrue);
      expect(
        state.canView('Billing'),
        isFalse,
        reason: 'Add without View does not open the module',
      );
      expect(state.canView('Laboratory'), isFalse);
    },
  );

  test(
    'sign-out clears tokens, the session and every registered cache',
    () async {
      final tokens = InMemoryTokenStore();
      await tokens.save(const AuthTokens(access: 'a', refresh: 'r'));
      final session = SessionController(
        tokenStore: tokens,
        initial: staffSession(),
      );
      var cleared = false;
      session.onSignOut(() async => cleared = true);

      await session.signOut();

      expect(session.state.isSignedIn, isFalse);
      expect(cleared, isTrue);
      expect(await tokens.readAccessToken(), isNull);
      expect(await tokens.readRefreshToken(), isNull);
    },
  );

  test('sign-out still clears tokens when a cleanup step fails', () async {
    final tokens = InMemoryTokenStore();
    await tokens.save(const AuthTokens(access: 'a', refresh: 'r'));
    final session = SessionController(
      tokenStore: tokens,
      initial: staffSession(),
    );
    session.onSignOut(() async => throw StateError('cache locked'));

    await expectLater(session.signOut(), throwsStateError);

    expect(await tokens.readAccessToken(), isNull);
  });

  test(
    'start keeps the saved hospital when the person still belongs to it',
    () async {
      final store = InMemoryTokenStore();
      final session = SessionController(tokenStore: store);
      final signedIn = staffSession();
      final twoHospitals = SessionState(
        user: signedIn.user,
        hospitals: const [
          HospitalContext(id: 7, name: 'A'),
          HospitalContext(id: 9, name: 'B'),
        ],
      );

      await session.start(twoHospitals, preferredHospitalId: 9);
      expect(session.activeHospitalId, 9);
      expect(await store.readHospitalId(), 9);

      await session.start(twoHospitals, preferredHospitalId: 42);
      expect(
        session.activeHospitalId,
        7,
        reason: 'a hospital the person left falls back to the first',
      );
    },
  );

  test('switching hospital is remembered; sign-out forgets it', () async {
    final store = InMemoryTokenStore();
    final session = SessionController(tokenStore: store);
    await session.start(
      SessionState(
        user: staffSession().user,
        hospitals: const [
          HospitalContext(id: 7, name: 'A'),
          HospitalContext(id: 9, name: 'B'),
        ],
      ),
    );

    await session.selectHospital(9);
    expect(await store.readHospitalId(), 9);

    await session.signOut();
    expect(await store.readHospitalId(), isNull);
    expect(session.activeHospitalId, isNull);
  });

  test('an expired sign-out is flagged until the next sign-in', () async {
    final session = SessionController(
      tokenStore: InMemoryTokenStore(),
      initial: staffSession(),
    );

    await session.signOut(expired: true);
    expect(session.sessionExpired, isTrue);
    expect(session.status, SessionStatus.signedOut);

    await session.start(staffSession());
    expect(session.sessionExpired, isFalse);
  });

  test('selectHospital ignores hospitals the user is not a member of', () {
    final session = SessionController(
      tokenStore: InMemoryTokenStore(),
      initial: staffSession(),
    );

    session.selectHospital(99);

    expect(session.activeHospitalId, 7);
  });

  test('AuthTokens never prints its values', () {
    expect(
      const AuthTokens(access: 'eyJ.secret', refresh: 'r').toString(),
      isNot(contains('secret')),
    );
  });
}
