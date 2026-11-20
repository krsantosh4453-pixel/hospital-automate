import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/polling.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../../patient/ui/queue_screen.dart' show queuePollInterval;
import '../data/doctor_repository.dart';
import 'doctor_ui.dart';

/// Moves the server allows from each status (encounters/views.py
/// `allowed_from`). "Call next" is not offered here; the doctor calls a
/// chosen token. The server refuses to start a second consultation while one
/// is open (409), and never closes one on its own.
List<QueueAction> actionsFor(String status) => switch (status) {
  'Waiting' => const [QueueAction.call, QueueAction.skip, QueueAction.noShow],
  'Called' || 'Acknowledged' || 'Ready' => const [
    QueueAction.startConsultation,
    QueueAction.skip,
    QueueAction.noShow,
  ],
  'In Consultation' => const [QueueAction.complete, QueueAction.skip],
  _ => const [],
};

/// `/queue` for a doctor: today's tokens, grouped by where they are.
class QueueBoardScreen extends StatefulWidget {
  const QueueBoardScreen({
    super.key,
    this.pollInterval = queuePollInterval,
    this.now,
    this.readOnly = false,
  });

  final Duration pollInterval;
  final DateTime Function()? now;

  /// The front desk's view: the same board, without queue moves or links
  /// into consultations (those are the doctor's).
  final bool readOnly;

  @override
  State<QueueBoardScreen> createState() => _QueueBoardScreenState();
}

class _QueueBoardScreenState extends State<QueueBoardScreen> {
  late final DoctorRepository _repository = AppScope.read(context).doctor;
  late final RecordLoader<List<QueueToken>> _loader = RecordLoader(
    () => _repository.queue(date: today(widget.now)),
  );
  late final Poller _poller;
  final Set<int> _busy = {};
  String? _actionError;
  DateTime? _checkedAt;

  @override
  void initState() {
    super.initState();
    _poller = Poller(
      interval: widget.pollInterval,
      onTick: _refresh,
      // No poll while a load or a queue move is running.
      isBusy: () => _loader.loading || _busy.isNotEmpty,
    );
    _refresh();
  }

  @override
  void dispose() {
    _poller.dispose();
    _loader.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    await _loader.load();
    if (mounted && _loader.error == null) {
      setState(() => _checkedAt = DateTime.now());
    }
  }

  Future<void> _move(QueueToken token, QueueAction action) async {
    if (_busy.contains(token.id)) return;
    final t = context.l10n;
    if (action == QueueAction.skip || action == QueueAction.noShow) {
      final confirmed = await showHmsConfirm(
        context,
        title: action == QueueAction.skip ? t.skipTokenTitle : t.noShowTitle,
        message: t.queueMoveConfirm('${token.tokenNumber ?? '—'}'),
        confirmLabel: queueActionLabel(t, action),
        destructive: true,
      );
      if (!confirmed || !mounted) return;
    }
    setState(() {
      _busy.add(token.id);
      _actionError = null;
    });
    try {
      final moved = await _repository.moveToken(token.id, action);
      final rows = _loader.data ?? const <QueueToken>[];
      _loader.replace([
        for (final row in rows) row.id == moved.id ? moved : row,
      ]);
    } catch (error) {
      if (mounted) {
        final t = context.l10n;
        // A queue move is only refused as a conflict when this doctor already
        // has a patient in consultation; it is not a signed record.
        final doctorBusy =
            error is ApiException && error.kind == ApiErrorKind.conflict;
        setState(
          () => _actionError = doctorBusy
              ? t.queueDoctorBusy
              : clinicalErrorMessage(t, error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy.remove(token.id));
    }
    // The server recalculates positions and estimates for everyone.
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.navQueue,
          description: widget.readOnly
              ? t.receptionQueueIntro
              : t.doctorQueueIntro,
          actions: [
            HmsButton(
              label: t.refresh,
              icon: LucideIcons.refreshCw,
              variant: HmsButtonVariant.secondary,
              onPressed: _loader.loading ? null : _refresh,
            ),
          ],
        ),
        if (_checkedAt != null) ...[
          const SizedBox(height: AppSpacing.x2),
          Text(
            t.lastChecked(formatClock(t, _checkedAt)),
            style: AppTypography.small(color: AppColors.ink500),
          ),
        ],
        const SizedBox(height: AppSpacing.x4),
        if (_actionError != null) ...[
          HmsAlert(
            tone: AlertTone.danger,
            title: t.queueMoveFailed,
            message: _actionError,
          ),
          const SizedBox(height: AppSpacing.x4),
        ],
        RecordSection<List<QueueToken>>(
          loader: _loader,
          builder: (context, tokens) => _Board(
            tokens: tokens,
            busy: _busy,
            onMove: _move,
            readOnly: widget.readOnly,
          ),
        ),
      ],
    );
  }
}

