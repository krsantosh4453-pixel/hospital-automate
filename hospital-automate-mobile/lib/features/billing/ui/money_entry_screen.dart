import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_client.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/billing_models.dart';
import 'billing_ui.dart';

enum MoneyEntryKind { payment, refund }

/// `/billing/invoices/<id>/pay` and `.../refund`: money received at the
/// desk, or paid back. The balance shown is the server's, read fresh; the
/// app checks the amount only to catch typing slips, and the server checks
/// it again against the locked invoice. One idempotency key lives for the
/// whole screen, so pressing again after an unanswered request returns the
/// first record instead of creating a second one.
class MoneyEntryScreen extends StatefulWidget {
  const MoneyEntryScreen({
    super.key,
    required this.invoiceId,
    required this.kind,
  });

  final int invoiceId;
  final MoneyEntryKind kind;

  @override
  State<MoneyEntryScreen> createState() => _MoneyEntryScreenState();
}

class _MoneyEntryScreenState extends State<MoneyEntryScreen> {
  late final _services = AppScope.read(context);
  late final RecordLoader<Invoice> _loader = RecordLoader(
    () => _services.billing.invoice(widget.invoiceId),
  );
  final _amount = TextEditingController();
  final _note = TextEditingController();
  final String _key = ApiClient.newIdempotencyKey();
  String _method = paymentMethods.first;
  bool _saving = false;
  String? _amountError;
  String? _noteError;
  String? _error;
  InvoicePayment? _recorded;

