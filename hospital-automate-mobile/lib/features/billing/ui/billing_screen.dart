import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_search_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../dashboard/dashboard_stats.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import 'billing_ui.dart';

enum _Tab { invoices, payments }

/// `/billing`: the hospital's billing figures as the server computes them,
/// the invoice list (status filtered on the server; search and dates on the
/// loaded rows) and recent payments. No total is added up on the phone.
class BillingScreen extends StatefulWidget {
  const BillingScreen({super.key});

  @override
  State<BillingScreen> createState() => _BillingScreenState();
}

class _BillingScreenState extends State<BillingScreen> {
  late final _services = AppScope.read(context);
  String? _status;
  late final RecordLoader<List<Invoice>> _invoices = RecordLoader(
    () => _services.billing.invoices(status: _status),
  );
  late final RecordLoader<List<InvoicePayment>> _payments = RecordLoader(
    _services.billing.payments,
  );
  late final RecordLoader<DashboardStats?> _stats = RecordLoader(() async {
    final hospital = _services.session.activeHospitalId;
    return hospital == null ? null : _services.dashboard.fetch(hospital);
  });
  _Tab _tab = _Tab.invoices;
  String _search = '';
  DateTimeRange? _dates;

  @override
  void initState() {
    super.initState();
    _invoices.load();
    _stats.load();
  }

  @override
  void dispose() {
    _invoices.dispose();
    _payments.dispose();
    _stats.dispose();
    super.dispose();
  }

  void _showTab(_Tab tab) {
    setState(() => _tab = tab);
    if (tab == _Tab.payments && _payments.data == null) _payments.load();
  }

  void _filter(String? status) {
    setState(() => _status = status);
    _invoices.load();
  }

