import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/security/session_controller.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import 'brand_mark.dart';
import 'nav_config.dart';

/// Sidebar.jsx: brand row, grouped navigation and the sign-in footer, on
/// `brand-950`. Used as the phone drawer, the tablet rail and the wide sidebar.
class Sidebar extends StatelessWidget {
  const Sidebar({
    super.key,
    required this.groups,
    required this.location,
    required this.session,
    required this.onNavigate,
    required this.onSignIn,
    this.collapsed = false,
    this.onToggleCollapsed,
    this.onClose,
  });

  final List<NavGroup> groups;
  final String location;
  final SessionState session;
  final ValueChanged<NavItem> onNavigate;
  final VoidCallback onSignIn;
  final bool collapsed;

  /// Shown on the wide sidebar: collapse to the icon rail and back.
  final VoidCallback? onToggleCollapsed;

  /// Shown in the drawer: close it.
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Material(
      color: AppColors.sidebar,
      child: SafeArea(
        right: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _BrandRow(
              collapsed: collapsed,
              onToggleCollapsed: onToggleCollapsed,
              onClose: onClose,
            ),
            if (collapsed && onToggleCollapsed != null)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.x3),
                child: _SidebarIconButton(
                  icon: LucideIcons.panelLeftOpen,
                  tooltip: l10n.expandSidebar,
                  onTap: onToggleCollapsed!,
                ),
              ),
            Expanded(
              child: Semantics(
                label: l10n.navMain,
                container: true,
                child: ListView(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.x3,
                    vertical: AppSpacing.x3,
                  ),
                  children: [
                    for (var i = 0; i < groups.length; i++)
                      _NavGroupSection(
                        group: groups[i],
                        first: i == 0,
                        collapsed: collapsed,
                        location: location,
                        onNavigate: onNavigate,
                      ),
                  ],
                ),
              ),
            ),
            _SidebarFooter(
              session: session,
              collapsed: collapsed,
              onSignIn: onSignIn,
            ),
          ],
        ),
      ),
    );
  }
}

class _BrandRow extends StatelessWidget {
  const _BrandRow({
    required this.collapsed,
    this.onToggleCollapsed,
    this.onClose,
  });

  final bool collapsed;
  final VoidCallback? onToggleCollapsed;
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      height: AppDimensions.headerHeight,
      padding: EdgeInsets.symmetric(
        horizontal: collapsed ? AppSpacing.x2 : AppSpacing.x4,
      ),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.sidebarDivider)),
      ),
      child: Row(
        mainAxisAlignment: collapsed
            ? MainAxisAlignment.center
            : MainAxisAlignment.spaceBetween,
        children: [
          Flexible(child: BrandMark(compact: collapsed)),
          if (!collapsed && onClose != null)
            _SidebarIconButton(
              icon: LucideIcons.x,
              tooltip: l10n.closeNavigation,
              onTap: onClose!,
              size: 20,
            ),
          if (!collapsed && onClose == null && onToggleCollapsed != null)
            _SidebarIconButton(
              icon: LucideIcons.panelLeftClose,
              tooltip: l10n.collapseSidebar,
              onTap: onToggleCollapsed!,
            ),
        ],
      ),
    );
  }
}

class _NavGroupSection extends StatelessWidget {
  const _NavGroupSection({
    required this.group,
    required this.first,
    required this.collapsed,
    required this.location,
    required this.onNavigate,
  });

