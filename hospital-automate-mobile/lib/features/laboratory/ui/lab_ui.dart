import 'package:flutter/material.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/data/record_models.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/lab_workflow.dart';

/// Laboratory pages (staff paths, as on the web).
abstract final class LabRoutes {
  static const worklist = '/laboratory';
  static const newOrder = '/laboratory/new';

  static String order(int id) => '$worklist/$id';
}

/// A lab status in the reader's language; other values fall back to
/// [statusLabel] (Released, Cancelled) or are shown as sent.
String labStatusLabel(AppLocalizations t, String status) => switch (status) {
  LabStatus.ordered => t.labStatusOrdered,
  LabStatus.samplePending => t.labStatusSamplePending,
  LabStatus.collected => t.labStatusCollected,
  LabStatus.dispatched => t.labStatusDispatched,
  LabStatus.received => t.labStatusReceived,
  LabStatus.processing => t.labStatusProcessing,
  LabStatus.resultEntered => t.labStatusResultEntered,
  LabStatus.verified => t.labStatusVerified,
  _ => statusLabel(t, status),
};

/// The button label for a workflow step.
String labStepLabel(AppLocalizations t, LabStep step) => switch (step) {
  LabStep.collect => t.labStepCollect,
  LabStep.dispatch => t.labStepDispatch,
  LabStep.receive => t.labStepReceive,
  LabStep.startProcessing => t.labStepStartProcessing,
  LabStep.enterResult => t.labStepEnterResult,
  LabStep.verify => t.labStepVerify,
  LabStep.release => t.labStepRelease,
};

String labQueueLabel(AppLocalizations t, LabQueue queue) => switch (queue) {
  LabQueue.awaitingCollection => t.labQueueAwaitingCollection,
  LabQueue.sampleCollected => t.labQueueSampleCollected,
  LabQueue.inProgress => t.labQueueInProgress,
  LabQueue.awaitingRelease => t.labQueueAwaitingRelease,
  LabQueue.released => t.labQueueReleased,
  LabQueue.cancelled => t.labQueueCancelled,
};

/// A safe sentence for a refused laboratory write. A 400 without field
/// errors is the server refusing the step for the test's current status
/// (someone else moved it on); the server's own text is never shown.
String labErrorMessage(AppLocalizations t, Object error) {
  if (error is ApiException &&
      error.kind == ApiErrorKind.validation &&
      error.fieldErrors.isEmpty) {
    return t.labStepRefused;
  }
  if (error is ApiException && error.kind == ApiErrorKind.validation) {
    return t.checkTheseFields(error.fieldErrors.keys.join(', '));
  }
  return apiErrorMessage(t, error);
}

/// Whether a failed write may still have reached the server (no answer came
/// back), so repeating it could create a second record.
bool outcomeUnknown(Object error) =>
    error is ApiException &&
    (error.kind == ApiErrorKind.timeout ||
        error.kind == ApiErrorKind.network ||
        error.kind == ApiErrorKind.unknown);

/// A rounded label in an alert tone, styled like [StatusBadge], for texts
/// that are not server statuses (or statuses [StatusBadge] has no colour for).
class ToneBadge extends StatelessWidget {
  const ToneBadge({super.key, required this.label, required this.tone});

  final String label;
  final AlertTone tone;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.x2, vertical: 2),
    decoration: BoxDecoration(
      color: tone.fill,
      border: Border.all(color: tone.border),
      borderRadius: const BorderRadius.all(Radius.circular(999)),
    ),
    child: Text(
      label,
      style: AppTypography.caption(weight: FontWeight.w600, color: tone.text),
    ),
  );
}

/// The lab status as a coloured badge.
class LabStatusBadge extends StatelessWidget {
  const LabStatusBadge({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) => ToneBadge(
    label: labStatusLabel(context.l10n, status),
    tone: switch (status) {
      LabStatus.released => AlertTone.success,
      LabStatus.cancelled => AlertTone.danger,
      LabStatus.verified => AlertTone.success,
      _ => AlertTone.info,
    },
  );
}

/// Eight segments, filled up to the test's stage (web progress indicator).
class LabProgress extends StatelessWidget {
  const LabProgress({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final stage = labStageIndex(status);
    final done = status == LabStatus.released;
    return Semantics(
      label: context.l10n.labProgressLabel(stage + 1, LabStatus.stages.length),
      child: ExcludeSemantics(
        child: Row(
          children: [
            for (var i = 0; i < LabStatus.stages.length; i++) ...[
              if (i > 0) const SizedBox(width: 3),
              Expanded(
                child: Container(
                  height: 6,
                  decoration: BoxDecoration(
                    borderRadius: const BorderRadius.all(Radius.circular(99)),
                    color: i <= stage
                        ? (done ? AppColors.green500 : AppColors.brand500)
                        : AppColors.ink200,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// One order in the worklist: test, patient, date, sample number, status.
class LabOrderRow extends StatelessWidget {
  const LabOrderRow({super.key, required this.test, this.onTap});

  final LabTest test;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final urgent = test.priority == 'Urgent';
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    test.name,
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                ),
                if (urgent) ...[
                  ToneBadge(label: t.statusUrgent, tone: AlertTone.danger),
                  const SizedBox(width: AppSpacing.x1),
                ],
                LabStatusBadge(status: test.status),
              ],
            ),
            const SizedBox(height: 2),
            Text(
              [
                ?test.patientName,
                formatDay(t, test.testDate),
                if (test.sample != null) test.sample!.sampleId,
              ].join(' · '),
              style: AppTypography.small(),
            ),
            if (test.status != LabStatus.cancelled) ...[
              const SizedBox(height: AppSpacing.x2),
              LabProgress(status: test.status),
            ],
          ],
        ),
      ),
    );
  }
}
