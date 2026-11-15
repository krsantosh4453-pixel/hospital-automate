import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';

/// Button.jsx variants.
enum HmsButtonVariant { primary, secondary, ghost, danger }

enum HmsButtonSize {
  small(AppDimensions.controlSmall, AppSpacing.x3, 13, 15),
  medium(AppDimensions.control, AppSpacing.x4, 14, 17),
  large(AppDimensions.controlLarge, AppSpacing.x5, 15, 17);

  const HmsButtonSize(this.height, this.padding, this.fontSize, this.iconSize);

  final double height;
  final double padding;
  final double fontSize;
  final double iconSize;
}

/// Where the button sits: the light page canvas, or a teal surface (card,
/// header, dialog), where the web swaps white fills for raised teal.
enum HmsSurface { canvas, card }

/// The one button used across the app, matching the web `Button`.
class HmsButton extends StatelessWidget {
  const HmsButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.variant = HmsButtonVariant.primary,
    this.size = HmsButtonSize.medium,
    this.surface = HmsSurface.canvas,
    this.loading = false,
    this.expand = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final HmsButtonVariant variant;
  final HmsButtonSize size;
  final HmsSurface surface;
  final bool loading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final colors = _colors();
    final enabled = onPressed != null && !loading;
    final child = Row(
      mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (loading)
          SizedBox.square(
            dimension: size.iconSize,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: colors.foreground,
            ),
          )
        else if (icon != null)
          Icon(icon, size: size.iconSize, color: colors.foreground),
        if (loading || icon != null)
          SizedBox(width: size == HmsButtonSize.small ? 6 : 8),
        Flexible(
          child: Text(
            label,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.style(
              size.fontSize,
              weight: FontWeight.w500,
              color: colors.foreground,
            ),
          ),
        ),
      ],
    );
    return Semantics(
      button: true,
      enabled: enabled,
      child: Opacity(
        opacity: enabled ? 1 : 0.6,
        child: Material(
          color: colors.fill,
          shape: RoundedRectangleBorder(
            borderRadius: AppRadii.button,
            side: colors.border == null
                ? BorderSide.none
                : BorderSide(color: colors.border!),
          ),
          child: InkWell(
            onTap: enabled ? onPressed : null,
            borderRadius: AppRadii.button,
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minHeight: size.height,
                minWidth: size.height,
              ),
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: size.padding),
                child: child,
              ),
            ),
          ),
        ),
      ),
    );
  }

  _ButtonColors _colors() {
    final onCard = surface == HmsSurface.card;
    return switch (variant) {
      HmsButtonVariant.primary => _ButtonColors(
        onCard ? AppColors.cardButton : AppColors.brand600,
        Colors.white,
      ),
      HmsButtonVariant.secondary =>
        onCard
            ? const _ButtonColors(
                AppColors.cardRaised,
                AppColors.onCard,
                AppColors.onCardLineStrong,
              )
            : const _ButtonColors(
                AppColors.surface,
                AppColors.ink800,
                AppColors.lineStrong,
              ),
      HmsButtonVariant.ghost => _ButtonColors(
        Colors.transparent,
        onCard ? AppColors.onCard : AppColors.ink700,
      ),
      HmsButtonVariant.danger => const _ButtonColors(
        AppColors.red600,
        Colors.white,
      ),
    };
  }
}

class _ButtonColors {
  const _ButtonColors(this.fill, this.foreground, [this.border]);

  final Color fill;
  final Color foreground;
  final Color? border;
}
