import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../patient/data/record_models.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/dispense_plan.dart';
import '../data/pharmacy_models.dart';
import 'pharmacy_ui.dart';

/// One prescribed medicine: what the doctor wrote (read-only), what has
/// been issued, what is in stock, and — while some is still owed — the
/// batch and quantity to issue now.
class DispenseLineCard extends StatefulWidget {
  const DispenseLineCard({
    super.key,
    required this.item,
    required this.stock,
    required this.today,
    required this.line,
    required this.editable,
    required this.allowSubstitutes,
    required this.onChanged,
  });

  final PrescriptionItem item;
  final List<Medicine> stock;
  final DateTime today;
  final DispenseLine? line;
  final bool editable;

  /// Only a Pharmacist may give a same-salt substitute (server rule).
  final bool allowSubstitutes;
  final ValueChanged<DispenseLine> onChanged;

  @override
  State<DispenseLineCard> createState() => _DispenseLineCardState();
}

class _DispenseLineCardState extends State<DispenseLineCard> {
  late final _quantity = TextEditingController(
    text: '${widget.line?.quantity ?? 0}',
  );
  late final _reason = TextEditingController(text: widget.line?.reason ?? '');

  @override
  void dispose() {
    _quantity.dispose();
    _reason.dispose();
    super.dispose();
  }

  DispenseLine get _line => widget.line ?? const DispenseLine();

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final item = widget.item;
    final availability = availabilityOf(item, widget.stock, widget.today);
    final batches = usableBatches(widget.stock, item.name, widget.today);
    final substitutes = widget.allowSubstitutes
        ? substituteBatches(widget.stock, item.name, widget.today)
        : const <Medicine>[];
    final chosen = [
      ...batches,
      ...substitutes,
    ].where((m) => m.id == _line.batchId).firstOrNull;
    final isSubstitute =
        chosen != null &&
        chosen.name.trim().toLowerCase() != item.name.trim().toLowerCase();
    return HmsCard(
      padding: const EdgeInsets.all(AppSpacing.x4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item.name,
                  style: AppTypography.body(weight: FontWeight.w600),
                ),
              ),
              StatusBadge(
                status: switch (availability) {
                  Availability.done || Availability.inStock => 'Completed',
                  Availability.split || Availability.short => 'Held',
                  Availability.none => 'Cancelled',
                },
                label: availabilityLabel(t, availability),
              ),
            ],
          ),
          Text(
            [?item.dosage, ?item.frequency, ?item.duration].join(' · '),
            style: AppTypography.small(),
          ),
          if (item.instructions != null)
            Text(item.instructions!, style: AppTypography.caption()),
          const SizedBox(height: AppSpacing.x2),
          Text(
            t.prescribedIssuedLeft(
              item.quantity ?? 0,
              item.dispensedQuantity ?? 0,
              item.remaining,
            ),
            style: AppTypography.caption(),
          ),
          if (widget.editable) ...[
            const SizedBox(height: AppSpacing.x3),
            DropdownButtonFormField<int>(
              key: Key('batch-${item.id}'),
              initialValue: chosen?.id,
              isExpanded: true,
              decoration: InputDecoration(labelText: t.stockBatch),
              items: [
                for (final m in batches)
                  DropdownMenuItem(value: m.id, child: Text(_batchText(t, m))),
                for (final m in substitutes)
                  DropdownMenuItem(
                    value: m.id,
                    child: Text(
                      '${t.substitute}: ${m.name} · ${_batchText(t, m)}',
                    ),
                  ),
              ],
              onChanged: (id) => widget.onChanged(_line.copyWith(batchId: id)),
            ),
            if (batches.isEmpty && substitutes.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.x1),
                child: Text(t.noUsableBatch, style: AppTypography.caption()),
              ),
            const SizedBox(height: AppSpacing.x3),
            TextField(
              key: Key('qty-${item.id}'),
              controller: _quantity,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              decoration: InputDecoration(
                labelText: t.quantityNow,
                helperText: t.atMost(item.remaining),
              ),
              onChanged: (text) => widget.onChanged(
                _line.copyWith(quantity: int.tryParse(text) ?? 0),
              ),
            ),
            if (isSubstitute) ...[
              const SizedBox(height: AppSpacing.x3),
              TextField(
                key: Key('reason-${item.id}'),
                controller: _reason,
                decoration: InputDecoration(labelText: t.substituteReason),
                onChanged: (text) =>
                    widget.onChanged(_line.copyWith(reason: text)),
              ),
            ],
          ],
        ],
      ),
    );
  }

  String _batchText(AppLocalizations t, Medicine m) => [
    if (m.batch != null) t.batchCode(m.batch!),
    t.inStockCount(m.quantity, m.unit ?? ''),
    if (m.expiryDate != null) t.expiresOn(formatDay(t, m.expiryDate)),
  ].join(' · ');
}
