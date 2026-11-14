import 'package:flutter/material.dart';

import 'dart:ui' show Tristate;

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/features/navigation/sidebar.dart';

import '../../support/test_app.dart';

void main() {
  testWidgets('phone: the drawer opens from the header and closes again', (
    tester,
  ) async {
    await pumpApp(tester, testServices());
    expect(find.byType(Sidebar), findsNothing);

    await tester.tap(find.byTooltip('Open navigation'));
    await tester.pumpAndSettle();

    expect(find.byType(Sidebar), findsOneWidget);
    expect(find.text('FRONT DESK'), findsOneWidget);
    expect(
      find.text('ADMINISTRATION'),
      findsNothing,
      reason: 'visitors never see Administration',
    );

    await tester.tap(find.byTooltip('Close navigation'));
    await tester.pumpAndSettle();

    expect(find.byType(Sidebar), findsNothing);
  });

  testWidgets(
    'phone: choosing a module navigates, closes the drawer and asks a visitor to sign in',
    (tester) async {
      await pumpApp(tester, testServices());
      await tester.tap(find.byTooltip('Open navigation'));
      await tester.pumpAndSettle();

      await tester.tap(
        find.descendant(
          of: find.byType(Sidebar),
          matching: find.text('Patients'),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(Sidebar), findsNothing);
      expect(find.text('Sign-in required'), findsOneWidget);
      expect(
        find.text('Sign in with a staff account that may open Patients.'),
        findsOneWidget,
      );
      // Breadcrumbs: Home › Front desk › Patients
      expect(find.text('Front desk'), findsOneWidget);

      await tester.tap(find.text('Home'));
      await tester.pumpAndSettle();
      expect(find.text('Your care, organised in one place'), findsOneWidget);
    },
  );

  testWidgets('the current page is highlighted in the sidebar', (tester) async {
    await pumpApp(tester, testServices(), location: '/queue');
    await tester.tap(find.byTooltip('Open navigation'));
    await tester.pumpAndSettle();

    final queue = tester.getSemantics(find.bySemanticsLabel('Queue').last);
    final home = tester.getSemantics(find.bySemanticsLabel('Home').last);
    expect(queue.flagsCollection.isSelected, Tristate.isTrue);
    expect(home.flagsCollection.isSelected, isNot(Tristate.isTrue));
  });

  testWidgets(
    'tablet: a persistent icon rail, and the menu button opens the full drawer',
    (tester) async {
      await pumpApp(tester, testServices(), size: tabletSize);

      final rail = tester.getSize(find.byType(Sidebar));
      expect(rail.width, 72);

      await tester.tap(find.byTooltip('Open navigation'));
      await tester.pumpAndSettle();
      expect(find.text('FRONT DESK'), findsOneWidget);
    },
  );

  testWidgets(
    'desktop: full sidebar without a menu button, collapsible to the rail',
    (tester) async {
      await pumpApp(tester, testServices(), size: desktopSize);

      expect(find.byTooltip('Open navigation'), findsNothing);
      expect(tester.getSize(find.byType(Sidebar)).width, 256);

      await tester.tap(find.byTooltip('Collapse sidebar'));
      await tester.pumpAndSettle();

      expect(tester.getSize(find.byType(Sidebar)).width, 72);
    },
  );

  testWidgets('signed-in staff see only the modules their role may view', (
    tester,
  ) async {
    final services = testServices(
      session: staffSession(
        role: 'Lab Staff',
        permissions: {'Dashboard.View', 'Laboratory.View'},
      ),
    );
    await pumpApp(tester, services);
    await tester.tap(find.byTooltip('Open navigation'));
    await tester.pumpAndSettle();

    expect(find.text('Laboratory'), findsOneWidget);
    expect(find.text('Patients'), findsNothing);
    expect(find.text('Billing'), findsNothing);
  });

  testWidgets('the language switch stays compact, not header-tall', (
    tester,
  ) async {
    // Regression: seen on the emulator, the toggle filled the 64 px header.
    await pumpApp(tester, testServices());

    expect(tester.getSize(find.text('EN')).height, lessThan(20));
    final option = find
        .ancestor(of: find.text('EN'), matching: find.byType(InkWell))
        .first;
    expect(tester.getSize(option).height, 32);
  });

  testWidgets('the header language switch turns the interface Hindi', (
    tester,
  ) async {
    final services = testServices();
    await pumpApp(tester, services);

    await tester.tap(find.text('हिं'));
    await tester.pumpAndSettle();

    expect(services.locale.language, AppLanguage.hi);
    expect(find.text('आपकी देखभाल, एक ही जगह व्यवस्थित'), findsOneWidget);
    expect(find.text('स्टाफ़ साइन इन'), findsWidgets);
  });

  testWidgets('search finds a page and opens it', (tester) async {
    await pumpApp(tester, testServices());

    await tester.tap(find.byTooltip('Jump to a page'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'pharm');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Pharmacy').last);
    await tester.pumpAndSettle();

    expect(
      find.text('Sign in with a staff account that may open Pharmacy.'),
      findsOneWidget,
    );
  });

  testWidgets('the hospital switcher explains a visitor has no hospitals', (
    tester,
  ) async {
    await pumpApp(tester, testServices());

    await tester.tap(find.bySemanticsLabel('Hospital: Select Hospital'));
    await tester.pumpAndSettle();

    expect(
      find.text('You are not a member of any hospital yet.'),
      findsOneWidget,
    );
  });

  testWidgets(
    'the header Staff sign in button opens the staff sign-in screen',
    (tester) async {
      await pumpApp(tester, testServices());

      await tester.tap(find.text('Staff sign in').first);
      await tester.pumpAndSettle();

      expect(find.text('STAFF PORTAL'), findsOneWidget);
      expect(find.text('Use your hospital staff account.'), findsOneWidget);
    },
  );

  testWidgets('an unknown path falls back to Home', (tester) async {
    await pumpApp(tester, testServices(), location: '/no-such-page');

    expect(find.text('Your care, organised in one place'), findsOneWidget);
  });
}
