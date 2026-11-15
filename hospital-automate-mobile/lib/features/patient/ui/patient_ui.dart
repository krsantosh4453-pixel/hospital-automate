import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_body.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../record_loader.dart';

/// Bills show paise, as the web's invoice pages do.
final rupeesWithPaise = NumberFormat.currency(
  locale: 'en_IN',
  symbol: '₹',
  decimalDigits: 2,
);

String formatRupees(double? amount) =>
    amount == null ? '—' : rupeesWithPaise.format(amount);

String formatDay(AppLocalizations t, DateTime? day) =>
    day == null ? '—' : DateFormat.yMMMd(t.localeName).format(day);

String formatDateTime(AppLocalizations t, DateTime? when) => when == null
    ? '—'
    : DateFormat.yMMMd(t.localeName).add_jm().format(when.toLocal());

String formatClock(AppLocalizations t, DateTime? when) =>
    when == null ? '—' : DateFormat.jm(t.localeName).format(when.toLocal());

/// A server status in the reader's language; unknown values are shown as sent.
String statusLabel(AppLocalizations t, String status) => switch (status) {
  'Scheduled' => t.statusScheduled,
  'Checked In' => t.statusCheckedIn,
  'In Consultation' => t.statusInConsultation,
  'Completed' => t.statusCompleted,
  'Cancelled' => t.statusCancelled,
  'No Show' => t.statusNoShow,
  'Waiting' => t.statusWaiting,
  'Called' => t.statusCalled,
  'Acknowledged' => t.statusAcknowledged,
  'Ready' => t.statusReady,
  'Confirmed' => t.statusConfirmed,
  'Pending' => t.statusPending,
  'Dispensed' => t.statusDispensed,
  'Partially Dispensed' => t.statusPartiallyDispensed,
  'Released' => t.statusReleased,
  'Unpaid' => t.statusUnpaid,
  'Partially Paid' => t.statusPartiallyPaid,
  'Paid' => t.statusPaid,
  _ => status.isEmpty ? '—' : status,
};

AlertTone _toneFor(String status) => switch (status) {
  'Completed' ||
  'Paid' ||
  'Released' ||
  'Dispensed' ||
  'Ready' => AlertTone.success,
  'Cancelled' || 'No Show' => AlertTone.danger,
  'Unpaid' ||
  'Partially Paid' ||
  'Called' ||
  'Partially Dispensed' => AlertTone.warning,
  _ => AlertTone.info,
};

/// StatusBadge (Data.jsx): a small rounded label in the status colour.
class StatusBadge extends StatelessWidget {
  const StatusBadge({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(status);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.x2,
        vertical: 2,
      ),
      decoration: BoxDecoration(
        color: tone.fill,
        border: Border.all(color: tone.border),
        borderRadius: const BorderRadius.all(Radius.circular(999)),
      ),
      child: Text(
        statusLabel(context.l10n, status),
        style: AppTypography.caption(weight: FontWeight.w600, color: tone.text),
      ),
    );
  }
}

/// The month and day of an appointment in a small tile (web date chip).
class DayTile extends StatelessWidget {
  const DayTile({super.key, required this.day});

  final DateTime? day;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final when = day;
    // A minimum, not a fixed size, so large text grows the tile instead of overflowing.
    return Container(
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
      padding: const EdgeInsets.all(AppSpacing.x1),
      decoration: const BoxDecoration(
        color: AppColors.cardTintBrand,
        borderRadius: BorderRadius.all(Radius.circular(AppRadii.xl)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            when == null ? '' : DateFormat.MMM(t.localeName).format(when),
            style: AppTypography.caption(weight: FontWeight.w600),
          ),
          Text(
            when == null ? '—' : '${when.day}',
            style: AppTypography.body(weight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

/// A labelled value inside a card (`dl` rows on the web).
class DetailRow extends StatelessWidget {
  const DetailRow({super.key, required this.label, required this.value});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) {
    final shown = value == null || value!.trim().isEmpty ? '—' : value!;
    return Padding(
      padding: AppSpacing.cardRow,
      child: MergeSemantics(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 2, child: Text(label, style: AppTypography.small())),
            const SizedBox(width: AppSpacing.x3),
            Expanded(
              flex: 3,
              child: Text(
                shown,
                style: AppTypography.body(weight: FontWeight.w500),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Renders a [RecordLoader]: skeleton on the first load, an error card with
/// retry when nothing could be loaded, otherwise [builder]. A failed refresh
/// keeps the last data and shows a warning above it.
class RecordSection<T> extends StatelessWidget {
  const RecordSection({
    super.key,
    required this.loader,
    required this.builder,
    this.skeletons = 3,
  });

  final RecordLoader<T> loader;
  final Widget Function(BuildContext context, T data) builder;
  final int skeletons;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: loader,
      builder: (context, _) {
        final data = loader.data;
        final error = loader.error;
        if (data == null && error != null) {
          return HmsCard(
            child: HmsErrorState(error: error, onRetry: loader.load),
          );
        }
        if (data == null) {
          return Column(
            children: [
              for (var i = 0; i < skeletons; i++) ...[
                if (i > 0) const SizedBox(height: AppSpacing.x3),
                const HmsSkeleton(height: 72),
              ],
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (error != null) ...[
              HmsAlert(
                tone: AlertTone.warning,
                title: context.l10n.refreshFailed,
                message: apiErrorMessage(context.l10n, error),
              ),
              const SizedBox(height: AppSpacing.x4),
            ],
            builder(context, data),
          ],
        );
      },
    );
  }
}

/// A patient page: the page body, rebuilt from scratch when the patient
/// switches hospital so no record of the previous hospital stays on screen.
class PatientPage extends StatelessWidget {
  const PatientPage({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final session = AppScope.of(context).session;
    return ListenableBuilder(
      listenable: session,
      builder: (context, _) => PageBody(
        location: location,
        children: [
          KeyedSubtree(
            key: ValueKey('hospital-${session.activeHospitalId}'),
            child: child,
          ),
        ],
      ),
    );
  }
}
