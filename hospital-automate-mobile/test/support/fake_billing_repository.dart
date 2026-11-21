import 'dart:async';

import 'package:hms_mobile/features/billing/data/billing_models.dart';
import 'package:hms_mobile/features/billing/data/billing_repository.dart';
import 'package:hms_mobile/features/doctor/data/doctor_models.dart';
import 'package:hms_mobile/features/patient/data/record_models.dart';

/// In-memory [BillingRepository] for widget tests. Like the server, it
/// returns the first payment when an idempotency key is sent again. All
/// amounts it reports are set by the test, never computed by the app.
class FakeBillingRepository implements BillingRepository {
  FakeBillingRepository({
    List<Invoice>? invoices,
    this.paymentRows = const [],
    this.patients = const [],
    this.loadError,
  }) : invoiceRows = [...?invoices];

  List<Invoice> invoiceRows;
  List<InvoicePayment> paymentRows;
  List<PatientSummary> patients;
  Object? loadError;

  /// Thrown by the next write (then cleared).
  Object? failNext;

  /// What the next payment write does to the invoice, as the server would.
  Invoice Function(Invoice before, PaymentRequest request)? afterPayment;
  Completer<void>? gate;

  final List<String?> statusQueries = [];
  final List<({PaymentRequest request, String key})> paymentCalls = [];
  final List<({RefundRequest request, String key})> refundCalls = [];
  final List<InvoiceDraft> created = [];
  final Map<String, InvoicePayment> _byKey = {};

  @override
  Future<List<Invoice>> invoices({String? status}) async {
    statusQueries.add(status);
    if (loadError != null) throw loadError!;
    return [
      for (final invoice in invoiceRows)
        if (status == null || invoice.status == status) invoice,
    ];
  }

  @override
  Future<Invoice> invoice(int id) async {
    if (loadError != null) throw loadError!;
    return invoiceRows.firstWhere((i) => i.id == id);
  }

  Future<void> _write() async {
    if (gate != null) await gate!.future;
    final error = failNext;
    if (error != null) {
      failNext = null;
      throw error;
    }
  }

  @override
  Future<Invoice> createInvoice(InvoiceDraft draft) async {
    await _write();
    created.add(draft);
    final invoice = Invoice(
      id: 500 + created.length,
      status: 'Unpaid',
      invoiceNumber: 'INV/26-27/SYN${created.length}',
      patientId: draft.patientId,
      patientName: 'Test Patient Bill',
      totalAmount: 1000,
      totalPaid: 0,
      balanceDue: 1000,
    );
    invoiceRows = [invoice, ...invoiceRows];
    return invoice;
  }

  @override
  Future<InvoicePayment> recordPayment(
    PaymentRequest request,
    String idempotencyKey,
  ) async {
    paymentCalls.add((request: request, key: idempotencyKey));
    await _write();
    final earlier = _byKey[idempotencyKey];
    if (earlier != null) return earlier;
    final payment = InvoicePayment(
      id: 700 + _byKey.length,
      invoiceId: request.invoiceId,
      kind: 'payment',
      amount: amountInPaise(request.amount) / 100,
      method: request.method,
      receiptNumber: 'RCPT-SYN${_byKey.length + 1}',
      reference: request.reference,
    );
    _byKey[idempotencyKey] = payment;
    final apply = afterPayment;
    if (apply != null) {
      invoiceRows = [
        for (final i in invoiceRows)
          i.id == request.invoiceId ? apply(i, request) : i,
      ];
    }
    return payment;
  }

  @override
  Future<InvoicePayment> refund(
    RefundRequest request,
    String idempotencyKey,
  ) async {
    refundCalls.add((request: request, key: idempotencyKey));
    await _write();
    return InvoicePayment(
      kind: 'refund',
      invoiceId: request.invoiceId,
      amount: amountInPaise(request.amount) / 100,
      method: request.method,
      receiptNumber: 'RFND-SYN1',
      reference: request.reason,
    );
  }

  @override
  Future<List<InvoicePayment>> payments() async {
    if (loadError != null) throw loadError!;
    return paymentRows;
  }

  @override
  Future<List<PatientSummary>> searchPatients(String query) async => patients;
}
