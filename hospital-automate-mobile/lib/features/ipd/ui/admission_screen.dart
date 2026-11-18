import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../operations/ops_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart'
    show DetailRow, RecordSection, formatDateTime, formatRupees;
import '../data/ipd_models.dart';
import '../data/ipd_repository.dart';
import 'bed_picker.dart';
import 'ipd_ui.dart';

/// `/ipd/:id`: one stay, its beds and how far its discharge has come. The
/// server decides every step; the page shows its answer and reloads.
class AdmissionScreen extends StatefulWidget {
  const AdmissionScreen({super.key, required this.admissionId});

  final int admissionId;

  @override
  State<AdmissionScreen> createState() => _AdmissionScreenState();
}

class _AdmissionScreenState extends State<AdmissionScreen>
    with PullToRefresh<AdmissionScreen> {
  late final IpdRepository _repository = AppScope.read(context).ipd;
  late final RecordLoader<IpdAdmission> _admission = RecordLoader(
    () => _repository.admission(widget.admissionId),
  );
  late final RecordLoader<DischargeReadiness> _readiness = RecordLoader(
    () => _repository.readiness(widget.admissionId),
  );
  late final RecordLoader<DischargeSummaryRecord?> _summary = RecordLoader(
    () => _repository.dischargeSummary(widget.admissionId),
  );
  bool _busy = false;
  String? _notice;
  String? _failure;

  @override
  void initState() {
    super.initState();
    reload();
  }

  @override
  void dispose() {
    _admission.dispose();
    _readiness.dispose();
    _summary.dispose();
    super.dispose();
  }

  @override
  Future<void> reload() =>
      Future.wait([_admission.load(), _readiness.load(), _summary.load()]);

  Future<void> _moveBed(IpdAdmission admission) async {
    final hospitalId = AppScope.read(context).session.activeHospitalId;
    if (_busy || hospitalId == null) return;
    final moved = await showBedPicker(
      context,
      repository: _repository,
      hospitalId: hospitalId,
      admission: admission,
    );
    if (!moved || !mounted) return;
    setState(() {
      _notice = context.l10n.ipdBedSaved;
      _failure = null;
    });
    await reload();
  }

  Future<void> _dischargeStep(
    IpdAdmission admission, {
    required bool complete,
  }) async {
    final t = context.l10n;
    if (_busy) return;
    final ok = await showHmsConfirm(
      context,
      title: complete ? t.ipdCompleteDischarge : t.ipdInitiateDischarge,
      message: complete ? t.ipdConfirmComplete : t.ipdConfirmInitiate,
      confirmLabel: complete ? t.ipdCompleteDischarge : t.ipdInitiateDischarge,
      destructive: complete,
    );
    if (!ok || !mounted) return;
    setState(() => _busy = true);
    try {
      final updated = complete
          ? await _repository.completeDischarge(admission.id)
          : await _repository.initiateDischarge(admission.id);
      if (!mounted) return;
      _admission.replace(updated);
      setState(() {
        _notice = complete ? t.ipdDischargeDone : t.opsSaved;
        _failure = null;
      });
    } catch (error) {
      if (mounted) setState(() => _failure = stepErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    await reload();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final canEdit = AppScope.of(context).session.state.can(ipdModule, 'Edit');
    return RecordSection<IpdAdmission>(
      loader: _admission,
      builder: (context, admission) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          PageHeader(
            title: admission.patientName ?? t.navIpd,
            description: admissionStatusLabel(t, admission.status),
            actions: [
              HmsButton(
                label: t.opsBackToList,
                icon: LucideIcons.arrowLeft,
                variant: HmsButtonVariant.secondary,
                onPressed: () => context.go(IpdRoutes.list),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.x4),
          OutcomeBanner(
            success: _failure == null ? _notice : null,
            error: _failure,
          ),
          if (!canEdit) ReadOnlyNotice(message: t.ipdReadOnly),
          _StayCard(admission: admission),
          const SizedBox(height: AppSpacing.x4),
          _BedCard(
            admission: admission,
            onMove: canEdit && !_busy ? () => _moveBed(admission) : null,
          ),
          const SizedBox(height: AppSpacing.x4),
          RecordSection<DischargeReadiness>(
            loader: _readiness,
            skeletons: 1,
            builder: (context, readiness) => _DischargeCard(
              admission: admission,
              readiness: readiness,
              onInitiate: canEdit && !_busy && admission.canInitiateDischarge
                  ? () => _dischargeStep(admission, complete: false)
                  : null,
              onComplete:
                  canEdit &&
                      !_busy &&
                      admission.isDischarging &&
                      readiness.ready
                  ? () => _dischargeStep(admission, complete: true)
                  : null,
            ),
          ),
          const SizedBox(height: AppSpacing.x4),
          _SummaryCard(loader: _summary),
        ],
      ),
    );
  }
}

class _StayCard extends StatelessWidget {
  const _StayCard({required this.admission});

  final IpdAdmission admission;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.ipdStay,
            icon: LucideIcons.bedDouble,
            trailing: AdmissionBadge(status: admission.status),
          ),
          DetailRow(
            label: t.ipdAdmittedOn,
            value: formatDateTime(t, admission.admissionDate),
          ),
          if (admission.dischargeDate != null)
            DetailRow(
              label: t.ipdDischargedOn,
              value: formatDateTime(t, admission.dischargeDate),
            ),
          DetailRow(
            label: t.ipdAdmittingDoctor,
            value: admission.admittingDoctorName,
          ),
          DetailRow(label: t.ipdReason, value: admission.reason),
        ],
      ),
    );
  }
}