class _Board extends StatelessWidget {
  const _Board({
    required this.tokens,
    required this.busy,
    required this.onMove,
    required this.readOnly,
  });

  final bool readOnly;
  final List<QueueToken> tokens;
  final Set<int> busy;
  final Future<void> Function(QueueToken, QueueAction) onMove;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    List<QueueToken> where(Set<String> statuses) => [
      for (final token in tokens)
        if (statuses.contains(token.status)) token,
    ]..sort((a, b) => (a.tokenNumber ?? 0).compareTo(b.tokenNumber ?? 0));
    final serving = where({'In Consultation'});
    final called = where({'Called', 'Acknowledged', 'Ready'});
    final waiting = where({'Waiting'});
    final done =
        tokens.length - serving.length - called.length - waiting.length;
    Widget group(String title, List<QueueToken> rows, String empty) => HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: '$title (${rows.length})'),
          if (rows.isEmpty)
            HmsEmptyState(compact: true, title: empty)
          else
            HmsDividedColumn(
              children: [
                for (final token in rows)
                  _TokenRow(
                    token: token,
                    busy: busy.contains(token.id),
                    onMove: onMove,
                    readOnly: readOnly,
                  ),
              ],
            ),
        ],
      ),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        group(t.nowServing, serving, t.nobodyInConsultation),
        const SizedBox(height: AppSpacing.x4),
        group(t.calledPatients, called, t.nobodyCalled),
        const SizedBox(height: AppSpacing.x4),
        group(t.waitingPatients, waiting, t.nobodyWaiting),
        const SizedBox(height: AppSpacing.x4),
        Text(t.queueFinishedToday(done), style: AppTypography.small()),
      ],
    );
  }
}

class _TokenRow extends StatelessWidget {
  const _TokenRow({
    required this.token,
    required this.busy,
    required this.onMove,
    required this.readOnly,
  });

  final bool readOnly;
  final QueueToken token;
  final bool busy;
  final Future<void> Function(QueueToken, QueueAction) onMove;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final minutes = token.estimatedWaitMinutes;
    return Padding(
      padding: AppSpacing.cardRow,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '#${token.tokenNumber ?? '—'}',
                style: AppTypography.style(
                  20,
                  weight: FontWeight.w700,
                  color: AppColors.onCard,
                ),
              ),
              const SizedBox(width: AppSpacing.x3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      token.patientName ?? t.patientLabel,
                      style: AppTypography.body(weight: FontWeight.w600),
                    ),
                    Text(
                      [
                        ?token.department,
                        if (token.queuePosition != null)
                          t.positionShort('${token.queuePosition}'),
                        if (minutes != null) t.estimatedWaitShort('$minutes'),
                      ].join(' · '),
                      style: AppTypography.small(),
                    ),
                  ],
                ),
              ),
              StatusBadge(status: token.status),
            ],
          ),
          if (!readOnly) ...[
            const SizedBox(height: AppSpacing.x2),
            Wrap(
              spacing: AppSpacing.x2,
              runSpacing: AppSpacing.x2,
              children: [
                for (final action in actionsFor(token.status))
                  HmsButton(
                    key: ValueKey('queue-${token.id}-${action.path}'),
                    label: queueActionLabel(t, action),
                    size: HmsButtonSize.small,
                    surface: HmsSurface.card,
                    variant:
                        action == QueueAction.skip ||
                            action == QueueAction.noShow
                        ? HmsButtonVariant.secondary
                        : HmsButtonVariant.primary,
                    loading: busy,
                    onPressed: busy ? null : () => onMove(token, action),
                  ),
                if (token.visitId != null)
                  HmsButton(
                    label: t.openConsultation,
                    size: HmsButtonSize.small,
                    surface: HmsSurface.card,
                    variant: HmsButtonVariant.ghost,
                    onPressed: () =>
                        context.go(DoctorRoutes.visit(token.visitId!)),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

String queueActionLabel(AppLocalizations t, QueueAction action) =>
    switch (action) {
      QueueAction.call => t.queueCall,
      QueueAction.startConsultation => t.queueStartConsultation,
      QueueAction.complete => t.queueComplete,
      QueueAction.skip => t.queueSkip,
      QueueAction.noShow => t.queueNoShow,
    };
