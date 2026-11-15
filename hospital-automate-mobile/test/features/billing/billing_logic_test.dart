import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/billing/data/billing_models.dart';
import 'package:hms_mobile/features/billing/data/billing_repository.dart';
import 'package:hms_mobile/features/billing/ui/billing_ui.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';
import 'package:hms_mobile/l10n/generated/app_localizations_en.dart';

import '../../support/test_app.dart';
import '../laboratory/lab_logic_test.dart' show roleSession;

// Synthetic data only.
const invoiceJson = <String, Object?>{
  'id': 12,
  'invoice_number': 'INV/26-27/000012',
  'patient': 41,
  'patient_name': 'Test Patient Bill',
  'patient_uhid': 'UH-41',
  'hospital': 7,
  'hospital_name': 'Test General Hospital',
  'discount': '100.00',
  'tax': '54.00',
  'total': '1154.00',
  'status': 'Partially Paid',
  'created_at': '2026-11-15T05:00:00Z',
  'items': [
    {
      'id': 1,
      'description': 'Doctor Consultation',
      'quantity': 1,
      'unit_price': '500.00',
      'subtotal': '500.00',
      'tax_rate': '0.00',
      'pharmacy_sale': null,
    },
    {
      'id': 2,
      'description': 'Paracetamol 500',
      'quantity': 2,
      'unit_price': '350.00',
      'subtotal': '700.00',
      'tax_rate': '12.00',
      'pharmacy_sale': 88,
    },
  ],
  'payments': [
    {
      'id': 3,
      'invoice': 12,
      'kind': 'payment',
      'amount': '600.00',
      'payment_method': 'UPI',
      'receipt_number': 'RCPT-A1',
      'reference': 'UPI-REF-1',
      'paid_at': '2026-11-15T05:10:00Z',
    },
    {
      'id': 4,
      'invoice': 12,
      'kind': 'refund',
      'amount': '100.00',
      'payment_method': 'Cash',
      'receipt_number': 'RFND-A1',
      'reference': 'Overcharged',
      'paid_at': '2026-11-15T05:20:00Z',
    },
  ],
  'total_paid': '500.00',
  'balance_due': '654.00',
  'is_paid': false,
  'subtotal': '1200.00',
  'tax_amount': '54.00',
  'total_amount': '1154.00',
};

const billingVAE = {'Billing.View', 'Billing.Add', 'Billing.Edit'};

({ApiBillingRepository repo, FakeAdapter adapter}) billingRepo(
  Map<String, (Object body, int status)> routes,
) {
  final adapter = FakeAdapter((options) async {
    final answer = routes[options.uri.path];
    if (answer == null) return jsonBody('{"detail":"Not found."}', 404);
    return jsonBody(jsonEncode(answer.$1), answer.$2);
  });
  final api = ApiClient(
    config: testConfig,
    accessToken: () async => 'access-token',
    hospitalId: () => 7,
    adapter: adapter,
    log: (_) {},
  );
  return (repo: ApiBillingRepository(api), adapter: adapter);
}