class _BedCard extends StatelessWidget {
  const _BedCard({required this.admission, this.onMove});

  final IpdAdmission admission;
  final VoidCallback? onMove;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final current = admission.currentBed;
    final canMove = admission.canAllocateBed || admission.canTransferBed;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.ipdCurrentBed, icon: LucideIcons.bed),
          DetailRow(
            label: t.ipdCurrentBed,
            value: current == null ? t.ipdAwaitingBed : current.place.label,
          ),
          if (current != null)
            DetailRow(
              label: t.ipdSince,
              value: formatDateTime(t, current.allocatedAt),
            ),
          if (canMove && onMove != null)
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.x3),
              child: HmsButton(
                key: const Key('ipd-move-bed'),
                label: admission.canAllocateBed
                    ? t.ipdAllocateBed
                    : t.ipdTransferBed,
                icon: LucideIcons.arrowRightLeft,
                surface: HmsSurface.card,
                onPressed: onMove,
              ),
            ),
          const SizedBox(height: AppSpacing.x3),
          Text(
            t.ipdBedHistory,
            style: AppTypography.small(weight: FontWeight.w600),
          ),
          if (admission.bedHistory.isEmpty)
            Padding(
              padding: AppSpacing.cardRow,
              child: Text(t.ipdNoBedHistory, style: AppTypography.small()),
            ),
          for (final record in admission.bedHistory)
            DetailRow(
              label: record.place.label,
              value: [
                formatDateTime(t, record.allocatedAt),
                if (record.releasedAt != null)
                  formatDateTime(t, record.releasedAt),
              ].join(' → '),
            ),
        ],
      ),
    );
  }
}

class _DischargeCard extends StatelessWidget {
  const _DischargeCard({
    required this.admission,
    required this.readiness,
    this.onInitiate,
    this.onComplete,
  });

