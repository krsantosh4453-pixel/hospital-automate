// Live run of the laboratory and billing repositories against a throwaway
// backend with synthetic `seed_demo` data (e2e settings). Never point this at
// a server with real patients: it creates an order, an invoice and payments.
//
//   HMS_LIVE_ORIGIN=http://127.0.0.1:8137 HMS_LIVE_PASSWORD=… \
//   flutter test test/live/lab_billing_live_test.dart
//
// Skipped unless both variables are set.
@Tags(['live'])
library;

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';
import 'package:hms_mobile/features/auth/auth_models.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/features/billing/data/billing_models.dart';
import 'package:hms_mobile/features/billing/data/billing_repository.dart';
import 'package:hms_mobile/features/dashboard/dashboard_repository.dart';
import 'package:hms_mobile/features/laboratory/data/lab_repository.dart';
import 'package:hms_mobile/features/laboratory/data/lab_workflow.dart';

final _env = Platform.environment;
final _origin = _env['HMS_LIVE_ORIGIN'];
final _password = _env['HMS_LIVE_PASSWORD'];
const _patientQuery = 'Demo Portal';
const _device = DeviceInfo(
  deviceId: 'live-test-lab-billing',
  platform: 'other',
  appVersion: 'live-test',
);

Matcher _apiError(ApiErrorKind kind) =>
    throwsA(isA<ApiException>().having((e) => e.kind, 'kind', kind));

