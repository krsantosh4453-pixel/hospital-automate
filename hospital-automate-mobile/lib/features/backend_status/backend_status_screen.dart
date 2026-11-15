import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/network/backend_health.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/hms_button.dart';
import '../../shared/widgets/hms_card.dart';

/// Proves the app reaches the backend: calls the public `/health/` endpoint.
class BackendStatusCard extends StatefulWidget {
  const BackendStatusCard({
    super.key,
    required this.origin,
    required this.checkHealth,
  });

  final String origin;
  final HealthCheck checkHealth;

  @override
  State<BackendStatusCard> createState() => _BackendStatusCardState();
}

class _BackendStatusCardState extends State<BackendStatusCard> {
  late Future<HealthResult> _result = widget.checkHealth();

  void _retry() {
    final next = widget.checkHealth();
    setState(() {
      _result = next;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: l10n.serverConnection,
            description: l10n.serverConnectionText,
            icon: LucideIcons.server,
          ),
          Padding(
            padding: AppSpacing.cardHeader,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.backend,
                  style: AppTypography.small(weight: FontWeight.w500),
                ),
                SelectableText(
                  widget.origin,
                  style: AppTypography.body(weight: FontWeight.w600),
                ),
                const SizedBox(height: AppSpacing.x4),
                FutureBuilder<HealthResult>(
                  future: _result,
                  builder: (context, snapshot) {
                    final result = snapshot.data;
                    if (snapshot.connectionState != ConnectionState.done ||
                        result == null) {
                      return Row(
                        children: [
                          const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: AppColors.onCard,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.x3),
                          Flexible(
                            child: Text(
                              l10n.checkingConnection,
                              style: AppTypography.body(),
                            ),
                          ),
                        ],
                      );
                    }
                    return Semantics(
                      liveRegion: true,
                      child: Row(
                        children: [
                          Icon(
                            result.reachable
                                ? LucideIcons.circleCheck
                                : LucideIcons.circleAlert,
                            size: 20,
                            color: result.reachable
                                ? AppColors.brand200
                                : const Color(0xFFF5BCB6),
                          ),
                          const SizedBox(width: AppSpacing.x3),
                          Expanded(
                            child: Text(
                              result.message,
                              style: AppTypography.body(),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
                const SizedBox(height: AppSpacing.x4),
                HmsButton(
                  label: l10n.checkAgain,
                  onPressed: _retry,
                  variant: HmsButtonVariant.secondary,
                  surface: HmsSurface.card,
                  icon: LucideIcons.refreshCw,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
