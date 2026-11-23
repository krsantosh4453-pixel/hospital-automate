/// Billing requests the desk sends. Amounts travel as decimal strings
/// ("400.00"), never doubles, and every total is computed by the server
/// (billing/services.py): the app sends lines and money received only.
library;

import 'package:flutter/foundation.dart';

/// The methods the web billing page records (src/pages/billing.jsx). They
/// label money already received at the counter: the backend has no payment
/// gateway, so choosing UPI or Card here never charges anyone.
const paymentMethods = ['Cash', 'UPI', 'Card', 'Bank Transfer'];

/// Charge sources offered as line presets, as on the web invoice form.
/// Medicine bills come from the pharmacy itself (billing/pharmacy_charges.py).
enum ChargeSource { consultation, laboratory, pharmacy, other }

/// The description the web form writes for a [ChargeSource] line.
const chargeSourceDescriptions = {
  ChargeSource.consultation: 'Doctor Consultation',
  ChargeSource.laboratory: 'Laboratory Charges',
  ChargeSource.pharmacy: 'Pharmacy Charges',
  ChargeSource.other: 'Other Charges',
};

/// Rupees typed by a person, as a decimal string with two places, or null
/// when it is not a plain positive amount ("12", "12.5", "1,200.00").
String? normalizeAmount(String input) {
  final cleaned = input.trim().replaceAll(',', '');
  final match = RegExp(r'^(\d{1,10})(?:\.(\d{1,2}))?$').firstMatch(cleaned);
  if (match == null) return null;
  final rupees = int.parse(match.group(1)!);
  final paise = (match.group(2) ?? '').padRight(2, '0');
  final value = '$rupees.$paise';
  return amountInPaise(value) == 0 ? null : value;
}

/// Same as [normalizeAmount] but also accepts zero (a discount or tax rate).
String? normalizeAmountOrZero(String input) {
  final cleaned = input.trim().replaceAll(',', '');
  if (cleaned.isEmpty || RegExp(r'^0+(\.0{0,2})?$').hasMatch(cleaned)) {
    return '0.00';
  }
  return normalizeAmount(cleaned);
}

/// An amount in whole paise, for exact comparisons (no floating point).
int amountInPaise(String normalized) {
  final parts = normalized.split('.');
  return int.parse(parts[0]) * 100 +
      int.parse(parts.length > 1 ? parts[1] : '0');
}

/// A server amount (already rounded to paise) in whole paise.
int? paiseOf(double? amount) => amount == null ? null : (amount * 100).round();

/// Money received at the desk against one invoice (`POST billing/payments/`).
@immutable
class PaymentRequest {
  const PaymentRequest({
    required this.invoiceId,
    required this.amount,
    required this.method,
    this.reference = '',
  });

  final int invoiceId;

  /// From [normalizeAmount].
  final String amount;
  final String method;

  /// UPI transaction id, card slip or transfer reference, if any.
  final String reference;

  Map<String, Object?> toJson(String idempotencyKey) => {
    'invoice': invoiceId,
    'amount': amount,
    'payment_method': method,
    if (reference.trim().isNotEmpty) 'reference': reference.trim(),
    'idempotency_key': idempotencyKey,
  };
}

/// Money paid back on an invoice (`POST billing/invoices/<id>/refund/`).
@immutable
class RefundRequest {
  const RefundRequest({
    required this.invoiceId,
    required this.amount,
    required this.reason,
    required this.method,
  });

  final int invoiceId;
  final String amount;
  final String reason;
  final String method;

  Map<String, Object?> toJson(String idempotencyKey) => {
    'amount': amount,
    'reason': reason.trim(),
    'payment_method': method,
    'idempotency_key': idempotencyKey,
  };
}

/// One line of a new invoice. The server computes its subtotal and tax.
@immutable
class InvoiceDraftLine {
  const InvoiceDraftLine({
    required this.description,
    required this.unitPrice,
    this.quantity = 1,
    this.taxRate = '0.00',
  });

  final String description;
  final String unitPrice;
  final int quantity;

  /// GST percent, 0 to 100.
  final String taxRate;

  Map<String, Object?> toJson() => {
    'description': description.trim(),
    'quantity': quantity,
    'unit_price': unitPrice,
    'tax_rate': taxRate,
  };
}

/// A new invoice (`POST billing/invoices/` with `items_data`). Totals,
/// tax, status and the invoice number are all set by the server.
@immutable
class InvoiceDraft {
  const InvoiceDraft({
    required this.hospitalId,
    required this.patientId,
    required this.lines,
    this.discount = '0.00',
  });

  final int hospitalId;
  final int patientId;
  final List<InvoiceDraftLine> lines;
  final String discount;

  Map<String, Object?> toJson() => {
    'hospital': hospitalId,
    'patient': patientId,
    'discount': discount,
    'items_data': [for (final line in lines) line.toJson()],
  };
}
