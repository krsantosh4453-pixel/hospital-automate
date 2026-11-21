import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/features/dashboard/dashboard_stats.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

import '../../support/test_app.dart';
import '../laboratory/lab_logic_test.dart' show roleSession;
import '../laboratory/lab_screens_test.dart' show tapVisible, textFieldIn;
import 'billing_logic_test.dart' show invoiceJson;

// Synthetic data only.
SessionState billingStaff() => roleSession('Billing Staff', {
  'Dashboard.View',
  'Billing.View',
  'Billing.Add',
  'Billing.Edit',
});

SessionState receptionist() => roleSession('Receptionist', {
  'Dashboard.View',
  'Patients.View',
  'Billing.View',
  'Billing.Add',
});

final billingStats = DashboardStats.fromJson(const {
  'statistics': {
    'billing': {
      'total_invoices': 31,
      'paid': 20,
      'pending': 6,
      'partial': 5,
      'total_revenue': 120000.0,
      'today_revenue': 4500.0,
      'refunded': 300.0,
      'outstanding': 17250.5,
    },
  },
});

Invoice openInvoice() => Invoice.fromJson(invoiceJson);

Invoice unpaidInvoice() => Invoice.fromJson({
  ...invoiceJson,
  'id': 13,
  'invoice_number': 'INV/26-27/000013',
  'patient_name': 'Test Patient Other',
  'status': 'Unpaid',
  'payments': <Object?>[],
  'total_paid': '0.00',
  'balance_due': '500.00',
  'total_amount': '500.00',
  'created_at': '2026-10-01T05:00:00Z',
});

Future<FakeBillingRepository> pumpBilling(
  WidgetTester tester,
  String location, {
  SessionState? session,
  FakeBillingRepository? repository,
  AppLanguage language = AppLanguage.en,
}) async {
  final repo =
      repository ??
      FakeBillingRepository(invoices: [openInvoice(), unpaidInvoice()]);
  await pumpApp(
    tester,
    testServices(
      session: session ?? billingStaff(),
      billing: repo,
      dashboard: FakeDashboardRepository(stats: billingStats),
      language: language,
    ),
    location: location,
  );
  return repo;
}

/// What the server does to the invoice after a full payment.
Invoice settle(Invoice before, Object? _) => Invoice.fromJson({
  ...invoiceJson,
  'status': 'Paid',
  'total_paid': '1154.00',
  'balance_due': '0.00',
});

Future<void> pickPatient(WidgetTester tester, String query, String name) async {
  await tester.enterText(textFieldIn('record-picker-search'), query);
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pumpAndSettle();
  await tapVisible(tester, find.text(name));
}

