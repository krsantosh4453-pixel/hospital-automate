import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/features/dashboard/dashboard_stats.dart';
import 'package:hms_mobile/core/theme/app_spacing.dart';
import 'package:hms_mobile/features/navigation/sidebar.dart';

import '../support/test_app.dart';

/// Every main page at every supported size must lay out without overflow.
/// A RenderFlex overflow is reported as a test failure by flutter_test.
void main() {
  const sizes = {
    'small phone': smallPhoneSize,
    'phone': phoneSize,
    'phone landscape': Size(915, 412),
    'tablet': tabletSize,
    'desktop': desktopSize,
  };
  const pages = ['/', '/patients', '/settings', '/staff-login'];

  for (final size in sizes.entries) {
    for (final page in pages) {
      testWidgets('guest $page lays out on a ${size.key}', (tester) async {
        await pumpApp(tester, testServices(), size: size.value, location: page);

        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('staff dashboard lays out on a ${size.key}', (tester) async {
      final repository = FakeDashboardRepository(
        stats: DashboardStats.fromJson(statsJson),
      );
      await pumpApp(
        tester,
        testServices(session: staffSession(), dashboard: repository),
        size: size.value,
      );

      expect(tester.takeException(), isNull);
    });
  }

  // Regression: on the emulator in landscape the camera-cutout inset
  // squeezed the 72 px icon rail and it overflowed by 32 px.
  testWidgets('landscape with a camera-cutout inset keeps the rail intact', (
    tester,
  ) async {
    tester.view.padding = const FakeViewPadding(left: 48 * 3, top: 24 * 3);
    addTearDown(tester.view.resetPadding);

    await pumpApp(tester, testServices(), size: const Size(914, 411));

    expect(tester.takeException(), isNull);
    expect(
      tester.getSize(find.byType(Sidebar)).width,
      AppDimensions.sidebarRailWidth + 48,
    );
  });

  testWidgets('large text (200%) on a phone still lays out', (tester) async {
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

    await pumpApp(tester, testServices());

    expect(tester.takeException(), isNull);
  });
}
