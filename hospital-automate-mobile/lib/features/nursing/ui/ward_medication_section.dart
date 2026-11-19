import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/nursing_models.dart';
import 'nursing_ui.dart';
import 'ward_patient_screen.dart';
import 'ward_widgets.dart';

/// Doses a nurse records against the doctor's medication orders.
///
/// Safety: the app never changes an order, its dose or its instructions;
/// every outcome is confirmed against the patient's name and UHID first;
/// a dose shows as recorded only after the server confirms it; a dose
/// already being sent cannot be tapped again; and the server refuses a dose
/// already recorded (by anyone) or whose order is no longer in force.
class WardMedicationSection extends StatefulWidget {
  const WardMedicationSection({super.key, required this.ward});

  final WardContext ward;

  @override
  State<WardMedicationSection> createState() => _WardMedicationSectionState();
}

class _WardMedicationSectionState extends State<WardMedicationSection> {
  WardContext get _w => widget.ward;
  late final RecordLoader<List<MedicationOrder>> _loader = RecordLoader(
    () => _w.repository.medicationOrders(_w.patient.id),
  );

  /// Doses whose outcome is being sent; their buttons are disabled.
  final Set<int> _sending = {};
  String? _error;
  String? _done;

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

  Future<void> _record(Dose dose, DoseAction action) async {
    if (_sending.contains(dose.id)) return;
    final t = context.l10n;
    final reason = await confirmDose(
      context,
      ward: _w,
      dose: dose,
      action: action,
    );
    if (reason == null || !mounted) return;
    setState(() {
      _sending.add(dose.id);
      _error = null;
      _done = null;
    });
    try {
      final saved = await _w.repository.recordDose(
        dose.id,
        action,
        reason: reason,
      );
      if (mounted) {
        setState(
          () => _done = t.doseRecorded(
            saved.medicineName,
            doseStatusLabel(t, saved.status),
            formatClock(t, saved.recordedAt),
          ),
        );
      }
    } catch (error) {
      if (mounted) setState(() => _error = doseErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _sending.remove(dose.id));
      // Whatever happened, show what the server now holds.
      await _loader.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return WardSectionCard(
      title: t.medicationAdministration,
      icon: LucideIcons.pill,
      list: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.x4),
              child: HmsAlert(tone: AlertTone.danger, title: _error!),
            ),
          if (_done != null)
            Padding(
              padding: const EdgeInsets.all(AppSpacing.x4),
              child: HmsAlert(tone: AlertTone.success, title: _done!),
            ),
          RecordSection<List<MedicationOrder>>(
            loader: _loader,
            skeletons: 1,
            builder: (context, orders) {
              final active = [
                for (final o in orders)
                  if (o.isActive) o,
              ];
              if (active.isEmpty) {
                return HmsEmptyState(
                  compact: true,
                  title: t.noMedicationOrders,
                  description: t.medicationOrdersByDoctor,
                );
              }
              return HmsDividedColumn(
                children: [
                  for (final order in active)
                    _OrderTile(
                      order: order,
                      sending: _sending,
                      onRecord: _record,
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _OrderTile extends StatelessWidget {
  const _OrderTile({
    required this.order,
    required this.sending,
    required this.onRecord,
  });

  final MedicationOrder order;
  final Set<int> sending;
  final void Function(Dose dose, DoseAction action) onRecord;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final due =
        [
          for (final d in order.doses)
            if (d.isDue) d,
        ]..sort(
          (a, b) => (a.scheduledAt ?? DateTime(0)).compareTo(
            b.scheduledAt ?? DateTime(0),
          ),
        );
    final recorded =
        [
          for (final d in order.doses)
            if (!d.isDue) d,
        ]..sort(
          (a, b) => (b.recordedAt ?? DateTime(0)).compareTo(
            a.recordedAt ?? DateTime(0),
          ),
        );
    return Padding(
      padding: AppSpacing.cardRow,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            order.medicineName,
            style: AppTypography.body(weight: FontWeight.w600),
          ),
          Text(
            [?order.dose, ?order.route, ?order.frequency].join(' · '),
            style: AppTypography.small(),
          ),
          if (order.orderedByName != null)
            Text(
              '${t.orderedBy}: ${order.orderedByName}',
              style: AppTypography.caption(),
            ),
          const SizedBox(height: AppSpacing.x2),
          if (due.isEmpty)
            Text(t.noDosesDue, style: AppTypography.caption())
          else
            for (final dose in due.take(3))
              _DueDose(
                dose: dose,
                busy: sending.contains(dose.id),
                onRecord: onRecord,
              ),
          for (final dose in recorded.take(2))
            Text(
              '${doseStatusLabel(t, dose.status)} · '
              '${formatDateTime(t, dose.recordedAt)}'
              '${dose.givenByName == null ? '' : ' · ${dose.givenByName}'}',
              style: AppTypography.caption(),
            ),
        ],
      ),
    );
  }
}

class _DueDose extends StatelessWidget {
  const _DueDose({
    required this.dose,
    required this.busy,
    required this.onRecord,
  });

  final Dose dose;
  final bool busy;
  final void Function(Dose dose, DoseAction action) onRecord;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    String label(DoseAction a) => switch (a) {
      DoseAction.administer => t.markGiven,
      DoseAction.hold => t.markHeld,
      DoseAction.refuse => t.markRefused,
      DoseAction.missed => t.markMissed,
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.x3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  t.doseDueAt(formatDateTime(t, dose.scheduledAt)),
                  style: AppTypography.small(),
                ),
              ),
              if (dose.isDelayed)
                StatusBadge(status: 'Held', label: t.dosesOverdue),
            ],
          ),
          const SizedBox(height: AppSpacing.x2),
          Wrap(
            spacing: AppSpacing.x2,
            runSpacing: AppSpacing.x2,
            children: [
              for (final action in DoseAction.values)
                HmsButton(
                  key: Key('dose-${dose.id}-${action.name}'),
                  label: label(action),
                  size: HmsButtonSize.small,
                  surface: HmsSurface.card,
                  loading: busy && action == DoseAction.administer,
                  variant: action == DoseAction.administer
                      ? HmsButtonVariant.primary
                      : HmsButtonVariant.secondary,
                  onPressed: busy ? null : () => onRecord(dose, action),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Asks the nurse to check the patient, medicine, dose and route before an
/// outcome is sent. Returns the reason typed (empty when none is needed),
/// or null when cancelled.
Future<String?> confirmDose(
  BuildContext context, {
  required WardContext ward,
  required Dose dose,
  required DoseAction action,
}) {
  final t = context.l10n;
  return showHmsModal<String>(
    context,
    title: switch (action) {
      DoseAction.administer => t.confirmGiveTitle,
      DoseAction.hold => t.confirmHoldTitle,
      DoseAction.refuse => t.confirmRefuseTitle,
      DoseAction.missed => t.confirmMissedTitle,
    },
    description: t.checkPatientBeforeDose,
    body: _DoseConfirmForm(ward: ward, dose: dose, action: action),
  );
}

class _DoseConfirmForm extends StatefulWidget {
  const _DoseConfirmForm({
    required this.ward,
    required this.dose,
    required this.action,
  });

  final WardContext ward;
  final Dose dose;
  final DoseAction action;

  @override
  State<_DoseConfirmForm> createState() => _DoseConfirmFormState();
}

class _DoseConfirmFormState extends State<_DoseConfirmForm> {
  final _reason = TextEditingController();

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final dose = widget.dose;
    final needsReason = widget.action.needsReason;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCard(
          child: HmsDividedColumn(
            children: [
              DetailRow(label: t.patientLabel, value: widget.ward.identity(t)),
              DetailRow(label: t.medicineName, value: dose.medicineName),
              DetailRow(label: t.dosage, value: dose.dose),
              DetailRow(label: t.route, value: dose.route),
              DetailRow(
                label: t.scheduledFor,
                value: formatDateTime(t, dose.scheduledAt),
              ),
            ],
          ),
        ),
        if (needsReason) ...[
          const SizedBox(height: AppSpacing.x3),
          TextField(
            key: const Key('dose-reason'),
            controller: _reason,
            maxLines: 2,
            decoration: InputDecoration(labelText: t.reasonRequired),
            onChanged: (_) => setState(() {}),
          ),
        ],
        const SizedBox(height: AppSpacing.x4),
        Wrap(
          alignment: WrapAlignment.end,
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            HmsButton(
              label: t.cancel,
              variant: HmsButtonVariant.secondary,
              surface: HmsSurface.card,
              onPressed: () => Navigator.of(context).pop(),
            ),
            HmsButton(
              key: const Key('confirm-dose'),
              label: t.confirm,
              surface: HmsSurface.card,
              onPressed: needsReason && _reason.text.trim().isEmpty
                  ? null
                  : () => Navigator.of(context).pop(_reason.text.trim()),
            ),
          ],
        ),
      ],
    );
  }
}