  Future<void> _pickDates() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(now.year - 5),
      lastDate: now,
      initialDateRange: _dates,
    );
    if (picked != null && mounted) setState(() => _dates = picked);
  }

  Future<void> _refresh() => Future.wait([
    _invoices.load(),
    _stats.load(),
    if (_payments.data != null) _payments.load(),
  ]);

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.navBilling,
          description: t.billingDeskIntro,
          actions: [
            HmsButton(
              label: t.refresh,
              icon: LucideIcons.refreshCw,
              variant: HmsButtonVariant.secondary,
              onPressed: _refresh,
            ),
            if (mayCreateInvoices(_services.session.state))
              HmsButton(
                key: const Key('new-invoice'),
                label: t.billingNewInvoice,
                icon: LucideIcons.plus,
                onPressed: () => context.go(BillingRoutes.newInvoice),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        _BillingCounts(loader: _stats),
        const SizedBox(height: AppSpacing.x4),
        SegmentedButton<_Tab>(
          segments: [
            ButtonSegment(
              value: _Tab.invoices,
              label: Text(t.billingInvoices),
              icon: const Icon(LucideIcons.receiptIndianRupee),
            ),
            ButtonSegment(
              value: _Tab.payments,
              label: Text(t.billingPayments),
              icon: const Icon(LucideIcons.wallet),
            ),
          ],
          selected: {_tab},
          onSelectionChanged: (s) => _showTab(s.first),
        ),
        const SizedBox(height: AppSpacing.x4),
        if (_tab == _Tab.invoices) _invoiceTab(t) else _paymentTab(t),
      ],
    );
  }

  Widget _invoiceTab(AppLocalizations t) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Wrap(
        spacing: AppSpacing.x2,
        runSpacing: AppSpacing.x2,
        children: [
          ChoiceChip(
            label: Text(t.filterAll),
            selected: _status == null,
            onSelected: (_) => _filter(null),
          ),
          for (final status in Invoice.statuses)
            ChoiceChip(
              key: Key('invoice-status-$status'),
              label: Text(statusLabel(t, status)),
              selected: _status == status,
              onSelected: (_) => _filter(status),
            ),
        ],
      ),
      const SizedBox(height: AppSpacing.x3),
      HmsSearchField(
        key: const Key('billing-search'),
        hint: t.billingSearchHint,
        surface: HmsSurface.canvas,
        onChanged: (v) => setState(() => _search = v),
      ),
      const SizedBox(height: AppSpacing.x2),
      Wrap(
        spacing: AppSpacing.x2,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          HmsButton(
            key: const Key('invoice-dates'),
            label: _dates == null
                ? t.billingAnyDate
                : '${formatDay(t, _dates!.start)} – ${formatDay(t, _dates!.end)}',
            icon: LucideIcons.calendarRange,
            variant: HmsButtonVariant.secondary,
            size: HmsButtonSize.small,
            onPressed: _pickDates,
          ),
          if (_dates != null)
            HmsButton(
              label: t.billingClearDates,
              variant: HmsButtonVariant.ghost,
              size: HmsButtonSize.small,
              onPressed: () => setState(() => _dates = null),
            ),
        ],
      ),
      const SizedBox(height: AppSpacing.x3),
      RecordSection<List<Invoice>>(
        loader: _invoices,
        builder: (context, invoices) {
          final shown = invoices.where(_matches).toList();
          return HmsCard(
            child: shown.isEmpty
                ? HmsEmptyState(
                    icon: LucideIcons.receiptIndianRupee,
                    title: invoices.isEmpty
                        ? t.noBillsYet
                        : t.billingNoInvoicesMatch,
                  )
                : HmsDividedColumn(
                    children: [
                      for (final invoice in shown)
                        InvoiceRow(
                          key: Key('invoice-${invoice.id}'),
                          invoice: invoice,
                          onTap: () =>
                              context.go(BillingRoutes.invoice(invoice.id)),
                        ),
                    ],
                  ),
          );
        },
      ),
    ],
  );

  bool _matches(Invoice invoice) {
    final query = _search.trim().toLowerCase();
    if (query.isNotEmpty &&
        ![
          invoice.invoiceNumber,
          invoice.patientName,
          invoice.patientUhid,
        ].any((f) => f != null && f.toLowerCase().contains(query))) {
      return false;
    }
    final range = _dates;
    final created = invoice.createdAt;
    if (range == null) return true;
    if (created == null) return false;
    final day = DateTime(created.year, created.month, created.day);
    return !day.isBefore(range.start) && !day.isAfter(range.end);
  }

  Widget _paymentTab(AppLocalizations t) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      HmsAlert(title: t.billingNoGateway, message: t.billingNoGatewayBody),
      const SizedBox(height: AppSpacing.x3),
      RecordSection<List<InvoicePayment>>(
        loader: _payments,
        builder: (context, rows) {
          if (rows.isEmpty) {
            return HmsCard(
              child: HmsEmptyState(
                icon: LucideIcons.wallet,
                title: t.noPaymentsYet,
              ),
            );
          }
          final refunds = rows.where((p) => p.isRefund).length;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              StatTileGrid(
                children: [
                  StatTile(
                    label: t.billingPaymentsRecorded,
                    value: '${rows.length - refunds}',
                    icon: LucideIcons.circleCheck,
                    tone: HmsTone.success,
                    hint: t.billingLatestRecords(rows.length),
                  ),
                  StatTile(
                    label: t.billingRefunds,
                    value: '$refunds',
                    icon: LucideIcons.undo2,
                    tone: HmsTone.warning,
                    hint: t.billingLatestRecords(rows.length),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.x3),
              HmsCard(
                child: HmsDividedColumn(
                  children: [
                    for (final payment in rows)
                      PaymentRow(
                        payment: payment,
                        onTap: payment.invoiceId == null
                            ? null
                            : () => context.go(
                                BillingRoutes.invoice(payment.invoiceId!),
                              ),
                      ),
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

/// `home/stats/detail/` billing figures. Money is null for roles the server
/// does not show revenue to, and then reads "—".
class _BillingCounts extends StatelessWidget {
  const _BillingCounts({required this.loader});

  final RecordLoader<DashboardStats?> loader;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return ListenableBuilder(
      listenable: loader,
      builder: (context, _) {
        final s = loader.data;
        if (loader.error != null && s == null) {
          return HmsAlert(
            tone: AlertTone.warning,
            title: t.billingCountsUnavailable,
            message: apiErrorMessage(t, loader.error!),
          );
        }
        String? count(String key) =>
            s == null ? null : '${s.count('billing', key)}';
        String? money(String key) =>
            s == null ? null : formatRupees(s.money('billing', key));
        return StatTileGrid(
          children: [
            StatTile(
              label: t.billingTotalInvoices,
              value: count('total_invoices'),
              icon: LucideIcons.receiptIndianRupee,
            ),
            StatTile(
              label: t.statusUnpaid,
              value: count('pending'),
              icon: LucideIcons.hourglass,
              tone: HmsTone.warning,
            ),
            StatTile(
              label: t.statusPartiallyPaid,
              value: count('partial'),
              icon: LucideIcons.circleDashed,
              tone: HmsTone.warning,
            ),
            StatTile(
              label: t.statusPaid,
              value: count('paid'),
              icon: LucideIcons.circleCheck,
              tone: HmsTone.success,
            ),
            StatTile(
              label: t.outstandingBalance,
              value: money('outstanding'),
              icon: LucideIcons.wallet,
              tone: HmsTone.danger,
            ),
            StatTile(
              label: t.tileCollectedToday,
              value: money('today_revenue'),
              icon: LucideIcons.indianRupee,
              tone: HmsTone.success,
              hint: t.billingNetOfRefunds,
            ),
          ],
        );
      },
    );
  }
}