  final IpdAdmission admission;
  final DischargeReadiness readiness;
  final VoidCallback? onInitiate;
  final VoidCallback? onComplete;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final blockers = dischargeBlockers(t, admission, readiness);
    final bill = readiness.finalBill;
    final closed = admission.status == AdmissionStatus.discharged;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.ipdDischarge, icon: LucideIcons.logOut),
          if (!closed) ...[
            HmsAlert(
              tone: readiness.ready ? AlertTone.success : AlertTone.warning,
              title: readiness.ready ? t.ipdDischargeReady : t.ipdStillToDo,
              message: blockers.isEmpty ? null : blockers.join('\n'),
            ),
            const SizedBox(height: AppSpacing.x3),
          ],
          Text(
            t.ipdChecklist,
            style: AppTypography.small(weight: FontWeight.w600),
          ),
          for (final item in readiness.checklist)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.x1),
              child: Row(
                children: [
                  Icon(
                    item.done ? LucideIcons.circleCheck : LucideIcons.circle,
                    size: 16,
                  ),
                  const SizedBox(width: AppSpacing.x2),
                  Expanded(
                    child: Text(
                      checklistLabel(t, item),
                      style: AppTypography.body(),
                    ),
                  ),
                ],
              ),
            ),
          DetailRow(
            label: t.ipdSummary,
            value: readiness.summaryFinalized
                ? t.ipdSummaryFinalized
                : t.ipdSummaryNotFinalized,
          ),
          DetailRow(
            label: t.ipdFinalBill,
            value: bill == null
                ? t.ipdNoFinalBill
                : [?bill.number, ?bill.status].join(' · '),
          ),
          if (bill != null) ...[
            DetailRow(label: t.ipdBillTotal, value: formatRupees(bill.total)),
            DetailRow(
              label: t.ipdBalanceDue,
              value: formatRupees(bill.balanceDue),
            ),
          ],
          if (readiness.days != null)
            DetailRow(label: t.ipdDaysBilled, value: '${readiness.days}'),
          const SizedBox(height: AppSpacing.x3),
          Text(t.ipdDischargeStepsOnWeb, style: AppTypography.caption()),
          if (!closed) ...[
            const SizedBox(height: AppSpacing.x3),
            Wrap(
              spacing: AppSpacing.x2,
              runSpacing: AppSpacing.x2,
              children: [
                if (admission.canInitiateDischarge)
                  HmsButton(
                    key: const Key('ipd-initiate-discharge'),
                    label: t.ipdInitiateDischarge,
                    surface: HmsSurface.card,
                    onPressed: onInitiate,
                  ),
                if (admission.isDischarging)
                  HmsButton(
                    key: const Key('ipd-complete-discharge'),
                    label: t.ipdCompleteDischarge,
                    surface: HmsSurface.card,
                    variant: HmsButtonVariant.danger,
                    onPressed: onComplete,
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.loader});

  final RecordLoader<DischargeSummaryRecord?> loader;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return ListenableBuilder(
      listenable: loader,
      builder: (context, _) {
        final error = loader.error;
        final forbidden =
            error is ApiException && error.kind == ApiErrorKind.forbidden;
        final summary = loader.data;
        final Widget body;
        if (forbidden) {
          body = Text(t.ipdSummaryDoctorsOnly, style: AppTypography.small());
        } else if (error != null) {
          body = HmsErrorState(error: error, onRetry: loader.load);
        } else if (summary == null && loader.loading) {
          body = const HmsLoading();
        } else if (summary == null) {
          body = Text(t.ipdNoSummary, style: AppTypography.small());
        } else {
          body = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ToneBadge(
                label: summary.finalized
                    ? t.ipdSummaryFinalized
                    : t.ipdSummaryDraft,
                tone: summary.finalized ? AlertTone.success : AlertTone.warning,
              ),
              const SizedBox(height: AppSpacing.x2),
              Text(summary.summary, style: AppTypography.body()),
              if (summary.finalized)
                Text(
                  [
                    ?summary.doctorName,
                    formatDateTime(t, summary.finalizedAt),
                  ].join(' · '),
                  style: AppTypography.caption(),
                ),
            ],
          );
        }
        return HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(title: t.ipdSummary, icon: LucideIcons.fileText),
              Padding(padding: AppSpacing.cardRow, child: body),
            ],
          ),
        );
      },
    );
  }
}