  bool get _refund => widget.kind == MoneyEntryKind.refund;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    _amount.dispose();
    _note.dispose();
    super.dispose();
  }

  /// Most that may be entered: the balance for a payment, the net amount
  /// received for a refund (both as the server reports them).
  double? _limit(Invoice invoice) =>
      _refund ? invoice.totalPaid : invoice.balanceDue;

  String? _checkAmount(AppLocalizations t, Invoice invoice) {
    final amount = normalizeAmount(_amount.text);
    if (amount == null) return t.billingAmountInvalid;
    final limit = paiseOf(_limit(invoice));
    if (limit != null && amountInPaise(amount) > limit) {
      return _refund
          ? t.billingRefundTooHigh(formatRupees(_limit(invoice)))
          : t.billingAmountTooHigh(formatRupees(_limit(invoice)));
    }
    return null;
  }

  Future<void> _submit(Invoice invoice) async {
    if (_saving) return;
    final t = context.l10n;
    final amountError = _checkAmount(t, invoice);
    final noteError = _refund && _note.text.trim().isEmpty
        ? t.billingRefundReasonRequired
        : null;
    setState(() {
      _amountError = amountError;
      _noteError = noteError;
      _error = null;
    });
    if (amountError != null || noteError != null) return;
    final amount = normalizeAmount(_amount.text)!;
    final shown = formatRupees(amountInPaise(amount) / 100);
    final number = invoice.invoiceNumber ?? '#${invoice.id}';
    final ok = await showHmsConfirm(
      context,
      title: _refund
          ? t.billingConfirmRefundTitle
          : t.billingConfirmPaymentTitle,
      message: _refund
          ? t.billingConfirmRefund(
              shown,
              paymentMethodLabel(t, _method),
              number,
            )
          : t.billingConfirmPayment(
              shown,
              paymentMethodLabel(t, _method),
              number,
              invoice.patientName ?? '—',
            ),
      confirmLabel: _refund ? t.billingRecordRefund : t.billingRecordPayment,
      destructive: _refund,
    );
    if (!ok || !mounted) return;
    setState(() => _saving = true);
    try {
      final record = _refund
          ? await _services.billing.refund(
              RefundRequest(
                invoiceId: invoice.id,
                amount: amount,
                reason: _note.text,
                method: _method,
              ),
              _key,
            )
          : await _services.billing.recordPayment(
              PaymentRequest(
                invoiceId: invoice.id,
                amount: amount,
                method: _method,
                reference: _note.text,
              ),
              _key,
            );
      if (!mounted) return;
      setState(() => _recorded = record);
      // The invoice as the server now has it (status and balance).
      await _loader.load();
    } catch (error) {
      if (mounted) setState(() => _error = billingErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: _refund ? t.billingRecordRefund : t.billingRecordPayment,
          description: _refund ? t.billingRefundIntro : t.billingPaymentIntro,
          actions: [
            HmsButton(
              label: t.billingBackToInvoice,
              icon: LucideIcons.arrowLeft,
              variant: HmsButtonVariant.secondary,
              onPressed: () =>
                  context.go(BillingRoutes.invoice(widget.invoiceId)),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        if (!_refund) ...[
          HmsAlert(title: t.billingNoGateway, message: t.billingNoGatewayBody),
          const SizedBox(height: AppSpacing.x4),
        ],
        RecordSection<Invoice>(
          loader: _loader,
          builder: (context, invoice) => _recorded != null
              ? _resultCard(t, invoice, _recorded!)
              : _formCard(t, invoice),
        ),
      ],
    );
  }

  Widget _formCard(AppLocalizations t, Invoice invoice) {
    final allowed = _refund
        ? mayRefund(_services.session.state, invoice)
        : mayCollectPayment(_services.session.state, invoice);
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: invoice.invoiceNumber ?? '#${invoice.id}',
            description: invoice.patientName,
            icon: LucideIcons.receiptIndianRupee,
            trailing: StatusBadge(status: invoice.status),
          ),
          HmsDividedColumn(
            children: [
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
          if (!allowed)
            HmsEmptyState(
              compact: true,
              icon: LucideIcons.lock,
              title: _refund
                  ? t.billingRefundNotAllowed
                  : t.billingPaymentNotAllowed,
            )
          else
            Padding(
              padding: const EdgeInsets.all(AppSpacing.x4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_error != null) ...[
                    HmsAlert(tone: AlertTone.danger, title: _error!),
                    const SizedBox(height: AppSpacing.x3),
                  ],
                  HmsTextField(
                    key: const Key('money-amount'),
                    label: t.billingAmount,
                    required: true,
                    prefixText: '₹ ',
                    controller: _amount,
                    error: _amountError,
                    enabled: !_saving,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                  ),
                  Text(t.billingPaymentMethod),
                  const SizedBox(height: AppSpacing.x2),
                  Wrap(
                    spacing: AppSpacing.x2,
                    runSpacing: AppSpacing.x2,
                    children: [
                      for (final method in paymentMethods)
                        ChoiceChip(
                          key: Key('method-$method'),
                          label: Text(paymentMethodLabel(t, method)),
                          selected: _method == method,
                          onSelected: _saving
                              ? null
                              : (_) => setState(() => _method = method),
                        ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.x3),
                  HmsTextField(
                    key: const Key('money-note'),
                    label: _refund ? t.billingRefundReason : t.billingReference,
                    hint: _refund ? null : t.billingReferenceHint,
                    required: _refund,
                    controller: _note,
                    error: _noteError,
                    enabled: !_saving,
                    maxLength: 200,
                    textInputAction: TextInputAction.done,
                  ),
                  HmsButton(
                    key: const Key('money-submit'),
                    label: _refund
                        ? t.billingRecordRefund
                        : t.billingRecordPayment,
                    variant: _refund
                        ? HmsButtonVariant.danger
                        : HmsButtonVariant.primary,
                    surface: HmsSurface.card,
                    expand: true,
                    loading: _saving,
                    onPressed: _saving ? null : () => _submit(invoice),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  /// What the server recorded (its amount, receipt and the new balance).
  Widget _resultCard(
    AppLocalizations t,
    Invoice invoice,
    InvoicePayment record,
  ) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(
          title: record.isRefund
              ? t.billingRefundRecorded
              : t.billingPaymentRecorded,
          icon: LucideIcons.circleCheck,
          trailing: StatusBadge(status: invoice.status),
        ),
        HmsDividedColumn(
          children: [
            DetailRow(label: t.billingReceipt, value: record.receiptNumber),
            DetailRow(
              label: t.billingAmount,
              value: formatRupees(record.amount),
            ),
            DetailRow(
              label: t.billingPaymentMethod,
              value: paymentMethodLabel(t, record.method),
            ),
            DetailRow(
              label: t.balanceDue,
              value: formatRupees(invoice.balanceDue),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: HmsButton(
            key: const Key('money-done'),
            label: t.billingBackToInvoice,
            surface: HmsSurface.card,
            expand: true,
            onPressed: () => context.go(BillingRoutes.invoice(invoice.id)),
          ),
        ),
      ],
    ),
  );
}
