import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/record_picker.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/data/doctor_models.dart' show PatientSummary;
import '../../laboratory/ui/lab_new_order_screen.dart' show patientSubtitle;
import '../../laboratory/ui/lab_ui.dart' show outcomeUnknown;
import '../data/billing_models.dart';
import 'billing_ui.dart';

/// Line presets the desk may add by hand. Medicine is billed by the
/// pharmacy itself (one invoice line per sale), so it is not offered here.
const _presets = [
  ChargeSource.consultation,
  ChargeSource.laboratory,
  ChargeSource.other,
];

/// Most lines one bill takes from the phone.
const _maxLines = 10;

/// GST percent ceiling (InvoiceItem tax_rate 0–100), in hundredths.
const _maxTaxPaise = 10000;

class _LineInput {
  _LineInput(String description)
    : description = TextEditingController(text: description);

  final TextEditingController description;
  final quantity = TextEditingController(text: '1');
  final price = TextEditingController();
  final tax = TextEditingController(text: '0');
  String? error;

  void dispose() {
    description.dispose();
    quantity.dispose();
    price.dispose();
    tax.dispose();
  }

  /// This line for the server, or null after setting [error].
  InvoiceDraftLine? read(AppLocalizations t) {
    final qty = int.tryParse(quantity.text.trim());
    final unit = normalizeAmount(price.text);
    final rate = normalizeAmountOrZero(tax.text);
    if (description.text.trim().isEmpty) {
      error = t.billingLineDescriptionRequired;
    } else if (qty == null || qty < 1) {
      error = t.billingQuantityInvalid;
    } else if (unit == null) {
      error = t.billingAmountInvalid;
    } else if (rate == null || amountInPaise(rate) > _maxTaxPaise) {
      error = t.billingTaxRateInvalid;
    } else {
      error = null;
      return InvoiceDraftLine(
        description: description.text,
        quantity: qty,
        unitPrice: unit,
        taxRate: rate,
      );
    }
    return null;
  }
}

/// `/billing/new`: patient, lines and discount. Totals, GST, the status and
/// the invoice number are set by the server; nothing is added up here.
class NewInvoiceScreen extends StatefulWidget {
  const NewInvoiceScreen({super.key});

  @override
  State<NewInvoiceScreen> createState() => _NewInvoiceScreenState();
}

class _NewInvoiceScreenState extends State<NewInvoiceScreen> {
  late final _services = AppScope.read(context);
  final List<_LineInput> _lines = [
    _LineInput(chargeSourceDescriptions[ChargeSource.consultation]!),
  ];
  final _discount = TextEditingController(text: '0');
  PatientSummary? _patient;
  bool _saving = false;

  /// Set when the last attempt got no answer: the invoice may exist already.
  bool _maybeCreated = false;
  String? _error;

  @override
  void dispose() {
    for (final line in _lines) {
      line.dispose();
    }
    _discount.dispose();
    super.dispose();
  }

  /// The draft, or null after marking what is wrong.
  InvoiceDraft? _draft(AppLocalizations t) {
    final hospital = _services.session.activeHospitalId;
    final lines = [for (final line in _lines) line.read(t)];
    final discount = normalizeAmountOrZero(_discount.text);
    final patient = _patient;
    if (patient == null) {
      _error = t.billingChoosePatient;
    } else if (lines.contains(null)) {
      _error = t.fixHighlightedFields;
    } else if (discount == null) {
      _error = t.billingDiscountRefused;
    } else {
      _error = null;
    }
    if (_error != null || hospital == null) return null;
    return InvoiceDraft(
      hospitalId: hospital,
      patientId: patient!.id,
      lines: lines.whereType<InvoiceDraftLine>().toList(),
      discount: discount!,
    );
  }

