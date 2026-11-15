import '../../../core/network/api_client.dart';
import '../../../core/network/paged_rows.dart';
import '../../doctor/data/doctor_models.dart' show PatientSummary;
import '../../patient/data/json_read.dart';
import '../../patient/data/record_models.dart';
import 'billing_models.dart';

/// Invoices and payments of the acting hospital (`X-Hospital-ID`), over the
/// endpoints the web billing page uses. Amounts, balances and statuses are
/// the server's; it also checks each payment against the locked balance and
/// returns the first record when an idempotency key is sent again.
abstract interface class BillingRepository {
  Future<List<Invoice>> invoices({String? status});
  Future<Invoice> invoice(int id);
  Future<Invoice> createInvoice(InvoiceDraft draft);

  /// Reuse [idempotencyKey] when retrying the same payment: the server then
  /// answers with the payment it already recorded instead of a second one.
  Future<InvoicePayment> recordPayment(
    PaymentRequest request,
    String idempotencyKey,
  );
  Future<InvoicePayment> refund(RefundRequest request, String idempotencyKey);

  /// Recent payments and refunds across the hospital's invoices.
  Future<List<InvoicePayment>> payments();

  /// Patients to bill (`patients/?search=`, read-only for Billing Staff).
  Future<List<PatientSummary>> searchPatients(String query);
}

class ApiBillingRepository implements BillingRepository {
  ApiBillingRepository(this._api);

  final ApiClient _api;

  /// Payments are listed newest first; two pages cover the desk's day.
  static const _paymentPages = 2;

  @override
  Future<List<Invoice>> invoices({String? status}) async => [
    for (final row in await getAllRows(
      _api,
      'billing/invoices/',
      query: {'status': ?status},
    ))
      Invoice.fromJson(row),
  ];

  @override
  Future<Invoice> invoice(int id) => _api.get(
    'billing/invoices/$id/',
    decode: (json) => Invoice.fromJson(asMap(json)),
  );

  @override
  Future<Invoice> createInvoice(InvoiceDraft draft) => _api.post(
    'billing/invoices/',
    body: draft.toJson(),
    decode: (json) => Invoice.fromJson(asMap(json)),
  );

  @override
  Future<InvoicePayment> recordPayment(
    PaymentRequest request,
    String idempotencyKey,
  ) => _api.post(
    'billing/payments/',
    body: request.toJson(idempotencyKey),
    idempotencyKey: idempotencyKey,
    decode: (json) => InvoicePayment.fromJson(asMap(json)),
  );

  @override
  Future<InvoicePayment> refund(RefundRequest request, String idempotencyKey) =>
      _api.post(
        'billing/invoices/${request.invoiceId}/refund/',
        body: request.toJson(idempotencyKey),
        idempotencyKey: idempotencyKey,
        decode: (json) => InvoicePayment.fromJson(asMap(json)),
      );

  @override
  Future<List<InvoicePayment>> payments() async => [
    for (final row in await getAllRows(
      _api,
      'billing/payments/',
      maxPages: _paymentPages,
    ))
      InvoicePayment.fromJson(row),
  ];

  @override
  Future<List<PatientSummary>> searchPatients(String query) async => [
    for (final row in await getAllRows(
      _api,
      'patients/',
      query: {'search': query.trim()},
      maxPages: 1,
    ))
      PatientSummary.fromJson(row),
  ];
}
