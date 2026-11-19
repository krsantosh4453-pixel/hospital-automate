// Regression tests for the 2026-11-18 mobile security findings: app-switcher
// privacy, sessions surviving an iOS reinstall, leftover consultation audio,
// and Google sign-in on iOS without a configured client.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/security/privacy_cover.dart';
import 'package:hms_mobile/core/security/token_store.dart';
import 'package:hms_mobile/features/ai/data/scribe_recorder.dart';
import 'package:hms_mobile/features/auth/google_identity.dart';

class _MemoryMarker implements InstallMarker {
  _MemoryMarker([this._set = false]);
  bool _set;

  @override
  Future<bool> isSet() async => _set;

  @override
  Future<void> set() async => _set = true;
}

const _tokens = AuthTokens(
  access: 'synthetic-access',
  refresh: 'synthetic-refresh',
);

void main() {
  group('PrivacyCover', () {
    Future<void> pump(WidgetTester tester) => tester.pumpWidget(
      const MaterialApp(
        home: PrivacyCover(child: Text('Synthetic Patient, MRN 0001')),
      ),
    );

    testWidgets('covers patient data whenever the app leaves the foreground', (
      tester,
    ) async {
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await pump(tester);
      expect(find.byKey(const Key('privacy-cover')), findsNothing);

      // Down to the background and back, as the OS reports it.
      for (final state in [
        AppLifecycleState.inactive,
        AppLifecycleState.hidden,
        AppLifecycleState.paused,
        AppLifecycleState.hidden,
        AppLifecycleState.inactive,
      ]) {
        tester.binding.handleAppLifecycleStateChanged(state);
        await tester.pump();
        expect(
          find.byKey(const Key('privacy-cover')),
          findsOneWidget,
          reason: '$state',
        );
      }

      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      expect(find.byKey(const Key('privacy-cover')), findsNothing);
      expect(find.text('Synthetic Patient, MRN 0001'), findsOneWidget);
    });
  });

  group('forgetSessionFromPreviousInstall', () {
    test(
      'the first start of an install forgets tokens a Keychain kept',
      () async {
        final store = InMemoryTokenStore();
        await store.save(_tokens);
        await store.saveHospitalId(7);
        final marker = _MemoryMarker();

        await forgetSessionFromPreviousInstall(store, marker);

        expect(await store.readAccessToken(), isNull);
        expect(await store.readRefreshToken(), isNull);
        expect(await store.readHospitalId(), isNull);
        expect(await marker.isSet(), isTrue);
      },
    );

    test('later starts keep the signed-in session', () async {
      final store = InMemoryTokenStore();
      await store.save(_tokens);

      await forgetSessionFromPreviousInstall(store, _MemoryMarker(true));

      expect(await store.readAccessToken(), 'synthetic-access');
    });
  });

  group('deleteLeftoverRecordings', () {
    test('removes only scribe recordings', () async {
      final dir = await Directory.systemTemp.createTemp('hms-scribe-test');
      addTearDown(() => dir.delete(recursive: true));
      final leftover = File('${dir.path}/scribe-1731900000000.m4a')
        ..writeAsBytesSync([0, 0, 0, 24]);
      final other = File('${dir.path}/unrelated.m4a')..writeAsBytesSync([1]);

      expect(await deleteLeftoverRecordings(dir), 1);
      expect(leftover.existsSync(), isFalse);
      expect(other.existsSync(), isTrue);
    });

    test('a missing directory is not an error', () async {
      final dir = Directory(
        '${Directory.systemTemp.path}/hms-no-such-dir-${DateTime.now().microsecondsSinceEpoch}',
      );
      expect(await deleteLeftoverRecordings(dir), 0);
    });
  });

  group('PluginGoogleIdentity on iOS', () {
    test(
      'without an iOS client Google sign-in is unavailable instead of raising',
      () async {
        final identity = PluginGoogleIdentity(
          serverClientId: 'synthetic-web.apps.googleusercontent.com',
          iosClientId: '',
          platform: TargetPlatform.iOS,
        );
        expect(identity.configuredForPlatform, isFalse);
        expect(identity.isAvailable, isFalse);
        await expectLater(
          identity.requestIdToken(),
          throwsA(
            isA<GoogleSignInFailure>().having(
              (f) => f.misconfigured,
              'misconfigured',
              isTrue,
            ),
          ),
        );
      },
    );

    test('Android and a configured iOS build need nothing more', () {
      for (final (platform, id) in [
        (TargetPlatform.android, ''),
        (TargetPlatform.iOS, 'synthetic-ios.apps.googleusercontent.com'),
      ]) {
        final identity = PluginGoogleIdentity(
          serverClientId: 'synthetic-web.apps.googleusercontent.com',
          iosClientId: id,
          platform: platform,
        );
        expect(identity.configuredForPlatform, isTrue, reason: '$platform');
      }
    });
  });
}
