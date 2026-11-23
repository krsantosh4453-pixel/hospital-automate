import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/lab_workflow.dart';
import 'lab_step_forms.dart';
import 'lab_ui.dart';

/// `/laboratory/<id>`: one order, its sample trail and result, and the one
/// next step the server accepts, offered only to roles the server allows.
/// After every step the order is read again from the server.
class LabOrderScreen extends StatefulWidget {
  const LabOrderScreen({super.key, required this.orderId});

  final int orderId;

  @override
  State<LabOrderScreen> createState() => _LabOrderScreenState();
}

class _LabOrderScreenState extends State<LabOrderScreen> {
  late final _services = AppScope.read(context);
  late final RecordLoader<LabTest> _loader = RecordLoader(
    () => _services.laboratory.order(widget.orderId),
  );
  bool _busy = false;
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

  Future<void> _run(LabTest test, LabStep step) async {
    if (_busy) return;
    final t = context.l10n;
    final body = await askForLabStep(context, test, step);
    if (body == null || !mounted) return;
    await _write(
      () => _services.laboratory.advance(test.id, step, body),
      t.labStepDone(labStepLabel(t, step)),
    );
  }

  Future<void> _cancel(LabTest test) async {
    if (_busy) return;
    final t = context.l10n;
    final ok = await showHmsConfirm(
      context,
      title: t.labCancelOrder,
      message: t.labCancelConfirm(test.name),
      confirmLabel: t.labCancelOrder,
      destructive: true,
    );
    if (!ok || !mounted) return;
    await _write(
      () => _services.laboratory.cancel(test.id),
      t.labOrderCancelled,
    );
  }

  /// Sends one write, then shows the order as the server now has it.
  Future<void> _write(Future<LabTest> Function() send, String doneText) async {
    final t = context.l10n;
    setState(() {
      _busy = true;
      _error = null;
      _done = null;
    });
    try {
      await send();
      if (mounted) setState(() => _done = doneText);
    } catch (error) {
      if (mounted) setState(() => _error = labErrorMessage(t, error));
    } finally {
      // Read back either way: a refused step usually means the order moved on.
      await _loader.load();
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.labOrderTitle,
          actions: [
            HmsButton(
              label: t.labBackToWorklist,
              icon: LucideIcons.arrowLeft,
              variant: HmsButtonVariant.secondary,
              onPressed: () => context.go(LabRoutes.worklist),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        if (_error != null) ...[
          HmsAlert(tone: AlertTone.danger, title: _error!),
          const SizedBox(height: AppSpacing.x3),
        ],
        if (_done != null) ...[
          HmsAlert(tone: AlertTone.success, title: _done!),
          const SizedBox(height: AppSpacing.x3),
        ],
        RecordSection<LabTest>(
          loader: _loader,
          builder: (context, test) => _details(context, test),
        ),
      ],
    );
  }

  Widget _details(BuildContext context, LabTest test) {
    final t = context.l10n;
    final session = _services.session.state;
    final step = nextLabStep(test.status);
    final canStep = step != null && mayRunLabStep(session, step);
    final canCancel = mayCancelLabOrder(session, test.status);
    final canReject =
        mayRejectLabResult(test.status) &&
        mayRunLabStep(session, LabStep.reject);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: test.name,
                description: test.patientName,
                icon: LucideIcons.flaskConical,
                trailing: LabStatusBadge(status: test.status),
              ),
              if (test.status != LabStatus.cancelled)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.x4,
                  ),
                  child: LabProgress(status: test.status),
                ),
              HmsDividedColumn(
                children: [
                  DetailRow(
                    label: t.priority,
                    value: test.priority == 'Urgent'
                        ? t.statusUrgent
                        : test.priority,
                  ),
                  DetailRow(label: t.orderedBy, value: test.doctorName),
                  DetailRow(label: t.hospital, value: test.hospitalName),
                ],
              ),
              if (canStep || canCancel || canReject)
                Padding(
                  padding: const EdgeInsets.all(AppSpacing.x4),
                  child: Wrap(
                    spacing: AppSpacing.x2,
                    runSpacing: AppSpacing.x2,
                    children: [
                      if (canStep)
                        HmsButton(
                          key: const Key('lab-next-step'),
                          label: labStepLabel(t, step),
                          surface: HmsSurface.card,
                          loading: _busy,
                          onPressed: _busy ? null : () => _run(test, step),
                        ),
                      if (canReject)
                        HmsButton(
                          key: const Key('lab-reject'),
                          label: t.labStepReject,
                          variant: HmsButtonVariant.secondary,
                          surface: HmsSurface.card,
                          onPressed: _busy
                              ? null
                              : () => _run(test, LabStep.reject),
                        ),
                      if (canCancel)
                        HmsButton(
                          key: const Key('lab-cancel'),
                          label: t.labCancelOrder,
                          variant: HmsButtonVariant.danger,
                          surface: HmsSurface.card,
                          onPressed: _busy ? null : () => _cancel(test),
                        ),
                    ],
                  ),
                )
              else if (step != null)
                Padding(
                  padding: const EdgeInsets.all(AppSpacing.x4),
                  child: Text(t.labNextStepByOthers(labStepLabel(t, step))),
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        _Timeline(test: test),
        if (test.sample != null) ...[
          const SizedBox(height: AppSpacing.x4),
          _SampleCard(sample: test.sample!, dispatch: test.dispatch),
        ],
        const SizedBox(height: AppSpacing.x4),
        _ResultCard(test: test),
      ],
    );
  }
}