void main() {
  group('amounts', () {
    test('typed rupees become exact two-place strings', () {
      expect(normalizeAmount('500'), '500.00');
      expect(normalizeAmount(' 499.5 '), '499.50');
      expect(normalizeAmount('1,200.75'), '1200.75');
      expect(normalizeAmount('007'), '7.00');
    });

    test('zero, negative, too precise or text amounts are refused', () {
      for (final bad in ['', '0', '0.00', '-5', '12.345', 'abc', '1e3', '.5']) {
        expect(normalizeAmount(bad), isNull, reason: bad);
      }
      expect(normalizeAmountOrZero(''), '0.00');
      expect(normalizeAmountOrZero('0'), '0.00');
      expect(normalizeAmountOrZero('-1'), isNull);
    });

    test('comparisons are made in whole paise, never floating point', () {
      expect(amountInPaise('654.00'), 65400);
      expect(amountInPaise('0.10'), 10);
      expect(paiseOf(654.0), 65400);
      expect(paiseOf(0.1 + 0.2), 30);
    });
  });

  group('model', () {
    test('reads every staff-side invoice field from the server', () {
      final invoice = Invoice.fromJson(invoiceJson);
      expect(invoice.patientUhid, 'UH-41');
      expect(invoice.subtotal, 1200);
      expect(invoice.discount, 100);
      expect(invoice.taxAmount, 54);
      expect(invoice.totalAmount, 1154);
      expect(invoice.totalPaid, 500);
      expect(invoice.balanceDue, 654);
      expect(invoice.hasBalance, isTrue);
      expect(invoice.hasMoneyReceived, isTrue);
      expect(invoice.items.last.fromPharmacy, isTrue);
      expect(invoice.items.last.taxRate, 12);
      expect(invoice.payments.last.isRefund, isTrue);
      expect(invoice.payments.first.reference, 'UPI-REF-1');
    });
  });

  group('roles', () {
    final open = Invoice.fromJson(invoiceJson);

    test('a receptionist may collect but never refund', () {
      final desk = roleSession('Receptionist', {'Billing.View', 'Billing.Add'});
      expect(mayCollectPayment(desk, open), isTrue);
      expect(mayRefund(desk, open), isFalse);
    });

    test('billing staff may collect and refund', () {
      final staff = roleSession('Billing Staff', billingVAE);
      expect(mayCollectPayment(staff, open), isTrue);
      expect(mayRefund(staff, open), isTrue);
    });

    test('no money moves on a cancelled or settled bill, or for other roles',
        () {
      final staff = roleSession('Billing Staff', billingVAE);
      final cancelled =
          Invoice.fromJson({...invoiceJson, 'status': 'Cancelled'});
      final settled = Invoice.fromJson({
        ...invoiceJson,
        'status': 'Paid',
        'balance_due': '0.00',
      });
      expect(mayCollectPayment(staff, cancelled), isFalse);
      expect(mayCollectPayment(staff, settled), isFalse);
      final nurse = roleSession('Nurse', {'Billing.View', 'Billing.Add'});
      expect(mayCollectPayment(nurse, open), isFalse);
      expect(mayCreateInvoices(patientSession()), isFalse);
    });
  });

  group('repository', () {
    test('a payment sends the key in the header and the body', () async {
      final setup = billingRepo({
        '/api/v1/billing/payments/': (
          {
            'id': 9,
            'invoice': 12,
            'kind': 'payment',
            'amount': '654.00',
            'payment_method': 'Card',
            'receipt_number': 'RCPT-B2',
          },
          201,
        ),
      });
      final payment = await setup.repo.recordPayment(
        const PaymentRequest(
          invoiceId: 12,
          amount: '654.00',
          method: 'Card',
          reference: ' SLIP-77 ',
        ),
        'key-abc',
      );
      expect(payment.receiptNumber, 'RCPT-B2');
      final request = setup.adapter.requests.single;
      expect(request.headers['Idempotency-Key'], 'key-abc');
      expect(request.data, {
        'invoice': 12,
        'amount': '654.00',
        'payment_method': 'Card',
        'reference': 'SLIP-77',
        'idempotency_key': 'key-abc',
      });
    });

    test('a refund goes to the invoice refund action with its reason',
        () async {
      final setup = billingRepo({
        '/api/v1/billing/invoices/12/refund/': (
          {'kind': 'refund', 'amount': '50.00', 'receipt_number': 'RFND-1'},
          201,
        ),
      });
      await setup.repo.refund(
        const RefundRequest(
          invoiceId: 12,
          amount: '50.00',
          reason: ' Duplicate charge ',
          method: 'Cash',
        ),
        'key-r',
      );
      expect(setup.adapter.requests.single.data, {
        'amount': '50.00',
        'reason': 'Duplicate charge',
        'payment_method': 'Cash',
        'idempotency_key': 'key-r',
      });
    });

    test('a new invoice sends lines only, never totals or status', () async {
      final setup = billingRepo({
        '/api/v1/billing/invoices/': (invoiceJson, 201),
      });
      await setup.repo.createInvoice(
        const InvoiceDraft(
          hospitalId: 7,
          patientId: 41,
          discount: '100.00',
          lines: [
            InvoiceDraftLine(
              description: 'Doctor Consultation ',
              unitPrice: '500.00',
            ),
          ],
        ),
      );
      final body = setup.adapter.requests.single.data as Map;
      expect(
        body.keys,
        unorderedEquals(['hospital', 'patient', 'discount', 'items_data']),
      );
      expect(body['items_data'], [
        {
          'description': 'Doctor Consultation',
          'quantity': 1,
          'unit_price': '500.00',
          'tax_rate': '0.00',
        },
      ]);
    });

    test('the status filter is applied by the server', () async {
      final setup = billingRepo({
        '/api/v1/billing/invoices/': (
          {
            'count': 1,
            'next': null,
            'results': [invoiceJson],
          },
          200,
        ),
      });
      await setup.repo.invoices(status: 'Partially Paid');
      expect(
        setup.adapter.requests.single.uri.queryParameters['status'],
        'Partially Paid',
      );
    });
  });

  group('errors', () {
    final t = AppLocalizationsEn();

    ApiException refused(Map<String, List<String>> fields) => ApiException(
      kind: ApiErrorKind.validation,
      statusCode: 400,
      fieldErrors: fields,
      serverMessage: 'Amount exceeds the outstanding balance (654.00).',
    );

    test('the server text is never shown; the field decides the message', () {
      expect(
        billingErrorMessage(t, refused({'amount': ['x']})),
        t.billingAmountRefused,
      );
      expect(
        billingErrorMessage(t, refused({'invoice': ['x']})),
        t.billingInvoiceClosed,
      );
      expect(billingErrorMessage(t, refused({})), t.billingRefused);
      expect(
        billingErrorMessage(
          t,
          const ApiException(kind: ApiErrorKind.forbidden),
        ),
        t.errorForbidden,
      );
    });
  });
}
