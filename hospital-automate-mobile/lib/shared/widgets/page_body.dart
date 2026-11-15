import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../features/navigation/nav_config.dart';

/// The scrolling main area of a page (`main` in layout.jsx): page padding,
/// the 1600 px cap and the breadcrumb trail for navigation pages.
class PageBody extends StatelessWidget {
  const PageBody({
    super.key,
    required this.location,
    required this.children,
    this.onHome,
  });

  final String location;
  final List<Widget> children;

  /// Opens Home from the breadcrumb.
  final VoidCallback? onHome;

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.sm;
    final match = location == '/' ? null : findNavMatch(location);
    return SingleChildScrollView(
      padding: wide ? AppSpacing.pageWide : AppSpacing.pagePhone,
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(
            maxWidth: AppDimensions.contentMaxWidth,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (match != null) ...[
                Breadcrumbs(
                  group: match.group,
                  item: match.item,
                  onHome: onHome,
                ),
                const SizedBox(height: AppSpacing.x4),
              ],
              ...children,
            ],
          ),
        ),
      ),
    );
  }
}

/// Breadcrumbs.jsx: Home › section › page. Only Home links; sections are not pages.
class Breadcrumbs extends StatelessWidget {
  const Breadcrumbs({
    super.key,
    required this.group,
    required this.item,
    this.onHome,
  });

  final NavGroup group;
  final NavItem item;
  final VoidCallback? onHome;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final muted = AppTypography.body(color: AppColors.ink500);
    const chevron = Icon(
      LucideIcons.chevronRight,
      size: 14,
      color: AppColors.ink400,
    );
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: AppSpacing.x1,
      runSpacing: AppSpacing.x1,
      children: [
        Semantics(
          link: true,
          // At least 48×36 so a short label (Hindi "होम") is still easy to tap.
          child: InkWell(
            onTap: onHome,
            borderRadius: AppRadii.button,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minWidth: 48, minHeight: 36),
              child: Align(
                widthFactor: 1,
                heightFactor: 1,
                alignment: Alignment.centerLeft,
                child: Text(l10n.navHome, style: muted),
              ),
            ),
          ),
        ),
        chevron,
        Text(group.label(l10n), style: muted),
        chevron,
        Text(
          item.label(l10n),
          style: AppTypography.body(
            weight: FontWeight.w500,
            color: AppColors.ink800,
          ),
        ),
      ],
    );
  }
}