  Future<void> _submit() async {
    if (_saving || _maybeCreated) return;
    final t = context.l10n;
    final draft = _draft(t);
    setState(() {});
    if (draft == null) return;
    setState(() => _saving = true);
    try {
      final invoice = await _services.billing.createInvoice(draft);
      if (mounted) context.go(BillingRoutes.invoice(invoice.id));
    } catch (error) {
      if (!mounted) return;
      setState(() {
        // The server has no idempotency for invoices: never resend blindly.
        _maybeCreated = outcomeUnknown(error);
        _error = _maybeCreated
            ? t.billingInvoiceMaybeCreated
            : billingErrorMessage(t, error);
      });
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    if (!mayCreateInvoices(_services.session.state)) {
      return HmsCard(
        child: HmsEmptyState(
          icon: LucideIcons.lock,
          title: t.notEligibleForPage,
          description: t.billingCreateNotAllowed,
        ),
      );
    }
    final small = Theme.of(context).textTheme.bodySmall;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.billingNewInvoice,
          description: t.billingNewInvoiceIntro,
        ),
        const SizedBox(height: AppSpacing.x4),
        if (_error != null) ...[
          HmsAlert(
            tone: _maybeCreated ? AlertTone.warning : AlertTone.danger,
            title: _error!,
            action: _maybeCreated
                ? HmsButton(
                    label: t.billingOpenInvoiceList,
                    surface: HmsSurface.card,
                    onPressed: () => context.go(BillingRoutes.desk),
                  )
                : null,
          ),
          const SizedBox(height: AppSpacing.x4),
        ],
        HmsCard(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: RecordPicker<PatientSummary>(
            hint: t.billingPatientSearchHint,
            search: _services.billing.searchPatients,
            selected: _patient,
            minChars: 2,
            enabled: !_saving,
            title: (p) => p.name,
            subtitle: patientSubtitle,
            onSelected: (p) => setState(() => _patient = p),
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        for (var i = 0; i < _lines.length; i++) ...[
          _lineCard(t, i),
          const SizedBox(height: AppSpacing.x3),
        ],
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final source in _presets)
              ActionChip(
                key: Key('add-line-${source.name}'),
                avatar: const Icon(LucideIcons.plus, size: 16),
                label: Text(_presetLabel(t, source)),
                onPressed: _saving || _lines.length >= _maxLines
                    ? null
                    : () => setState(
                        () => _lines.add(
                          _LineInput(chargeSourceDescriptions[source]!),
                        ),
                      ),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x2),
        Text(t.billingPharmacyAutomatic, style: small),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsTextField(
                key: const Key('invoice-discount'),
                label: t.billingDiscount,
                prefixText: '₹ ',
                hint: t.billingDiscountHint,
                controller: _discount,
                enabled: !_saving,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
              ),
              Text(t.billingServerTotals, style: small),
              const SizedBox(height: AppSpacing.x3),
              HmsButton(
                key: const Key('invoice-submit'),
                label: t.billingCreateInvoice,
                surface: HmsSurface.card,
                expand: true,
                loading: _saving,
                onPressed: _saving || _maybeCreated ? null : _submit,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _lineCard(AppLocalizations t, int index) {
    final line = _lines[index];
    TextInputType decimal() =>
        const TextInputType.numberWithOptions(decimal: true);
    return HmsCard(
      padding: const EdgeInsets.all(AppSpacing.x4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  t.billingLineNumber(index + 1),
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
              if (_lines.length > 1)
                IconButton(
                  tooltip: t.billingRemoveLine,
                  icon: const Icon(LucideIcons.trash2),
                  onPressed: _saving
                      ? null
                      : () => setState(() => _lines.removeAt(index).dispose()),
                ),
            ],
          ),
          if (line.error != null) ...[
            HmsAlert(tone: AlertTone.danger, title: line.error!),
            const SizedBox(height: AppSpacing.x2),
          ],
          HmsTextField(
            key: Key('line-description-$index'),
            label: t.billingLineDescription,
            required: true,
            controller: line.description,
            enabled: !_saving,
            maxLength: 200,
          ),
          HmsTextField(
            key: Key('line-price-$index'),
            label: t.billingUnitPrice,
            required: true,
            prefixText: '₹ ',
            controller: line.price,
            enabled: !_saving,
            keyboardType: decimal(),
          ),
          Row(
            children: [
              Expanded(
                child: HmsTextField(
                  key: Key('line-quantity-$index'),
                  label: t.quantity,
                  controller: line.quantity,
                  enabled: !_saving,
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpacing.x2),
              Expanded(
                child: HmsTextField(
                  key: Key('line-tax-$index'),
                  label: t.billingGstPercent,
                  controller: line.tax,
                  enabled: !_saving,
                  keyboardType: decimal(),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  static String _presetLabel(AppLocalizations t, ChargeSource s) => switch (s) {
    ChargeSource.consultation => t.billingChargeConsultation,
    ChargeSource.laboratory => t.billingChargeLaboratory,
    ChargeSource.pharmacy => t.billingChargePharmacy,
    ChargeSource.other => t.billingChargeOther,
  };
}
