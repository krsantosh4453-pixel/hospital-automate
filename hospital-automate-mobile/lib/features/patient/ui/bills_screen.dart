import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../data/record_models.dart';
import '../record_loader.dart';
import 'patient_ui.dart';

/// The sum of the server's `balance_due` over [invoices]; null when no
/// invoice says (never estimated on the phone).
double? outstandingBalance(List<Invoice> invoices) {
  final known = [
    for (final invoice in invoices)
      if (invoice.balanceDue != null) invoice.balanceDue!,
  ];
  return known.isEmpty ? null : known.fold<double>(0, (sum, v) => sum + v);
}

/// `/patient/bills`: invoices and the payments recorded against them.
/// There is no online payment: the backend has no payment gateway, so bills
/// are paid at the hospital and this page only shows them.
class BillsScreen extends StatefulWidget {
  const BillsScreen({super.key});

  @override
  State<BillsScreen> createState() => _BillsScreenState();
}

class _BillsScreenState extends State<BillsScreen> {
  late final RecordLoader<List<Invoice>> _loader = RecordLoader(
    AppScope.read(context).patient.invoices,
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
        PageHeader(title: t.patientNavBills, description: t.billsIntro),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(title: t.payAtHospital, message: t.payAtHospitalBody),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<Invoice>>(
          loader: _loader,
          builder: (context, invoices) {
            if (invoices.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.receiptIndianRupee,
                  title: t.noBillsYet,
                ),
              );
            }
            final owing = invoices.where((i) => i.hasBalance).length;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                StatTileGrid(
                  children: [
                    StatTile(
                      label: t.outstandingBalance,
                      value: formatRupees(outstandingBalance(invoices)),
                      icon: LucideIcons.wallet,
                      tone: owing > 0 ? HmsTone.warning : HmsTone.success,
                    ),
                    StatTile(
                      label: t.billsWithBalance,
                      value: '$owing',
                      icon: LucideIcons.receiptIndianRupee,
                      tone: HmsTone.neutral,
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.x4),
                HmsCard(
                  child: HmsDividedColumn(
                    children: [
                      for (final invoice in invoices)
                        _InvoiceRow(invoice: invoice),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _InvoiceRow extends StatelessWidget {
  const _InvoiceRow({required this.invoice});

  final Invoice invoice;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return InkWell(
      onTap: () => _showInvoice(context, invoice),
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
                      formatDay(t, invoice.createdAt),
                      ?invoice.hospitalName,
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
                  formatRupees(invoice.totalAmount),
                  style: AppTypography.body(weight: FontWeight.w600),
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

Future<void> _showInvoice(BuildContext context, Invoice invoice) {
  final t = context.l10n;
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.x4),
        child: HmsCard(
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
                  DetailRow(
                    label: t.billDate,
                    value: formatDay(t, invoice.createdAt),
                  ),
                  for (final line in invoice.items)
                    DetailRow(
                      label: line.quantity == null
                          ? line.description
                          : '${line.description} × ${line.quantity}',
                      value: formatRupees(line.subtotal),
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
              HmsCardHeader(title: t.paymentHistory),
              if (invoice.payments.isEmpty)
                HmsEmptyState(compact: true, title: t.noPaymentsYet)
              else
                HmsDividedColumn(
                  children: [
                    for (final payment in invoice.payments)
                      DetailRow(
                        label: [
                          formatDateTime(t, payment.paidAt),
                          ?payment.method,
                          if (payment.kind == 'refund') t.refund,
                        ].join(' · '),
                        value: [
                          formatRupees(payment.amount),
                          if (payment.receiptNumber != null)
                            '(${payment.receiptNumber})',
                        ].join(' '),
                      ),
                  ],
                ),
            ],
          ),
        ),
      ),
    ),
  );
}