class _Timeline extends StatelessWidget {
  const _Timeline({required this.test});

  final LabTest test;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    String when(DateTime? at) => formatDateTime(t, at);
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.labTimeline, icon: LucideIcons.history),
          HmsDividedColumn(
            children: [
              DetailRow(
                label: t.labStatusOrdered,
                value: formatDay(t, test.testDate),
              ),
              DetailRow(
                label: t.labStatusCollected,
                value: when(test.collectedAt),
              ),
              DetailRow(
                label: t.labStatusDispatched,
                value: when(test.dispatchedAt),
              ),
              DetailRow(
                label: t.labStatusReceived,
                value: when(test.receivedAt),
              ),
              DetailRow(
                label: t.labStatusProcessing,
                value: when(test.processedAt),
              ),
              DetailRow(
                label: t.labStatusVerified,
                value: when(test.verifiedAt),
              ),
              DetailRow(label: t.releasedOn, value: when(test.releasedAt)),
            ],
          ),
        ],
      ),
    );
  }
}

class _SampleCard extends StatelessWidget {
  const _SampleCard({required this.sample, this.dispatch});

  final LabSample sample;
  final LabDispatch? dispatch;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final trip = dispatch;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.labSample, icon: LucideIcons.testTube),
          HmsDividedColumn(
            children: [
              DetailRow(label: t.labSampleNumber, value: sample.sampleId),
              DetailRow(label: t.labSampleType, value: sample.sampleType),
              DetailRow(label: t.labContainerType, value: sample.containerType),
              DetailRow(label: t.labCollectedBy, value: sample.collectedByName),
              DetailRow(
                label: t.labCollectedAt,
                value: formatDateTime(t, sample.collectedAt),
              ),
              DetailRow(label: t.labCollectionNotes, value: sample.notes),
              if (trip != null) ...[
                DetailRow(
                  label: t.labDispatchedBy,
                  value: trip.dispatchedByName,
                ),
                DetailRow(label: t.labReceivedBy, value: trip.receivedByName),
                DetailRow(label: t.labExternalLab, value: trip.externalLab),
                DetailRow(label: t.labDispatchNotes, value: trip.notes),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

/// The result exactly as the laboratory entered it; flags and ranges are
/// the laboratory's own, never interpreted here.
class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.test});

  final LabTest test;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final result = test.result;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.results,
            icon: LucideIcons.clipboardList,
            trailing: result == null
                ? null
                : ToneBadge(
                    label: result.isVerified
                        ? t.labResultVerified
                        : t.labResultAwaitingVerification,
                    tone: result.isVerified
                        ? AlertTone.success
                        : AlertTone.warning,
                  ),
          ),
          if (result == null || result.isEmpty)
            HmsEmptyState(compact: true, title: t.labNoResultYet)
          else
            HmsDividedColumn(
              children: [
                for (final entry in result.values.entries)
                  DetailRow(
                    label: entry.key,
                    value: [
                      entry.value,
                      if (result.flags[entry.key] != null)
                        '(${result.flags[entry.key]})',
                      if (result.referenceRanges[entry.key] != null)
                        '· ${t.referenceRange}: '
                            '${result.referenceRanges[entry.key]}',
                    ].join(' '),
                  ),
                if (result.text != null)
                  DetailRow(label: t.labResultText, value: result.text),
                DetailRow(label: t.labEnteredBy, value: result.enteredByName),
                DetailRow(
                  label: t.labEnteredAt,
                  value: formatDateTime(t, result.enteredAt),
                ),
                DetailRow(label: t.labVerifiedBy, value: result.verifiedByName),
              ],
            ),
        ],
      ),
    );
  }
}
