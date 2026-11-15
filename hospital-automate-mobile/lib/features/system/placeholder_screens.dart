import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/app_scope.dart';
import '../../core/localization/l10n.dart';
import '../../core/routing/app_routes.dart';
import '../../core/theme/app_spacing.dart';
import '../../shared/widgets/hms_button.dart';
import '../../shared/widgets/hms_card.dart';
import '../../shared/widgets/page_body.dart';
import '../../shared/widgets/states.dart';
import '../navigation/nav_config.dart';

/// A sidebar page whose module is not built in the mobile app yet.
///
/// Visitors see what the web shows them: sign in first. Signed-in people are
/// told plainly that the module is not in this app version; nothing is faked.
class ModuleScreen extends StatelessWidget {
  const ModuleScreen({super.key, required this.item, required this.location});

  final NavItem item;
  final String location;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final session = AppScope.of(context).session.state;
    final module = item.label(l10n);
    final signedIn = session.isSignedIn;
    return PageBody(
      location: location,
      onHome: () => context.go(AppRoutes.home),
      children: [
        HmsCard(
          child: signedIn
              ? HmsEmptyState(
                  icon: item.icon,
                  title: l10n.moduleNotOnMobileTitle(module),
                  description: l10n.moduleNotOnMobileBody,
                  action: _homeButton(context),
                )
              : HmsEmptyState(
                  icon: LucideIcons.lock,
                  title: l10n.signInRequired,
                  description: l10n.signInToOpen(module),
                  action: HmsButton(
                    label: l10n.staffSignIn,
                    icon: LucideIcons.logIn,
                    surface: HmsSurface.card,
                    onPressed: () => context.go(AppRoutes.staffLogin),
                  ),
                ),
        ),
      ],
    );
  }
}

Widget _homeButton(BuildContext context) => HmsButton(
  label: context.l10n.backToHome,
  icon: LucideIcons.house,
  variant: HmsButtonVariant.secondary,
  surface: HmsSurface.card,
  onPressed: () => context.go(AppRoutes.home),
);

/// Gap between stacked page sections (`space-y-6`).
const sectionGap = SizedBox(height: AppSpacing.x6);
