import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/page_header.dart';
import '../../operations/ops_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart'
    show DetailRow, RecordSection, formatDateTime;
import '../data/emergency_models.dart';
import '../data/emergency_repository.dart';
import '../../ipd/ui/ipd_ui.dart' show IpdRoutes;
import 'emergency_care_forms.dart';
import 'emergency_forms.dart';
import 'emergency_ui.dart';

/// `/emergency/:id`: one visit with its triage, care record and the next
/// moves its status allows. Every move is sent to the server, and the page
/// shows the visit as the server returns it afterwards.
class EmergencyVisitScreen extends StatefulWidget {
  const EmergencyVisitScreen({super.key, required this.visitId});

  final int visitId;

  @override
  State<EmergencyVisitScreen> createState() => _EmergencyVisitScreenState();
}

class _EmergencyVisitScreenState extends State<EmergencyVisitScreen>
    with PullToRefresh<EmergencyVisitScreen> {
  late final EmergencyRepository _repository = AppScope.read(context).emergency;
  late final RecordLoader<EmergencyVisit> _loader = RecordLoader(
    () => _repository.visit(widget.visitId),
  );
  bool _busy = false;
  String? _notice;
  String? _failure;

  /// The admission the server created from this visit, for the link to it.
  int? _admissionId;

  @override
  void initState() {
    super.initState();
    reload();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  @override
  Future<void> reload() => _loader.load();

  /// Runs a sheet that writes; on a confirmed write shows [success] and reloads.
  Future<void> _viaSheet(Future<bool> Function() open, String success) async {
    if (_busy) return;
    final done = await open();
    if (!done || !mounted) return;
    setState(() {
      _notice = success;
      _failure = null;
    });
    await reload();
  }

  Future<void> _startTriage(EmergencyVisit visit) async {
    final t = context.l10n;
    if (_busy) return;
    final ok = await showHmsConfirm(
      context,
      title: t.erStartTriage,
      message: t.erStartTriageConfirm,
      confirmLabel: t.erStartTriage,
    );
    if (!ok || !mounted) return;
    setState(() => _busy = true);
    try {
      final updated = await _repository.startTriage(visit.id);
      if (!mounted) return;
      _loader.replace(updated);
      setState(() {
        _notice = t.opsSaved;
        _failure = null;
      });
    } catch (error) {
      if (mounted) setState(() => _failure = stepErrorMessage(t, error));
      await reload();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _admit(EmergencyVisit visit) async {
    if (_busy) return;
    final services = AppScope.read(context);
    final admission = await showAdmitSheet(
      context,
      _repository,
      services.ipd,
      visit,
    );
    if (admission == null || !mounted) return;
    setState(() {
      _notice = context.l10n.erAdmitted;
      _failure = null;
      _admissionId = admission.admissionId;
    });
    await reload();
  }

  void _run(ErAction action, EmergencyVisit visit) {
    final t = context.l10n;
    switch (action) {
      case ErAction.startTriage:
        _startTriage(visit);
      case ErAction.completeTriage:
        _viaSheet(
          () => showTriageSheet(context, _repository, visit),
          t.opsSaved,
        );
      case ErAction.startConsultation:
        _viaSheet(
          () => showConsultationSheet(context, _repository, visit),
          t.opsSaved,
        );
      case ErAction.discharge:
        _viaSheet(
          () => showDispositionSheet(context, _repository, visit, refer: false),
          t.erDischarged,
        );
      case ErAction.refer:
        _viaSheet(
          () => showDispositionSheet(context, _repository, visit, refer: true),
          t.erReferred,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final canEdit = AppScope.of(context).session.state
        .can(emergencyModule, 'Edit');
    return RecordSection<EmergencyVisit>(
      loader: _loader,
      builder: (context, visit) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          PageHeader(
            title: visit.patientName ?? t.navEmergency,
            description: visit.visitNumber,
            actions: [
              HmsButton(
                label: t.opsBackToList,
                icon: LucideIcons.arrowLeft,
                variant: HmsButtonVariant.secondary,
                onPressed: () => context.go(EmergencyRoutes.list),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.x3),
          Wrap(
            spacing: AppSpacing.x2,
            children: [
              TriageBadge(level: visit.triageLevel),
              ErStatusBadge(status: visit.status),
            ],
          ),
          const SizedBox(height: AppSpacing.x4),
          OutcomeBanner(
            success: _failure == null ? _notice : null,
            error: _failure,
          ),
          if (_admissionId != null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.x4),
              child: HmsButton(
                key: const Key('er-open-admission'),
                label: t.erOpenAdmission,
                icon: LucideIcons.bedDouble,
                variant: HmsButtonVariant.secondary,
                onPressed: () => context.go(IpdRoutes.admission(_admissionId!)),
              ),
            ),
          if (canEdit)
            _ActionsCard(
              visit: visit,
              busy: _busy,
              onAction: (action) => _run(action, visit),
              onNote: () => _viaSheet(
                () => showErNoteSheet(context, _repository, visit),
                t.erNoteSaved,
              ),
              onVitals: visit.isClosed
                  ? null
                  : () => _viaSheet(
                      () => showErVitalsSheet(context, _repository, visit),
                      t.vitalsSaved,
                    ),
              onAdmit: admittableStatuses.contains(visit.status)
                  ? () => _admit(visit)
                  : null,
            )
          else
            ReadOnlyNotice(message: t.erReadOnly),
          _DetailsCard(visit: visit),
          const SizedBox(height: AppSpacing.x4),
          _TriageCard(triage: visit.triage),
          const SizedBox(height: AppSpacing.x4),
          _CareCard(visit: visit),
          const SizedBox(height: AppSpacing.x4),
          _NotesCard(notes: visit.notes),
        ],
      ),
    );
  }
}

class _ActionsCard extends StatelessWidget {
  const _ActionsCard({
    required this.visit,
    required this.busy,
    required this.onAction,
    required this.onNote,
    this.onVitals,
    this.onAdmit,
  });

  final EmergencyVisit visit;
  final bool busy;
  final ValueChanged<ErAction> onAction;
  final VoidCallback onNote;

  /// Null while the visit's status does not allow the step.
  final VoidCallback? onVitals;
  final VoidCallback? onAdmit;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final actions = erActionsFor(visit.status);
    String label(ErAction action) => switch (action) {
      ErAction.startTriage => t.erStartTriage,
      ErAction.completeTriage => t.erCompleteTriage,
      ErAction.startConsultation => t.erStartConsultation,
      ErAction.discharge => t.erDischarge,
      ErAction.refer => t.erRefer,
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.x4),
      child: HmsCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            HmsCardHeader(title: t.erNextSteps, icon: LucideIcons.listChecks),
            const SizedBox(height: AppSpacing.x3),
            if (actions.isEmpty)
              Text(t.erVisitClosed, style: AppTypography.small()),
            Wrap(
              spacing: AppSpacing.x2,
              runSpacing: AppSpacing.x2,
              children: [
                for (final action in actions)
                  HmsButton(
                    key: ValueKey('er-action-${action.name}'),
                    label: label(action),
                    surface: HmsSurface.card,
                    variant:
                        action == ErAction.discharge || action == ErAction.refer
                        ? HmsButtonVariant.secondary
                        : HmsButtonVariant.primary,
                    onPressed: busy ? null : () => onAction(action),
                  ),
                if (onAdmit != null)
                  HmsButton(
                    key: const Key('er-admit'),
                    label: t.erAdmitToIpd,
                    icon: LucideIcons.bedDouble,
                    surface: HmsSurface.card,
                    onPressed: busy ? null : onAdmit,
                  ),
                if (onVitals != null)
                  HmsButton(
                    key: const Key('er-record-vitals'),
                    label: t.erRecordVitals,
                    icon: LucideIcons.heartPulse,
                    surface: HmsSurface.card,
                    variant: HmsButtonVariant.secondary,
                    onPressed: busy ? null : onVitals,
                  ),
                HmsButton(
                  key: const Key('er-add-note'),
                  label: t.erAddNote,
                  icon: LucideIcons.notebookPen,
                  surface: HmsSurface.card,
                  variant: HmsButtonVariant.ghost,
                  onPressed: busy ? null : onNote,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailsCard extends StatelessWidget {
  const _DetailsCard({required this.visit});

  final EmergencyVisit visit;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.erDetails, icon: LucideIcons.siren),
          DetailRow(
            label: t.erArrival,
            value: formatDateTime(t, visit.arrivalTime),
          ),
          DetailRow(
            label: t.erTriageStarted,
            value: formatDateTime(t, visit.triageTime),
          ),
          DetailRow(
            label: t.erConsultationStarted,
            value: formatDateTime(t, visit.consultationStartTime),
          ),
          DetailRow(
            label: t.erAttendingDoctor,
            value: visit.attendingDoctorName ?? t.erNoDoctorYet,
          ),
          DetailRow(label: t.erRemarks, value: visit.remarks),
          if (visit.isClosed) ...[
            DetailRow(
              label: t.erLeftEr,
              value: formatDateTime(t, visit.dischargeTime),
            ),
            DetailRow(
              label: t.erDischargeDiagnosis,
              value: visit.dischargeDiagnosis,
            ),
            DetailRow(label: t.erFollowUp, value: visit.followUpInstructions),
          ],
        ],
      ),
    );
  }
}

class _TriageCard extends StatelessWidget {
  const _TriageCard({required this.triage});

  final ErTriage? triage;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final record = triage;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.erTriageSection, icon: LucideIcons.activity),
          if (record == null)
            Padding(
              padding: AppSpacing.cardRow,
              child: Text(t.erNotTriaged, style: AppTypography.small()),
            )
          else ...[
            DetailRow(label: t.erChiefComplaint, value: record.chiefComplaint),
            DetailRow(
              label: t.erPainScore,
              value: record.painScore?.toString(),
            ),
            DetailRow(
              label: t.erGcs,
              value: record.glasgowComaScale?.toString(),
            ),
            DetailRow(label: t.erTriageNotes, value: record.notes),
            DetailRow(
              label: t.erTriagedBy,
              value: [
                ?record.triagedByName,
                formatDateTime(t, record.triagedAt),
              ].join(' · '),
            ),
          ],
        ],
      ),
    );
  }
}

