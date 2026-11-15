import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/app_scope.dart';
import '../../core/localization/l10n.dart';
import '../../core/localization/locale_controller.dart';
import '../../core/routing/app_routes.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/hms_card.dart';
import '../../shared/widgets/page_body.dart';
import '../../shared/widgets/page_header.dart';
import '../auth/ui/devices_card.dart';
import '../backend_status/backend_status_screen.dart';

/// Settings: interface language, signed-in devices (when signed in) and the
/// server connection check.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key, required this.location});

  final String location;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final services = AppScope.of(context);
    return PageBody(
      location: location,
      onHome: () => context.go(AppRoutes.home),
      children: [
        PageHeader(title: l10n.settings, description: l10n.appSettingsIntro),
        const SizedBox(height: AppSpacing.x6),
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: l10n.language,
                description: l10n.interfaceLanguage,
                icon: LucideIcons.languages,
              ),
              ListenableBuilder(
                listenable: services.locale,
                builder: (context, _) => HmsDividedColumn(
                  children: [
                    for (final language in AppLanguage.values)
                      _LanguageRow(
                        label: language == AppLanguage.en
                            ? l10n.languageEnglish
                            : l10n.languageHindi,
                        selected: services.locale.language == language,
                        onTap: () => services.locale.setLanguage(language),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
        if (services.session.state.isSignedIn) ...[
          const SizedBox(height: AppSpacing.x6),
          const DevicesCard(),
        ],
        const SizedBox(height: AppSpacing.x6),
        BackendStatusCard(
          origin: services.config.origin,
          checkHealth: services.checkHealth,
        ),
      ],
    );
  }
}

class _LanguageRow extends StatelessWidget {
  const _LanguageRow({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      inMutuallyExclusiveGroup: true,
      checked: selected,
      button: true,
      label: label,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: AppSpacing.cardRow.copyWith(top: 14, bottom: 14),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: AppTypography.body(weight: FontWeight.w500),
                ),
              ),
              if (selected)
                const Icon(
                  LucideIcons.check,
                  size: 18,
                  color: AppColors.onCard,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
