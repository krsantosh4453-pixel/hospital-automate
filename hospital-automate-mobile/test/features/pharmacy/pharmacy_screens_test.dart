import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/theme/app_colors.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';
import 'package:hms_mobile/features/pharmacy/data/pharmacy_models.dart';

import '../../support/test_app.dart';

// Synthetic data only.
const pharmacyPermissions = {
  'Dashboard.View',
  'Pharmacy.View',
  'Prescriptions.View',
  'Inventory.View',
  'Compounders.View',
};

SessionState pharmacySession({String role = 'Pharmacist'}) => SessionState(
  user: const SessionUser(id: 92, displayName: 'pharm.test', firstName: 'Test'),
  hospitals: [
    HospitalContext(
      id: 1,
      name: 'Test General Hospital',
      role: role,
      permissions: pharmacyPermissions,
    ),
  ],
  activeHospitalId: 1,
);

const rx = Prescription(
  id: 3,
  status: 'Confirmed',
  patientName: 'Test Pharmacy Patient',
  patientUhid: 'UH-0042',
  doctorName: 'Dr Test',
  items: [
    PrescriptionItem(
      id: 7,
      name: 'Paracip 500',
      dosage: '500 mg',
      frequency: 'TID',
      duration: '5 days',
      quantity: 10,
      dispensedQuantity: 0,
    ),
  ],
);

final stock = [
  Medicine(
    id: 1,
    name: 'Paracip 500',
    quantity: 50,
    batch: 'PB1',
    expiryDate: DateTime(2030, 1, 1),
    genericName: 'Paracetamol',
    reorderLevel: 10,
  ),
  const Medicine(
    id: 5,
    name: 'Calpol 500',
    quantity: 30,
    batch: 'CB1',
    genericName: 'Paracetamol',
    reorderLevel: 10,
  ),
];

FakePharmacyRepository pharmacyRepo() => FakePharmacyRepository(
  stock: stock,
  prescriptionRows: const [rx],
  dispenseResult: const DispenseResult(
    prescriptionId: 3,
    status: 'Dispensed',
    remaining: {7: 0},
    sales: [],
    invoiceNumber: 'INV-TEST-1',
    invoiceTotal: 40,
  ),
);