void main() {
  group('billing desk', () {
    testWidgets('shows the server figures and the invoice list', (
      tester,
    ) async {
      await pumpBilling(tester, '/billing');
      expect(find.text('31'), findsOneWidget);
      expect(find.text('5'), findsOneWidget); // partially paid, server count
      expect(find.text('₹17,250.50'), findsOneWidget); // outstanding
      expect(find.text('INV/26-27/000012'), findsOneWidget);
      expect(find.text('INV/26-27/000013'), findsOneWidget);
    });

    testWidgets('the status filter asks the server for that status', (
      tester,
    ) async {
      final repo = await pumpBilling(tester, '/billing');
      await tapVisible(
        tester,
        find.byKey(const Key('invoice-status-Partially Paid')),
      );
      expect(repo.statusQueries.last, 'Partially Paid');
      expect(find.text('INV/26-27/000013'), findsNothing);
    });

    testWidgets('search narrows by patient or invoice number', (tester) async {
      await pumpBilling(tester, '/billing');
      await tester.enterText(textFieldIn('billing-search'), 'other');
      await tester.pumpAndSettle();
      expect(find.text('INV/26-27/000013'), findsOneWidget);
      expect(find.text('INV/26-27/000012'), findsNothing);
    });

    testWidgets('money figures withheld by the server read as a dash', (
      tester,
    ) async {
      await pumpApp(
        tester,
        testServices(
          session: billingStaff(),
          billing: FakeBillingRepository(invoices: [openInvoice()]),
          dashboard: FakeDashboardRepository(
            stats: DashboardStats.fromJson(const {
              'statistics': {
                'billing': {
                  'total_invoices': 1,
                  'outstanding': null,
                  'today_revenue': null,
                },
              },
            }),
          ),
        ),
        location: '/billing',
      );
      expect(find.text('—'), findsNWidgets(2));
    });

    testWidgets('payments tab lists receipts and says there is no gateway', (
      tester,
    ) async {
      final repo = FakeBillingRepository(
        invoices: [openInvoice()],
        paymentRows: openInvoice().payments,
      );
      await pumpBilling(tester, '/billing', repository: repo);
      await tapVisible(tester, find.text('Payments'));
      expect(find.text('RCPT-A1'), findsOneWidget);
      expect(find.text('RFND-A1'), findsOneWidget);
      expect(find.text('Payments are recorded at the desk'), findsOneWidget);
    });

    testWidgets('a failed list load offers a retry', (tester) async {
      final repo = FakeBillingRepository(
        invoices: [openInvoice()],
        loadError: const ApiException(kind: ApiErrorKind.server),
      );
      await pumpBilling(tester, '/billing', repository: repo);
      expect(find.text('Try again'), findsWidgets);
      repo.loadError = null;
      await tapVisible(tester, find.text('Try again').first);
      expect(find.text('INV/26-27/000012'), findsOneWidget);
    });

    testWidgets('roles without Billing are sent home', (tester) async {
      await pumpApp(
        tester,
        testServices(session: roleSession('Lab Staff', {'Laboratory.View'})),
        location: '/billing',
      );
      expect(find.text('INV/26-27/000012'), findsNothing);
      expect(find.byKey(const Key('new-invoice')), findsNothing);
    });

    testWidgets('billing pages are translated into Hindi', (tester) async {
      await pumpBilling(tester, '/billing', language: AppLanguage.hi);
      expect(find.text('नया बिल'), findsOneWidget);
      expect(find.text('INV/26-27/000012'), findsOneWidget);
    });
  });

  group('invoice detail', () {
    testWidgets('shows lines, totals and history exactly as the server sent', (
      tester,
    ) async {
      await pumpBilling(tester, '/billing/invoices/12');
      expect(find.text('Test Patient Bill'), findsWidgets);
      expect(find.text('UH-41'), findsOneWidget);
      expect(find.text('₹1,154.00'), findsWidgets); // total
      expect(find.text('₹654.00'), findsOneWidget); // balance
      expect(find.textContaining('from pharmacy'), findsOneWidget);
      expect(find.text('RFND-A1'), findsOneWidget);
    });

    testWidgets('a receptionist may record payments but not refunds', (
      tester,
    ) async {
      await pumpBilling(
        tester,
        '/billing/invoices/12',
        session: receptionist(),
      );
      expect(find.byKey(const Key('record-payment')), findsOneWidget);
      expect(find.byKey(const Key('record-refund')), findsNothing);
    });

    testWidgets('a paid invoice offers no payment', (tester) async {
      final repo = FakeBillingRepository(invoices: [settle(openInvoice(), 0)]);
      await pumpBilling(tester, '/billing/invoices/12', repository: repo);
      expect(find.byKey(const Key('record-payment')), findsNothing);
      expect(find.byKey(const Key('record-refund')), findsOneWidget);
    });
  });

  group('payment', () {
    testWidgets('more than the balance is stopped before anything is sent', (
      tester,
    ) async {
      final repo = await pumpBilling(tester, '/billing/invoices/12/pay');
      await tester.enterText(textFieldIn('money-amount'), '654.01');
      await tapVisible(tester, find.byKey(const Key('money-submit')));
      expect(find.textContaining('more than the balance due'), findsOneWidget);
      expect(repo.paymentCalls, isEmpty);

      await tester.enterText(textFieldIn('money-amount'), '-5');
      await tapVisible(tester, find.byKey(const Key('money-submit')));
      expect(find.textContaining('Enter an amount in rupees'), findsOneWidget);
      expect(repo.paymentCalls, isEmpty);
    });

    testWidgets('confirmed payment is shown as the server recorded it', (
      tester,
    ) async {
      final repo = FakeBillingRepository(invoices: [openInvoice()])
        ..afterPayment = settle;
      await pumpBilling(tester, '/billing/invoices/12/pay', repository: repo);
      await tester.enterText(textFieldIn('money-amount'), '654');
      await tapVisible(tester, find.byKey(const Key('method-UPI')));
      await tester.enterText(textFieldIn('money-note'), 'UPI-TXN-9');
      await tapVisible(tester, find.byKey(const Key('money-submit')));

      expect(find.textContaining('it does not charge anyone'), findsOneWidget);
      expect(repo.paymentCalls, isEmpty); // nothing before the confirmation
      await tapVisible(tester, find.text('Record payment').last);

      final call = repo.paymentCalls.single;
      expect(call.request.amount, '654.00');
      expect(call.request.method, 'UPI');
      expect(call.request.reference, 'UPI-TXN-9');
      expect(call.key, hasLength(32));
      expect(find.text('RCPT-SYN1'), findsOneWidget);
      expect(find.text('Paid'), findsWidgets); // the status the server set
      expect(find.text('₹0.00'), findsOneWidget);
    });

    testWidgets('backing out of the confirmation sends nothing', (
      tester,
    ) async {
      final repo = await pumpBilling(tester, '/billing/invoices/12/pay');
      await tester.enterText(textFieldIn('money-amount'), '100');
      await tapVisible(tester, find.byKey(const Key('money-submit')));
      await tapVisible(tester, find.text('Cancel').last);
      expect(repo.paymentCalls, isEmpty);
    });

    testWidgets('a retry after no answer reuses the same key', (tester) async {
      final repo = FakeBillingRepository(invoices: [openInvoice()])
        ..failNext = const ApiException(kind: ApiErrorKind.timeout);
      await pumpBilling(tester, '/billing/invoices/12/pay', repository: repo);
      await tester.enterText(textFieldIn('money-amount'), '100');
      await tapVisible(tester, find.byKey(const Key('money-submit')));
      await tapVisible(tester, find.text('Record payment').last);
      expect(find.byKey(const Key('money-done')), findsNothing);

      await tapVisible(tester, find.byKey(const Key('money-submit')));
      await tapVisible(tester, find.text('Record payment').last);
      expect(repo.paymentCalls, hasLength(2));
      expect(repo.paymentCalls[0].key, repo.paymentCalls[1].key);
      expect(find.byKey(const Key('money-done')), findsOneWidget);
    });

    testWidgets('a refused amount shows a safe message, not the server text', (
      tester,
    ) async {
      final repo = FakeBillingRepository(invoices: [openInvoice()])
        ..failNext = const ApiException(
          kind: ApiErrorKind.validation,
          statusCode: 400,
          fieldErrors: {
            'amount': ['Amount exceeds the outstanding balance (10.00).'],
          },
        );
      await pumpBilling(tester, '/billing/invoices/12/pay', repository: repo);
      await tester.enterText(textFieldIn('money-amount'), '100');
      await tapVisible(tester, find.byKey(const Key('money-submit')));
      await tapVisible(tester, find.text('Record payment').last);
      expect(find.textContaining('did not accept this amount'), findsOneWidget);
      expect(find.textContaining('outstanding balance (10.00)'), findsNothing);
    });

    testWidgets('a refund needs a reason and stays within the money received', (
      tester,
    ) async {
      final repo = await pumpBilling(tester, '/billing/invoices/12/refund');
      await tester.enterText(textFieldIn('money-amount'), '600');
      await tapVisible(tester, find.byKey(const Key('money-submit')));
      expect(
        find.textContaining('more than the amount received'),
        findsOneWidget,
      );
      expect(find.text('Give the reason for the refund.'), findsOneWidget);

      await tester.enterText(textFieldIn('money-amount'), '50');
      await tester.enterText(textFieldIn('money-note'), 'Duplicate charge');
      await tapVisible(tester, find.byKey(const Key('money-submit')));
      await tapVisible(tester, find.text('Record refund').last);
      expect(repo.refundCalls.single.request.reason, 'Duplicate charge');
    });

    testWidgets('a receptionist reaching the refund page cannot refund', (
      tester,
    ) async {
      final repo = await pumpBilling(
        tester,
        '/billing/invoices/12/refund',
        session: receptionist(),
      );
      expect(find.byKey(const Key('money-submit')), findsNothing);
      expect(repo.refundCalls, isEmpty);
    });
  });

  group('new invoice', () {
    const patient = PatientSummary(
      id: 41,
      name: 'Test Patient Bill',
      uhid: 'UH-41',
    );

    testWidgets('sends the chosen patient and lines, then opens the invoice', (
      tester,
    ) async {
      final repo = FakeBillingRepository(patients: [patient]);
      await pumpBilling(tester, '/billing/new', repository: repo);
      await tapVisible(tester, find.byKey(const Key('invoice-submit')));
      expect(
        find.text('Choose the patient by searching their name, phone or UHID.'),
        findsOneWidget,
      );

      await pickPatient(tester, 'Te', 'Test Patient Bill');
      await tester.enterText(textFieldIn('line-price-0'), '500');
      await tapVisible(tester, find.byKey(const Key('add-line-laboratory')));
      await tester.enterText(textFieldIn('line-price-1'), '350.5');
      await tester.enterText(textFieldIn('line-tax-1'), '5');
      await tapVisible(tester, find.byKey(const Key('invoice-submit')));

      final draft = repo.created.single;
      expect(draft.patientId, 41);
      expect(draft.discount, '0.00');
      expect([for (final l in draft.lines) l.unitPrice], ['500.00', '350.50']);
      expect(draft.lines[1].description, 'Laboratory Charges');
      expect(draft.lines[1].taxRate, '5.00');
      expect(find.text('INV/26-27/SYN1'), findsOneWidget); // server number
    });

    testWidgets('a line without a price is not sent', (tester) async {
      final repo = FakeBillingRepository(patients: [patient]);
      await pumpBilling(tester, '/billing/new', repository: repo);
      await pickPatient(tester, 'Te', 'Test Patient Bill');
      await tapVisible(tester, find.byKey(const Key('invoice-submit')));
      expect(repo.created, isEmpty);
      expect(find.textContaining('Enter an amount in rupees'), findsOneWidget);
    });

    testWidgets('an unanswered create is not resent blindly', (tester) async {
      final repo = FakeBillingRepository(patients: [patient])
        ..failNext = const ApiException(kind: ApiErrorKind.network);
      await pumpBilling(tester, '/billing/new', repository: repo);
      await pickPatient(tester, 'Te', 'Test Patient Bill');
      await tester.enterText(textFieldIn('line-price-0'), '500');
      await tapVisible(tester, find.byKey(const Key('invoice-submit')));
      expect(find.textContaining('may have been created'), findsOneWidget);
      await tester.tap(
        find.byKey(const Key('invoice-submit')),
        warnIfMissed: false,
      );
      await tester.pumpAndSettle();
      expect(repo.created, isEmpty);
    });
  });
}
