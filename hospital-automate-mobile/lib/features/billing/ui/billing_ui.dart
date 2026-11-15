import 'package:flutter/material.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/security/session_controller.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/tone.dart';
import '../../laboratory/data/lab_workflow.dart' show StaffRoles;
import '../../laboratory/ui/lab_ui.dart' show ToneBadge;
import '../../patient/data/record_models.dart';
import '../../patient/ui/patient_ui.dart';

/// Billing pages (staff paths, as on the web).
abstract final class BillingRoutes {
  static const desk = '/billing';
  static const newInvoice = '/billing/new';

  static String invoice(int id) => '$desk/invoices/$id';
  static String pay(int id) => '${invoice(id)}/pay';
  static String refund(int id) => '${invoice(id)}/refund';
}

/// `BILLING_ROLES` in billing/views.py: may list invoices and record payments.
const billingRoles = {
  StaffRoles.admin,
  StaffRoles.hospitalManager,
  StaffRoles.billingStaff,
  StaffRoles.receptionist,
};

/// Roles allowed to refund or cancel (a Receptionist may not).
const refundRoles = {
  StaffRoles.admin,
  StaffRoles.hospitalManager,
  StaffRoles.billingStaff,
};

/// Creating invoices and recording money both need `Billing.Add`.
bool mayCreateInvoices(SessionState s) =>
    s.hasRole(billingRoles) && s.can('Billing', 'Add');

bool mayCollectPayment(SessionState s, Invoice invoice) =>
    mayCreateInvoices(s) && !invoice.isCancelled && invoice.hasBalance;

bool mayRefund(SessionState s, Invoice invoice) =>
    s.hasRole(refundRoles) &&
    s.can('Billing', 'Edit') &&
    invoice.hasMoneyReceived;

/// A safe sentence for a refused billing write, by the field the server
/// named; its own text (which quotes balances) is never shown raw.
String billingErrorMessage(AppLocalizations t, Object error) {
  if (error is! ApiException || error.kind != ApiErrorKind.validation) {
    return apiErrorMessage(t, error);
  }
  final fields = error.fieldErrors.keys.toSet();
  if (fields.contains('amount')) return t.billingAmountRefused;
  if (fields.contains('invoice')) return t.billingInvoiceClosed;
  if (fields.contains('discount')) return t.billingDiscountRefused;
  if (fields.contains('idempotency_key')) return t.billingKeyReused;
  if (fields.contains('reason')) return t.billingRefundReasonRequired;
  if (fields.isEmpty) return t.billingRefused;
  return t.checkTheseFields(fields.join(', '));
}

String paymentMethodLabel(AppLocalizations t, String? method) =>
    switch (method) {
      'Cash' => t.paymentCash,
      'UPI' => t.paymentUpi,
      'Card' => t.paymentCard,
      'Bank Transfer' => t.paymentBankTransfer,
      null => '—',
      _ => method,
    };

/// One invoice in the desk list. All amounts are the server's.
class InvoiceRow extends StatelessWidget {
  const InvoiceRow({super.key, required this.invoice, this.onTap});

  final Invoice invoice;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    invoice.invoiceNumber ?? '#${invoice.id}',
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  Text(
                    [
                      ?invoice.patientName,
                      ?invoice.patientUhid,
                      formatDay(t, invoice.createdAt),
                    ].join(' · '),
                    style: AppTypography.small(),
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.x2),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  formatRupees(invoice.totalAmount),
                  style: AppTypography.body(weight: FontWeight.w600),
                ),
                if (invoice.hasBalance)
                  Text(
                    t.billingDue(formatRupees(invoice.balanceDue)),
                    style: AppTypography.caption(),
                  ),
                StatusBadge(status: invoice.status),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// One recorded payment or refund. Only confirmed records exist on the
/// server (no gateway, so nothing is pending or failed).
class PaymentRow extends StatelessWidget {
  const PaymentRow({super.key, required this.payment, this.onTap});

  final InvoicePayment payment;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    payment.receiptNumber ?? '—',
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  Text(
                    [
                      formatDateTime(t, payment.paidAt),
                      paymentMethodLabel(t, payment.method),
                      ?payment.reference,
                    ].join(' · '),
                    style: AppTypography.small(),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  payment.isRefund
                      ? '− ${formatRupees(payment.amount)}'
                      : formatRupees(payment.amount),
                  style: AppTypography.body(weight: FontWeight.w600),
                ),
                ToneBadge(
                  label: payment.isRefund ? t.refund : t.billingPaymentKind,
                  tone: payment.isRefund
                      ? AlertTone.warning
                      : AlertTone.success,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