Future<FakePharmacyRepository> pumpPharmacy(
  WidgetTester tester,
  String location, {
  FakePharmacyRepository? repository,
  SessionState? session,
  AppLanguage language = AppLanguage.en,
}) async {
  final repo = repository ?? pharmacyRepo();
  await pumpApp(
    tester,
    testServices(
      session: session ?? pharmacySession(),
      pharmacy: repo,
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

void main() {
  group('pharmacy home', () {
    testWidgets('shows server stock counts and the pending queue', (
      tester,
    ) async {
      await pumpPharmacy(tester, '/');
      expect(find.text('Medicine batches'), findsOneWidget);
      expect(find.text('40'), findsOneWidget);
      expect(find.text('38'), findsOneWidget); // in stock = 40 − 2
      expect(find.text('Prescriptions to dispense'), findsOneWidget);
      expect(find.textContaining('expires within 30 days'), findsOneWidget);
    });

    testWidgets('a failing part shows "not available", the rest still shows', (
      tester,
    ) async {
      final repo = pharmacyRepo()
        ..readError = const ApiException(kind: ApiErrorKind.server);
      await pumpPharmacy(tester, '/', repository: repo);
      expect(find.text('Medicine batches'), findsOneWidget);
      expect(find.text('Not available right now'), findsWidgets);
    });

    testWidgets('is shown in Hindi', (tester) async {
      await pumpPharmacy(tester, '/', language: AppLanguage.hi);
      expect(find.text('दवा बैच'), findsOneWidget);
    });
  });

  group('pharmacy page', () {
    testWidgets('queue lists prescriptions to dispense and opens one', (
      tester,
    ) async {
      final repo = await pumpPharmacy(tester, '/pharmacy');
      expect(find.textContaining('RX-3'), findsOneWidget);
      expect(repo.queueRequests.first, [
        'Confirmed',
        'Pending',
        'Partially Dispensed',
      ]);
      await tapVisible(tester, find.textContaining('RX-3'));
      expect(find.text('Paracip 500'), findsWidgets);
      expect(find.text('Prescribed 10 · Issued 0 · Left 10'), findsOneWidget);
    });

    testWidgets('medicines view filters by stock level and is read-only', (
      tester,
    ) async {
      final repo = pharmacyRepo()
        ..stock = [
          ...stock,
          const Medicine(
            id: 9,
            name: 'Empty Syrup',
            quantity: 0,
            reorderLevel: 5,
          ),
        ];
      await pumpPharmacy(tester, '/pharmacy', repository: repo);
      await tapVisible(tester, find.text('Medicines'));
      expect(find.text('Empty Syrup'), findsOneWidget);
      expect(find.textContaining('Stock is read-only here'), findsOneWidget);
      await tapVisible(tester, find.widgetWithText(ChoiceChip, 'Out of stock'));
      expect(find.text('Paracip 500'), findsNothing);
      expect(find.text('Empty Syrup'), findsOneWidget);
    });

    testWidgets('a nurse keeps the placeholder at /pharmacy', (tester) async {
      await pumpPharmacy(
        tester,
        '/pharmacy',
        session: pharmacySession(role: 'Nurse'),
      );
      expect(find.textContaining('not in the mobile app yet'), findsOneWidget);
    });
  });

  group('dispensing', () {
    testWidgets(
      'pre-selects a batch, confirms, sends once and shows the result',
      (tester) async {
        final repo = pharmacyRepo()..gate = Completer<void>();
        await pumpPharmacy(
          tester,
          '/pharmacy/prescriptions/3',
          repository: repo,
        );
        expect(find.textContaining('UH-0042'), findsWidgets);
        expect(find.text('In stock'), findsWidgets);

        await tapVisible(tester, find.byKey(const Key('dispense')));
        expect(find.text('Dispense these medicines?'), findsOneWidget);
        expect(
          find.textContaining('Paracip 500 × 10 (Batch PB1)'),
          findsOneWidget,
        );
        await tester.tap(find.text('Dispense').last); // the dialog's confirm
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 500));
        await tester.tap(
          find.byKey(const Key('dispense')),
          warnIfMissed: false,
        ); // again while sending
        await tester.pump();
        expect(repo.dispensed, hasLength(1));
        expect(repo.dispensed.single, {
          'prescription': 3,
          'partial': false,
          'lines': [
            {'item': 7, 'medicine': 1, 'quantity': 10},
          ],
        });
        repo.gate!.complete();
        await tester.pumpAndSettle();
        expect(find.textContaining('Dispensed in full'), findsOneWidget);
        expect(find.textContaining('INV-TEST-1'), findsOneWidget);
      },
    );

    testWidgets('the "At most" hint is readable on the card (finding 2)', (
      tester,
    ) async {
      await pumpPharmacy(tester, '/pharmacy/prescriptions/3');
      final field = tester.widget<TextField>(find.byKey(const Key('qty-7')));
      expect(field.decoration!.helperText, startsWith('At most'));
      expect(field.decoration!.helperStyle!.color, AppColors.onCard);
    });

    testWidgets('more than prescribed is stopped before sending', (
      tester,
    ) async {
      final repo = await pumpPharmacy(tester, '/pharmacy/prescriptions/3');
      await tester.ensureVisible(find.byKey(const Key('qty-7')));
      await tester.enterText(find.byKey(const Key('qty-7')), '11');
      await tester.pump();
      await tapVisible(tester, find.byKey(const Key('dispense')));
      expect(
        find.textContaining('at most 10 can still be issued'),
        findsOneWidget,
      );
      expect(repo.dispensed, isEmpty);
    });

    testWidgets('a server refusal is explained and nothing shows as issued', (
      tester,
    ) async {
      final repo = pharmacyRepo()
        ..writeError = const ApiException(
          kind: ApiErrorKind.conflict,
          statusCode: 409,
        );
      await pumpPharmacy(tester, '/pharmacy/prescriptions/3', repository: repo);
      await tapVisible(tester, find.byKey(const Key('dispense')));
      await tapVisible(tester, find.text('Dispense').last);
      expect(
        find.text('This prescription has already been dispensed.'),
        findsOneWidget,
      );
      expect(find.textContaining('Dispensed in full'), findsNothing);
    });

    testWidgets(
      'a paper prescription awaiting verification cannot be dispensed',
      (tester) async {
        final repo = pharmacyRepo()
          ..prescriptionRows = const [
            Prescription(
              id: 3,
              status: 'Pending Verification',
              items: [
                PrescriptionItem(id: 7, name: 'Paracip 500', quantity: 10),
              ],
            ),
          ];
        await pumpPharmacy(
          tester,
          '/pharmacy/prescriptions/3',
          repository: repo,
        );
        expect(
          find.textContaining('must be verified by a second pharmacist'),
          findsOneWidget,
        );
        expect(find.byKey(const Key('dispense')), findsNothing);
      },
    );

    testWidgets('only a pharmacist is offered a same-salt substitute', (
      tester,
    ) async {
      await pumpPharmacy(tester, '/pharmacy/prescriptions/3');
      await tapVisible(tester, find.byKey(const Key('batch-7')));
      expect(find.textContaining('Substitute: Calpol 500'), findsWidgets);
      await tester.tapAt(Offset.zero);
      await tester.pumpAndSettle();

      await pumpPharmacy(
        tester,
        '/pharmacy/prescriptions/3',
        session: pharmacySession(role: 'Compounder'),
      );
      await tapVisible(tester, find.byKey(const Key('batch-7')));
      expect(find.textContaining('Substitute: Calpol 500'), findsNothing);
    });

    testWidgets('fits a small phone without overflow', (tester) async {
      await pumpApp(
        tester,
        testServices(session: pharmacySession(), pharmacy: pharmacyRepo()),
        size: smallPhoneSize,
        location: '/pharmacy/prescriptions/3',
      );
      expect(tester.takeException(), isNull);
    });
  });
}