  final NavGroup group;
  final bool first;
  final bool collapsed;
  final String location;
  final ValueChanged<NavItem> onNavigate;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: EdgeInsets.only(top: first ? 0 : AppSpacing.x4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (collapsed && !first)
            const Padding(
              padding: EdgeInsets.fromLTRB(
                AppSpacing.x3,
                0,
                AppSpacing.x3,
                AppSpacing.x3,
              ),
              child: Divider(height: 1, color: AppColors.sidebarDivider),
            ),
          if (!collapsed && group.showsHeading)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.x3,
                0,
                AppSpacing.x3,
                AppSpacing.x1_5,
              ),
              child: Semantics(
                header: true,
                child: Text(
                  group.label(l10n).toUpperCase(),
                  style: AppTypography.navGroup(),
                ),
              ),
            ),
          for (final item in group.items)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.x0_5),
              child: _NavTile(
                item: item,
                active: item.matches(location),
                collapsed: collapsed,
                onTap: () => onNavigate(item),
              ),
            ),
        ],
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  const _NavTile({
    required this.item,
    required this.active,
    required this.collapsed,
    required this.onTap,
  });

  final NavItem item;
  final bool active;
  final bool collapsed;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final label = item.label(context.l10n);
    final tile = Material(
      color: active ? AppColors.sidebarActiveFill : Colors.transparent,
      borderRadius: AppRadii.button,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.button,
        hoverColor: const Color(0x0DFFFFFF),
        splashColor: const Color(0x14FFFFFF),
        child: ConstrainedBox(
          // Taller than the web's py-2 row so each entry is a comfortable touch target.
          constraints: const BoxConstraints(minHeight: 44),
          child: Stack(
            children: [
              if (active)
                const Positioned(
                  left: 0,
                  top: 6,
                  bottom: 6,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: AppColors.sidebarActiveBar,
                      borderRadius: BorderRadius.horizontal(
                        right: Radius.circular(999),
                      ),
                    ),
                    child: SizedBox(width: 3),
                  ),
                ),
              Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: collapsed ? 0 : AppSpacing.x3,
                  vertical: 12,
                ),
                child: Row(
                  mainAxisAlignment: collapsed
                      ? MainAxisAlignment.center
                      : MainAxisAlignment.start,
                  children: [
                    Icon(
                      item.icon,
                      size: 18,
                      color: active
                          ? AppColors.sidebarActiveIcon
                          : AppColors.sidebarIcon,
                    ),
                    if (!collapsed) ...[
                      const SizedBox(width: AppSpacing.x3),
                      Expanded(
                        child: Text(
                          label,
                          overflow: TextOverflow.ellipsis,
                          style: AppTypography.navItem(
                            color: active
                                ? AppColors.sidebarActiveText
                                : AppColors.sidebarText,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
    return Semantics(
      selected: active,
      button: true,
      label: label,
      excludeSemantics: true,
      child: collapsed ? Tooltip(message: label, child: tile) : tile,
    );
  }
}

class _SidebarFooter extends StatelessWidget {
  const _SidebarFooter({
    required this.session,
    required this.collapsed,
    required this.onSignIn,
  });

  final SessionState session;
  final bool collapsed;
  final VoidCallback onSignIn;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    // BUG-09: a signed-in patient was shown "Not signed in".
    final signedIn = session.isSignedIn;
    final text = signedIn
        ? l10n.signedInAs(session.activeRole ?? session.user!.displayName)
        : l10n.notSignedInSignIn;
    final row = Row(
      mainAxisAlignment: collapsed
          ? MainAxisAlignment.center
          : MainAxisAlignment.start,
      children: [
        if (signedIn)
          Container(
            width: 6,
            height: 6,
            decoration: const BoxDecoration(
              color: AppColors.green500,
              shape: BoxShape.circle,
            ),
          )
        else
          const Icon(
            LucideIcons.logIn,
            size: 15,
            color: AppColors.sidebarFooterText,
          ),
        if (!collapsed) ...[
          const SizedBox(width: AppSpacing.x2),
          Flexible(
            child: Text(
              text,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.caption(
                weight: FontWeight.w500,
                color: AppColors.sidebarFooterText,
              ),
            ),
          ),
        ],
      ],
    );
    return Container(
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AppColors.sidebarDivider)),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: collapsed ? AppSpacing.x2 : AppSpacing.x3,
        vertical: AppSpacing.x2,
      ),
      child: Semantics(
        button: !signedIn,
        label: text,
        excludeSemantics: true,
        child: InkWell(
          onTap: signedIn ? null : onSignIn,
          borderRadius: AppRadii.button,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 40),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.x2),
              child: row,
            ),
          ),
        ),
      ),
    );
  }
}

class _SidebarIconButton extends StatelessWidget {
  const _SidebarIconButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
    this.size = 18,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;
  final double size;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: onTap,
      tooltip: tooltip,
      icon: Icon(icon, size: size, color: AppColors.sidebarIcon),
      style: IconButton.styleFrom(
        hoverColor: const Color(0x1AFFFFFF),
        shape: const RoundedRectangleBorder(borderRadius: AppRadii.button),
      ),
    );
  }
}