void main() {
  final skip = _origin == null || _password == null
      ? 'Set HMS_LIVE_ORIGIN and HMS_LIVE_PASSWORD to run'
      : null;
  String? token;
  int? hospitalId;
  late ApiClient api;
  late ApiLabRepository lab;
  late ApiBillingRepository billing;

  setUpAll(() {
    if (skip != null) return;
    api = ApiClient(
      config: ApiConfig(origin: _origin!),
      accessToken: () async => token,
      hospitalId: () => hospitalId,
      log: (_) {},
    );
    lab = ApiLabRepository(api);
    billing = ApiBillingRepository(api);
  });

  Future<void> signIn(String username, String role) async {
    final auth = ApiAuthRepository(api);
    token = null;
    token = (await auth.staffPasswordLogin(
      username,
      _password!,
      _device,
    )).access;
    final context = (await auth.meContexts()).hospitals.single;
    expect(context.role, role);
    hospitalId = context.id;
  }

  group('laboratory', () {
    late int patientId;
    late int orderId;
    final sampleId = 'E2E-${DateTime.now().millisecondsSinceEpoch}';

    test('1. lab staff find the patient and place an order', () async {
      await signIn('demo.lab', 'Lab Staff');
      final found = await lab.lookupPatients(_patientQuery);
      patientId = found.first.id;
      final order = await lab.createOrder(
        LabOrderDraft(
          hospitalId: hospitalId!,
          patientId: patientId,
          testName: 'E2E Live Panel',
          priority: 'Urgent',
        ),
      );
      orderId = order.id;
      expect(order.status, LabStatus.ordered);
      final listed = await lab.orders(status: LabStatus.ordered);
      expect(listed.map((t) => t.id), contains(orderId));
    }, skip: skip);

    test('2. a step out of order is refused and changes nothing', () async {
      await expectLater(
        lab.advance(orderId, LabStep.verify),
        _apiError(ApiErrorKind.validation),
      );
      expect((await lab.order(orderId)).status, LabStatus.ordered);
    }, skip: skip);

    test('3. every step in turn, kept by the server', () async {
      await lab.advance(
        orderId,
        LabStep.collect,
        SampleCollectionInput(
          sampleType: 'Blood',
          containerType: 'EDTA',
          sampleId: sampleId,
          notes: 'E2E fasting',
        ).toJson(),
      );
      expect((await lab.findBySample(sampleId)).id, orderId);
      await lab.advance(orderId, LabStep.dispatch, {'dispatch_notes': 'E2E'});
      await lab.advance(orderId, LabStep.receive);
      await lab.advance(orderId, LabStep.startProcessing);
      await lab.advance(orderId, LabStep.enterResult, {
        'result_text': 'E2E synthetic result',
      });
      final entered = await lab.order(orderId);
      expect(entered.status, LabStatus.resultEntered);
      expect(entered.result!.isVerified, isFalse); // not approved by entry
      await lab.advance(orderId, LabStep.verify);
      await lab.advance(orderId, LabStep.release);

      final done = await lab.order(orderId);
      expect(done.status, LabStatus.released);
      expect(done.result!.text, 'E2E synthetic result');
      expect(done.result!.isVerified, isTrue);
      expect(done.sample!.sampleId, sampleId);
      expect(done.sample!.notes, 'E2E fasting');
      expect(done.collectedAt, isNotNull);
      expect(done.receivedAt, isNotNull);
      expect(done.releasedAt, isNotNull);
    }, skip: skip);

    test('4. a released order cannot be cancelled', () async {
      await expectLater(
        lab.cancel(orderId),
        _apiError(ApiErrorKind.validation),
      );
    }, skip: skip);

    test('5. a hospital manager may read but not order', () async {
      await signIn('demo.manager', 'Hospital Manager');
      expect((await lab.order(orderId)).status, LabStatus.released);
      await expectLater(
        lab.createOrder(
          LabOrderDraft(
            hospitalId: hospitalId!,
            patientId: patientId,
            testName: 'E2E Manager Order',
          ),
        ),
        _apiError(ApiErrorKind.forbidden),
      );
    }, skip: skip);
  });

  group('billing', () {
    late int invoiceId;
    final firstKey = ApiClient.newIdempotencyKey();

    test('1. the desk creates an invoice; the server computes it', () async {
      await signIn('demo.desk.main', 'Receptionist');
      final patient = (await billing.searchPatients(_patientQuery)).first;
      final invoice = await billing.createInvoice(
        InvoiceDraft(
          hospitalId: hospitalId!,
          patientId: patient.id,
          lines: const [
            InvoiceDraftLine(
              description: 'E2E Consultation',
              unitPrice: '1000.00',
            ),
            InvoiceDraftLine(
              description: 'E2E Laboratory',
              unitPrice: '200.00',
              taxRate: '5.00',
            ),
          ],
        ),
      );
      invoiceId = invoice.id;
      expect(invoice.status, 'Unpaid');
      expect(invoice.taxAmount, 10);
      expect(invoice.totalAmount, 1210);
      expect(invoice.balanceDue, 1210);
      expect(invoice.invoiceNumber, startsWith('INV/'));
    }, skip: skip);

    test('2. more than the balance is refused, nothing recorded', () async {
      await expectLater(
        billing.recordPayment(
          PaymentRequest(
            invoiceId: invoiceId,
            amount: '1210.01',
            method: 'Cash',
          ),
          ApiClient.newIdempotencyKey(),
        ),
        _apiError(ApiErrorKind.validation),
      );
      expect((await billing.invoice(invoiceId)).payments, isEmpty);
    }, skip: skip);

    test('3. the same key twice records one payment', () async {
      final request = PaymentRequest(
        invoiceId: invoiceId,
        amount: '400.00',
        method: 'UPI',
        reference: 'E2E-UPI-1',
      );
      final first = await billing.recordPayment(request, firstKey);
      final second = await billing.recordPayment(request, firstKey);
      expect(second.id, first.id);
      final invoice = await billing.invoice(invoiceId);
      expect(invoice.payments, hasLength(1));
      expect(invoice.status, 'Partially Paid');
      expect(invoice.totalPaid, 400);
      expect(invoice.balanceDue, 810);
    }, skip: skip);

    test('4. a receptionist cannot refund', () async {
      await expectLater(
        billing.refund(
          RefundRequest(
            invoiceId: invoiceId,
            amount: '50.00',
            reason: 'E2E',
            method: 'Cash',
          ),
          ApiClient.newIdempotencyKey(),
        ),
        _apiError(ApiErrorKind.forbidden),
      );
    }, skip: skip);

    test('5. billing staff refund, then settle; the figures follow', () async {
      await signIn('demo.billing', 'Billing Staff');
      await billing.refund(
        RefundRequest(
          invoiceId: invoiceId,
          amount: '100.00',
          reason: 'E2E overcharge',
          method: 'Cash',
        ),
        ApiClient.newIdempotencyKey(),
      );
      var invoice = await billing.invoice(invoiceId);
      expect(invoice.totalPaid, 300);
      expect(invoice.balanceDue, 910);

      final stats = await ApiDashboardRepository(api).fetch(hospitalId!);
      expect(stats.count('billing', 'partial'), greaterThanOrEqualTo(1));
      expect(stats.money('billing', 'outstanding'), greaterThanOrEqualTo(910));

      await billing.recordPayment(
        PaymentRequest(invoiceId: invoiceId, amount: '910.00', method: 'Card'),
        ApiClient.newIdempotencyKey(),
      );
      invoice = await billing.invoice(invoiceId);
      expect(invoice.status, 'Paid');
      expect(invoice.balanceDue, 0);
      final recent = await billing.payments();
      // The 400 payment, the 100 refund and the 910 payment.
      expect(recent.where((p) => p.invoiceId == invoiceId), hasLength(3));
    }, skip: skip);
  });
}
