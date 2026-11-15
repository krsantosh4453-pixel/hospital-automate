import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import 'billing_ui.dart';

/// `/billing/invoices/<id>`: one invoice exactly as the server holds it:
/// lines, discount, tax, total, money received and the balance, plus every
/// payment and refund. Read fresh each time the page opens.
class InvoiceScreen extends StatefulWidget {
  const InvoiceScreen({super.key, required this.invoiceId});

  final int invoiceId;

  @override
  State<InvoiceScreen> createState() => _InvoiceScreenState();
}

class _InvoiceScreenState extends State<InvoiceScreen> {
  late final _services = AppScope.read(context);
  late final RecordLoader<Invoice> _loader = RecordLoader(
    () => _services.billing.invoice(widget.invoiceId),
  );

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.billingInvoiceTitle,
          actions: [
            HmsButton(
              label: t.billingBackToDesk,
              icon: LucideIcons.arrowLeft,
              variant: HmsButtonVariant.secondary,
              onPressed: () => context.go(BillingRoutes.desk),
            ),
            HmsButton(
              label: t.refresh,
              icon: LucideIcons.refreshCw,
              variant: HmsButtonVariant.secondary,
              onPressed: _loader.load,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<Invoice>(
          loader: _loader,
          builder: (context, invoice) => _details(context, invoice),
        ),
      ],
    );
  }

  Widget _details(BuildContext context, Invoice invoice) {
    final t = context.l10n;
    final session = _services.session.state;
    final canPay = mayCollectPayment(session, invoice);
    final canRefund = mayRefund(session, invoice);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: invoice.invoiceNumber ?? '#${invoice.id}',
                description: invoice.hospitalName,
                icon: LucideIcons.receiptIndianRupee,
                trailing: StatusBadge(status: invoice.status),
              ),
              HmsDividedColumn(
                children: [
                  DetailRow(label: t.patientLabel, value: invoice.patientName),
                  DetailRow(label: t.patientId, value: invoice.patientUhid),
                  DetailRow(
                    label: t.billDate,
                    value: formatDateTime(t, invoice.createdAt),
                  ),
                ],
              ),
              if (canPay || canRefund)
                Padding(
                  padding: const EdgeInsets.all(AppSpacing.x4),
                  child: Wrap(
                    spacing: AppSpacing.x2,
                    runSpacing: AppSpacing.x2,
                    children: [
                      if (canPay)
                        HmsButton(
                          key: const Key('record-payment'),
                          label: t.billingRecordPayment,
                          icon: LucideIcons.indianRupee,
                          surface: HmsSurface.card,
                          onPressed: () =>
                              context.go(BillingRoutes.pay(invoice.id)),
                        ),
                      if (canRefund)
                        HmsButton(
                          key: const Key('record-refund'),
                          label: t.billingRecordRefund,
                          icon: LucideIcons.undo2,
                          variant: HmsButtonVariant.secondary,
                          surface: HmsSurface.card,
                          onPressed: () =>
                              context.go(BillingRoutes.refund(invoice.id)),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        _LinesCard(invoice: invoice),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(title: t.paymentHistory, icon: LucideIcons.wallet),
              if (invoice.payments.isEmpty)
                HmsEmptyState(compact: true, title: t.noPaymentsYet)
              else
                HmsDividedColumn(
                  children: [
                    for (final payment in invoice.payments)
                      PaymentRow(payment: payment),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x3),
        Text(t.billingPrintOnWeb, style: AppTypography.small()),
      ],
    );
  }
}

class _LinesCard extends StatelessWidget {
  const _LinesCard({required this.invoice});

  final Invoice invoice;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.billingItems, icon: LucideIcons.list),
          if (invoice.items.isEmpty)
            HmsEmptyState(compact: true, title: t.billingNoItems)
          else
            HmsDividedColumn(
              children: [
                for (final line in invoice.items)
                  DetailRow(
                    label: [
                      line.description,
                      if (line.fromPharmacy) '(${t.billingFromPharmacy})',
                    ].join(' '),
                    value: [
                      '${line.quantity ?? 1} × ${formatRupees(line.unitPrice)}',
                      if ((line.taxRate ?? 0) > 0)
                        t.billingGstRate('${line.taxRate}'),
                      '= ${formatRupees(line.subtotal)}',
                    ].join('  '),
                  ),
              ],
            ),
          HmsDividedColumn(
            children: [
              DetailRow(
                label: t.billingSubtotal,
                value: formatRupees(invoice.subtotal),
              ),
              DetailRow(
                label: t.billingDiscount,
                value: formatRupees(invoice.discount),
              ),
              DetailRow(
                label: t.billingTax,
                value: formatRupees(invoice.taxAmount),
              ),
              DetailRow(
                label: t.billTotal,
                value: formatRupees(invoice.totalAmount),
              ),
              DetailRow(
                label: t.amountPaid,
                value: formatRupees(invoice.totalPaid),
              ),
              DetailRow(
                label: t.balanceDue,
                value: formatRupees(invoice.balanceDue),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
