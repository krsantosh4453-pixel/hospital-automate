import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/localization/locale_controller.dart';
import '../../core/security/session_controller.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/avatar.dart';
import '../../shared/widgets/hms_button.dart';
import '../dashboard/role_homes.dart';
import 'header_dialogs.dart';
import 'nav_config.dart';

/// Navbar.jsx: the teal top bar. Menu button (narrow screens), page search,
/// hospital switcher, language switch, then sign-in or the profile menu.
class AppHeader extends StatelessWidget {
  const AppHeader({
    super.key,
    required this.session,
    required this.locale,
    required this.groups,
    required this.onOpenNavigation,
    required this.onNavigate,
    required this.onSignIn,
    required this.onSignOut,
    required this.onOpenSettings,
    required this.onSelectHospital,
  });

  final SessionState session;
  final LocaleController locale;
  final List<NavGroup> groups;

  /// Null when the sidebar is already on screen.
  final VoidCallback? onOpenNavigation;
  final ValueChanged<NavItem> onNavigate;

  /// `true` for staff sign-in, `false` for patient sign-in.
  final ValueChanged<bool> onSignIn;
  final VoidCallback onSignOut;
  final VoidCallback onOpenSettings;
  final ValueChanged<int> onSelectHospital;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final width = MediaQuery.sizeOf(context).width;
    final wide = width >= AppBreakpoints.md;
    return Material(
      color: AppColors.card,
      child: SafeArea(
        bottom: false,
        child: Container(
          height: AppDimensions.headerHeight,
          padding: EdgeInsets.symmetric(
            horizontal: width >= AppBreakpoints.sm
                ? AppSpacing.x6
                : AppSpacing.x2,
          ),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: AppColors.onCardLine)),
          ),
          // Left group (menu, search) and right group (hospital, language,
          // account) are pushed apart; both shrink their labels before
          // anything can overflow on a narrow phone or with large text.
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _flexibleWhen(
                wide,
                flex: 2,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (onOpenNavigation != null)
                      _HeaderIconButton(
                        icon: LucideIcons.menu,
                        tooltip: l10n.openNavigation,
                        onTap: onOpenNavigation!,
                      ),
                    if (wide)
                      Flexible(
                        child: _JumpField(onTap: () => _openJump(context)),
                      )
                    else
                      _HeaderIconButton(
                        icon: LucideIcons.search,
                        tooltip: l10n.jumpToPage,
                        onTap: () => _openJump(context),
                      ),
                  ],
                ),
              ),
              Flexible(
                flex: 5,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    // Icon-only on phones (fixed size); with its label it may shorten.
                    _flexibleWhen(
                      width >= AppBreakpoints.sm,
                      flex: 1,
                      child: _HospitalButton(
                        session: session,
                        showLabel: width >= AppBreakpoints.sm,
                        onSelect: onSelectHospital,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.x1_5),
                    _LanguageToggle(locale: locale),
                    const SizedBox(width: AppSpacing.x1_5),
                    if (session.isSignedIn)
                      Flexible(
                        child: _ProfileButton(
                          session: session,
                          showName: wide,
                          onSignOut: onSignOut,
                          onOpenSettings: onOpenSettings,
                        ),
                      )
                    else
                      ..._signInButtons(l10n, width),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// "Patient sign in" from `sm` up, then "Staff sign in". Below 360 px the
  /// staff button keeps only its icon (with a tooltip) so the bar fits.
  List<Widget> _signInButtons(AppLocalizations l10n, double width) {
    if (width < _compactHeaderWidth) {
      return [
        _HeaderIconButton(
          icon: LucideIcons.logIn,
          tooltip: l10n.staffSignIn,
          onTap: () => onSignIn(true),
        ),
      ];
    }
    return [
      if (width >= AppBreakpoints.sm) ...[
        Flexible(
          child: HmsButton(
            label: l10n.patientSignIn,
            onPressed: () => onSignIn(false),
            variant: HmsButtonVariant.secondary,
            surface: HmsSurface.card,
            size: HmsButtonSize.small,
          ),
        ),
        const SizedBox(width: AppSpacing.x1_5),
      ],
      Flexible(
        child: HmsButton(
          label: l10n.staffSignIn,
          icon: LucideIcons.logIn,
          onPressed: () => onSignIn(true),
          surface: HmsSurface.card,
          size: HmsButtonSize.small,
        ),
      ),
    ];
  }

  Future<void> _openJump(BuildContext context) async {
    final item = await showQuickJump(context, groups);
    if (item != null) onNavigate(item);
  }
}

const _compactHeaderWidth = 360.0;

/// Wraps [child] in a [Flexible] only when [flexible]; the phone's two icon
/// buttons keep their natural width so the right-hand group gives way instead.
Widget _flexibleWhen(
  bool flexible, {
  required int flex,
  required Widget child,
}) => flexible ? Flexible(flex: flex, child: child) : child;

class _JumpField extends StatelessWidget {
  const _JumpField({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Semantics(
      button: true,
      label: l10n.jumpToPage,
      excludeSemantics: true,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 320),
        child: Material(
          color: AppColors.onCardHover,
          shape: const RoundedRectangleBorder(
            borderRadius: AppRadii.button,
            side: BorderSide(color: AppColors.onCardLine),
          ),
          child: InkWell(
            onTap: onTap,
            borderRadius: AppRadii.button,
            child: SizedBox(
              height: AppDimensions.control,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.x3),
                child: Row(
                  children: [
                    const Icon(
                      LucideIcons.search,
                      size: 16,
                      color: AppColors.onCard,
                    ),
                    const SizedBox(width: AppSpacing.x2),
                    Expanded(
                      child: Text(l10n.jumpTo, style: AppTypography.small()),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _HospitalButton extends StatelessWidget {
  const _HospitalButton({
    required this.session,
    required this.showLabel,
    required this.onSelect,
  });

  final SessionState session;
  final bool showLabel;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final name = session.activeHospital?.name ?? l10n.selectHospitalTitle;
    return Semantics(
      button: true,
      label: '${l10n.hospital}: $name',
      excludeSemantics: true,
      child: Material(
        color: AppColors.cardRaised,
        shape: const RoundedRectangleBorder(
          borderRadius: AppRadii.button,
          side: BorderSide(color: AppColors.onCardLine),
        ),
        child: InkWell(
          borderRadius: AppRadii.button,
          onTap: () async {
            final id = await showHospitalPicker(context, session);
            if (id != null) onSelect(id);
          },
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: AppDimensions.control),
            child: Padding(
              padding: const EdgeInsets.only(
                left: AppSpacing.x2_5,
                right: AppSpacing.x2,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    LucideIcons.hospital,
                    size: 18,
                    color: AppColors.onCard,
                  ),
                  if (showLabel) ...[
                    const SizedBox(width: AppSpacing.x2_5),
                    Flexible(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 150),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              l10n.hospital.toUpperCase(),
                              style: AppTypography.style(
                                10.5,
                                weight: FontWeight.w500,
                                height: 14,
                                color: AppColors.onCard,
                                letterSpacing: 0.26,
                              ),
                            ),
                            Text(
                              name,
                              overflow: TextOverflow.ellipsis,
                              style: AppTypography.style(
                                13,
                                weight: FontWeight.w600,
                                height: 16,
                                color: AppColors.onCard,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(width: AppSpacing.x1),
                  const Icon(
                    LucideIcons.chevronDown,
                    size: 16,
                    color: AppColors.onCardMuted,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LanguageToggle extends StatelessWidget {
  const _LanguageToggle({required this.locale});

  final LocaleController locale;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: context.l10n.interfaceLanguage,
      container: true,
      child: Container(
        padding: const EdgeInsets.all(2),
        decoration: const BoxDecoration(
          color: AppColors.onCardFill,
          borderRadius: AppRadii.button,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final language in AppLanguage.values)
              _LanguageOption(
                language: language,
                selected: locale.language == language,
                onTap: () => locale.setLanguage(language),
              ),
          ],
        ),
      ),
    );
  }
}

class _LanguageOption extends StatelessWidget {
  const _LanguageOption({
    required this.language,
    required this.selected,
    required this.onTap,
  });

  final AppLanguage language;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Semantics(
      inMutuallyExclusiveGroup: true,
      checked: selected,
      label: language == AppLanguage.en
          ? l10n.languageEnglish
          : l10n.languageHindi,
      excludeSemantics: true,
      child: Material(
        color: selected ? AppColors.cardRaised : Colors.transparent,
        borderRadius: const BorderRadius.all(Radius.circular(AppRadii.md)),
        child: InkWell(
          onTap: onTap,
          borderRadius: const BorderRadius.all(Radius.circular(AppRadii.md)),
          child: ConstrainedBox(
            constraints: const BoxConstraints(minWidth: 30, minHeight: 32),
            // Size to the label (min 30×32), not to the whole header height.
            child: Center(
              widthFactor: 1,
              heightFactor: 1,
              child: Padding(
                // Tighter on very narrow phones so the header still fits.
                padding: EdgeInsets.symmetric(
                  horizontal:
                      MediaQuery.sizeOf(context).width < _compactHeaderWidth
                      ? AppSpacing.x1
                      : AppSpacing.x2,
                ),
                child: Text(
                  language.shortLabel,
                  style: AppTypography.caption(weight: FontWeight.w600),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ProfileButton extends StatelessWidget {
  const _ProfileButton({
    required this.session,
    required this.showName,
    required this.onSignOut,
    required this.onOpenSettings,
  });

  final SessionState session;
  final bool showName;
  final VoidCallback onSignOut;
  final VoidCallback onOpenSettings;

  /// "Acting as Doctor" for staff; "Patient" / "Family member" otherwise.
  String _roleText(AppLocalizations l10n) {
    final user = session.user!;
    if (user.isStaff) {
      final role = session.activeRole;
      return role == null ? '' : l10n.actingAs(roleLabel(l10n, role));
    }
    return user.accountType == AccountType.proxy
        ? l10n.accountFamily
        : l10n.accountPatient;
  }

  PopupMenuItem<String> _item(String value, IconData icon, String label) =>
      PopupMenuItem<String>(
        value: value,
        child: Row(
          children: [
            Icon(icon, size: 15, color: AppColors.onCard),
            const SizedBox(width: AppSpacing.x2),
            Text(label, style: AppTypography.small()),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final user = session.user!;
    return PopupMenuButton<String>(
      tooltip: l10n.profileMenuFor(user.displayName),
      position: PopupMenuPosition.under,
      onSelected: (value) => switch (value) {
        'settings' => onOpenSettings(),
        'logout' => onSignOut(),
        _ => null,
      },
      itemBuilder: (_) => [
        PopupMenuItem<String>(
          enabled: false,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                user.displayName,
                style: AppTypography.small(weight: FontWeight.w600),
              ),
              Text(_roleText(l10n), style: AppTypography.caption()),
            ],
          ),
        ),
        const PopupMenuDivider(),
        _item('settings', LucideIcons.settings, l10n.settings),
        _item('logout', LucideIcons.logOut, l10n.logout),
      ],
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.x1,
          vertical: AppSpacing.x1,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            HmsAvatar(name: user.displayName, size: AvatarSize.small),
            if (showName) ...[
              const SizedBox(width: AppSpacing.x2_5),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 128),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      user.displayName,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.small(weight: FontWeight.w600),
                    ),
                    Text(
                      _roleText(l10n),
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.caption(),
                    ),
                  ],
                ),
              ),
              const Icon(
                LucideIcons.chevronDown,
                size: 15,
                color: AppColors.onCardMuted,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _HeaderIconButton extends StatelessWidget {
  const _HeaderIconButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: onTap,
      tooltip: tooltip,
      icon: Icon(icon, size: 20, color: AppColors.onCard),
      style: IconButton.styleFrom(
        minimumSize: const Size.square(AppDimensions.touchTarget),
        shape: const RoundedRectangleBorder(borderRadius: AppRadii.button),
        hoverColor: AppColors.onCardFill,
      ),
    );
  }
}
