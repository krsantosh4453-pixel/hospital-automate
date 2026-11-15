import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import 'hms_button.dart';
import 'tone.dart';

/// Alert (States.jsx): an inline message on the page canvas.
class HmsAlert extends StatelessWidget {
  const HmsAlert({
    super.key,
    this.tone = AlertTone.info,
    required this.title,
    this.message,
    this.action,
  });

  final AlertTone tone;
  final String title;
  final String? message;
  final Widget? action;

  static const _icons = {
    AlertTone.info: LucideIcons.info,
    AlertTone.success: LucideIcons.circleCheck,
    AlertTone.warning: LucideIcons.triangleAlert,
    AlertTone.danger: LucideIcons.circleAlert,
  };

  @override
  Widget build(BuildContext context) {
    final urgent = tone == AlertTone.danger || tone == AlertTone.warning;
    return Semantics(
      liveRegion: urgent,
      container: true,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.x4,
          vertical: AppSpacing.x3,
        ),
        decoration: BoxDecoration(
          color: tone.fill,
          border: Border.all(color: tone.border),
          borderRadius: const BorderRadius.all(Radius.circular(AppRadii.xxl)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Icon(_icons[tone], size: 18, color: tone.icon),
            ),
            const SizedBox(width: AppSpacing.x3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: AppTypography.body(
                      weight: FontWeight.w600,
                      color: tone.text,
                    ),
                  ),
                  if (message != null)
                    Text(message!, style: AppTypography.body(color: tone.text)),
                ],
              ),
            ),
            if (action != null) ...[
              const SizedBox(width: AppSpacing.x3),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}

/// EmptyState (States.jsx), drawn inside a teal card. Never shows invented data.
class HmsEmptyState extends StatelessWidget {
  const HmsEmptyState({
    super.key,
    required this.title,
    this.icon = LucideIcons.inbox,
    this.description,
    this.action,
    this.compact = false,
  });

  final String title;
  final IconData icon;
  final String? description;
  final Widget? action;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: compact
          ? const EdgeInsets.symmetric(
              horizontal: AppSpacing.x4,
              vertical: AppSpacing.x8,
            )
          : const EdgeInsets.symmetric(horizontal: AppSpacing.x6, vertical: 56),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: const BoxDecoration(
              color: AppColors.onCardFill,
              borderRadius: AppRadii.card,
            ),
            child: Icon(icon, size: 22, color: AppColors.onCard),
          ),
          const SizedBox(height: AppSpacing.x3),
          Text(
            title,
            textAlign: TextAlign.center,
            style: AppTypography.body(weight: FontWeight.w600),
          ),
          if (description != null) ...[
            const SizedBox(height: AppSpacing.x1),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 384),
              child: Text(
                description!,
                textAlign: TextAlign.center,
                style: AppTypography.small(),
              ),
            ),
          ],
          if (action != null) ...[
            const SizedBox(height: AppSpacing.x4),
            action!,
          ],
        ],
      ),
    );
  }
}

/// ErrorState: an empty state with a retry button. [error] is shown through
/// [apiErrorMessage], so no server text or record detail reaches the screen.
class HmsErrorState extends StatelessWidget {
  const HmsErrorState({
    super.key,
    required this.error,
    this.onRetry,
    this.title,
  });

  final Object error;
  final VoidCallback? onRetry;
  final String? title;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return HmsEmptyState(
      icon: LucideIcons.circleAlert,
      title: title ?? l10n.somethingWentWrong,
      description: apiErrorMessage(l10n, error),
      action: onRetry == null
          ? null
          : HmsButton(
              label: l10n.tryAgain,
              onPressed: onRetry,
              variant: HmsButtonVariant.secondary,
              surface: HmsSurface.card,
            ),
    );
  }
}

/// Centred spinner for a loading region.
class HmsLoading extends StatelessWidget {
  const HmsLoading({super.key, this.label});

  final String? label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label ?? context.l10n.loading,
      child: const Padding(
        padding: EdgeInsets.all(AppSpacing.x8),
        child: Center(
          child: SizedBox.square(
            dimension: 24,
            child: CircularProgressIndicator(strokeWidth: 2.4),
          ),
        ),
      ),
    );
  }
}

/// `.skeleton`: a placeholder block with a slow shimmer, on the canvas.
class HmsSkeleton extends StatefulWidget {
  const HmsSkeleton({super.key, this.height = 88, this.radius = AppRadii.xxxl});

  final double height;
  final double radius;

  @override
  State<HmsSkeleton> createState() => _HmsSkeletonState();
}

class _HmsSkeletonState extends State<HmsSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Respect reduced motion, as the web does under prefers-reduced-motion.
    if (MediaQuery.disableAnimationsOf(context)) {
      _controller.stop();
    } else if (!_controller.isAnimating) {
      _controller.repeat();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: context.l10n.loading,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) => Container(
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.radius),
            gradient: LinearGradient(
              begin: Alignment(-1 + 2 * _controller.value - 1, 0),
              end: Alignment(1 + 2 * _controller.value - 1, 0),
              colors: const [
                AppColors.ink100,
                AppColors.ink50,
                AppColors.ink100,
              ],
            ),
          ),
        ),
      ),
    );
  }
}