/// Vitals, orders and medicines recorded in the visit (read here; they are
/// written on the web ER page).
class _CareCard extends StatelessWidget {
  const _CareCard({required this.visit});

  final EmergencyVisit visit;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    Widget empty(String text) => Padding(
      padding: AppSpacing.cardRow,
      child: Text(text, style: AppTypography.small()),
    );
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.erVitalsSection, icon: LucideIcons.heartPulse),
          if (visit.vitals.isEmpty) empty(t.erNoVitals),
          for (final reading in visit.vitals)
            DetailRow(
              label: formatDateTime(t, reading.recordedAt),
              value: _vitalsLine(t, reading),
            ),
          const SizedBox(height: AppSpacing.x3),
          HmsCardHeader(
            title: t.erOrdersSection,
            icon: LucideIcons.clipboardList,
          ),
          if (visit.orders.isEmpty) empty(t.erNoOrders),
          for (final order in visit.orders)
            DetailRow(
              label: order.orderType,
              value: [
                ?order.description,
                order.status,
                ?order.result,
              ].join(' · '),
            ),
          const SizedBox(height: AppSpacing.x3),
          HmsCardHeader(title: t.erMedicationsSection, icon: LucideIcons.pill),
          if (visit.medications.isEmpty) empty(t.erNoMedications),
          for (final med in visit.medications)
            DetailRow(
              label: med.name,
              value: [
                ?med.dose,
                ?med.route,
                ?med.frequency,
                med.administered ? t.erGiven : t.erNotGiven,
              ].join(' · '),
            ),
        ],
      ),
    );
  }

  static String _vitalsLine(AppLocalizations t, ErVitals v) => [
    if (v.systolic != null || v.diastolic != null)
      '${t.erBp} ${v.systolic ?? '—'}/${v.diastolic ?? '—'}',
    if (v.heartRate != null) '${t.vitalPulse} ${v.heartRate}',
    if (v.respiratoryRate != null) '${t.erRr} ${v.respiratoryRate}',
    if (v.spo2 != null) '${t.vitalSpo2} ${v.spo2}',
    if (v.temperature != null) '${t.vitalTemperature} ${v.temperature}',
    if (v.bloodSugar != null) '${t.erSugar} ${v.bloodSugar}',
  ].join(' · ');
}

class _NotesCard extends StatelessWidget {
  const _NotesCard({required this.notes});

  final List<ErNote> notes;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.erNotes, icon: LucideIcons.notebookPen),
          if (notes.isEmpty)
            Padding(
              padding: AppSpacing.cardRow,
              child: Text(t.erNoNotes, style: AppTypography.small()),
            ),
          for (final note in notes)
            Padding(
              padding: AppSpacing.cardRow,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(note.note, style: AppTypography.body()),
                  const SizedBox(height: 2),
                  Text(
                    [
                      ?note.writtenByName,
                      formatDateTime(t, note.writtenAt),
                    ].join(' · '),
                    style: AppTypography.caption(),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
