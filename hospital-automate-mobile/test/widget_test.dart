import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/backend_health.dart';

import 'support/test_app.dart';

void main() {
  testWidgets('starts on the guest home with the header and no figures', (
    tester,
  ) async {
    await pumpApp(tester, testServices());

    expect(find.text('Your care, organised in one place'), findsOneWidget);
    expect(find.text('Staff sign in'), findsWidgets);
    expect(find.text('Sign in to see'), findsNWidgets(4));
    expect(find.text('—'), findsNWidgets(4));
  });

  testWidgets('Settings shows the backend address and a healthy result', (
    tester,
  ) async {
    await pumpApp(tester, testServices(), location: '/settings');

    expect(find.text('http://10.0.2.2:8000'), findsOneWidget);
    expect(find.text('hms-backend is healthy'), findsOneWidget);
  });

  testWidgets(
    'Settings shows why the backend is unreachable and checks again',
    (tester) async {
      var calls = 0;
      final services = testServices(
        checkHealth: () async {
          calls++;
          return const HealthResult(
            reachable: false,
            message: 'Cannot reach the backend.',
          );
        },
      );
      await pumpApp(tester, services, location: '/settings');

      expect(find.text('Cannot reach the backend.'), findsOneWidget);

      await tester.ensureVisible(find.text('Check again'));
      await tester.tap(find.text('Check again'));
      await tester.pumpAndSettle();

      expect(calls, 2);
    },
  );
}
