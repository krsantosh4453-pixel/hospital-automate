import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/security/session_controller.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/app_backdrop.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/states.dart';

/// Covers the app while a stored session is being resumed, and when the
/// server could not be reached to check it (retry or sign out). Otherwise
/// shows [child] (the routed app).
class SessionGate extends StatelessWidget {
  const SessionGate({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final services = AppScope.of(context);
    return ListenableBuilder(
      listenable: services.session,
      builder: (context, _) {
        final t = context.l10n;
        return switch (services.session.status) {
          SessionStatus.restoring => Scaffold(
            body: AppBackdrop(child: HmsLoading(label: t.restoringSession)),
          ),
          SessionStatus.restoreFailed => Scaffold(
            body: AppBackdrop(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.x6),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 448),
                    child: HmsCard(
                      child: HmsEmptyState(
                        icon: LucideIcons.wifiOff,
                        title: t.restoreFailedTitle,
                        description: t.restoreFailedBody,
                        action: Wrap(
                          spacing: AppSpacing.x2,
                          runSpacing: AppSpacing.x2,
                          children: [
                            HmsButton(
                              label: t.tryAgain,
                              surface: HmsSurface.card,
                              onPressed: services.auth.restore,
                            ),
                            HmsButton(
                              label: t.signOut,
                              variant: HmsButtonVariant.secondary,
                              surface: HmsSurface.card,
                              onPressed: services.auth.signOut,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          _ => child,
        };
      },
    );
  }
}
