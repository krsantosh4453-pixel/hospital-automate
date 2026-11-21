import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/polling.dart';
import '../../../shared/widgets/tone.dart';
import '../data/record_models.dart';
import '../record_loader.dart';
import 'patient_ui.dart';

/// The backend has no push channel for queue changes (no WebSocket, no
/// FCM), so the page asks again on the web page's 30-second interval.
const queuePollInterval = Duration(seconds: 30);

/// `/patient/queue`: today's tokens with position and the server's wait
/// estimate. Polls only while the page is open and the app is in front.
class QueueScreen extends StatefulWidget {
  const QueueScreen({super.key, this.pollInterval = queuePollInterval});

  final Duration pollInterval;

  @override
  State<QueueScreen> createState() => _QueueScreenState();
}

class _QueueScreenState extends State<QueueScreen> {
  late final RecordLoader<List<QueueToken>> _loader = RecordLoader(
    AppScope.read(context).patient.queueTokens,
  );
  late final Poller _poller;
  DateTime? _checkedAt;

  @override
  void initState() {
    super.initState();
    _poller = Poller(
      interval: widget.pollInterval,
      onTick: _refresh,
      isBusy: () => _loader.loading,
    );
    _refresh();
  }

  Future<void> _refresh() async {
    await _loader.load();
    if (mounted && _loader.error == null) {
      setState(() => _checkedAt = DateTime.now());
    }
  }

  @override
  void dispose() {
    _poller.dispose();
    _loader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.patientNavQueue, description: t.queueIntro),
        if (_checkedAt != null) ...[
          const SizedBox(height: AppSpacing.x2),
          Text(
            t.lastChecked(formatClock(t, _checkedAt)),
            style: AppTypography.small(color: AppColors.ink500),
          ),
        ],
        const SizedBox(height: AppSpacing.x6),
        RecordSection<List<QueueToken>>(
          loader: _loader,
          skeletons: 1,
          builder: (context, tokens) {
            // A token from an earlier day is no longer a place in a queue.
            final today = DateUtils.dateOnly(DateTime.now());
            final open = [
              for (final token in tokens)
                if (token.isOpen &&
                    !(token.tokenDate?.isBefore(today) ?? false))
                  token,
            ];
            if (open.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.ticket,
                  title: t.noActiveToken,
                  description: t.noActiveTokenHint,
                ),
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < open.length; i++) ...[
                  if (i > 0) const SizedBox(height: AppSpacing.x4),
                  QueueTokenCard(token: open[i]),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

/// One token: number, status, position and the estimated wait.
class QueueTokenCard extends StatelessWidget {
  const QueueTokenCard({super.key, required this.token});

  final QueueToken token;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final minutes = token.estimatedWaitMinutes;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: Row(
              children: [
                Container(
                  width: 96,
                  height: 88,
                  decoration: const BoxDecoration(
                    color: AppColors.brand900,
                    borderRadius: BorderRadius.all(
                      Radius.circular(AppRadii.xxxl),
                    ),
                  ),
                  child: Semantics(
                    label: t.tokenNumber('${token.tokenNumber ?? '—'}'),
                    excludeSemantics: true,
                    // Scales down inside the fixed tile at very large text sizes.
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            t.tokenLabel,
                            style: AppTypography.caption(
                              color: AppColors.brand200,
                            ),
                          ),
                          Text(
                            '${token.tokenNumber ?? '—'}',
                            style: AppTypography.style(
                              32,
                              weight: FontWeight.w600,
                              color: AppColors.onCard,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.x4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      StatusBadge(status: token.status),
                      const SizedBox(height: AppSpacing.x1),
                      Text(
                        [
                          formatDay(t, token.tokenDate),
                          ?token.doctorName,
                        ].join(' · '),
                        style: AppTypography.small(),
                      ),
                      if (token.department != null)
                        Text(token.department!, style: AppTypography.caption()),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (token.isActive)
            HmsDividedColumn(
              children: [
                DetailRow(
                  label: t.queuePosition,
                  value: token.queuePosition == null
                      ? null
                      : '#${token.queuePosition}',
                ),
                DetailRow(
                  label: t.estimatedWait,
                  value: minutes == null ? null : t.minutesShort('$minutes'),
                ),
                DetailRow(
                  label: t.expectedAround,
                  value: token.estimatedStart == null
                      ? null
                      : formatClock(t, token.estimatedStart),
                ),
              ],
            ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: Semantics(
              liveRegion: true,
              child: switch (token.status) {
                'Called' => HmsAlert(
                  tone: AlertTone.info,
                  title: t.tokenCalled,
                  message: t.tokenCalledBody,
                ),
                'Ready' => HmsAlert(
                  tone: AlertTone.success,
                  title: t.tokenNext,
                ),
                'In Consultation' => HmsAlert(
                  tone: AlertTone.info,
                  title: t.tokenInConsultation,
                ),
                _ => Text(
                  t.estimatesAreApproximate,
                  style: AppTypography.small(),
                ),
              },
            ),
          ),
        ],
      ),
    );
  }
}
