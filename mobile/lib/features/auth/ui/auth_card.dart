import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_body.dart';

/// The web sign-in panel (`hms-surface-dark rounded-2xl p-6 sm:p-8`): an
/// eyebrow ("Staff portal"), title, subtitle and the form, centred on the
/// canvas at up to 448 px wide.
class AuthPage extends StatelessWidget {
  const AuthPage({
    super.key,
    required this.location,
    required this.eyebrow,
    required this.title,
    required this.subtitle,
    required this.children,
    this.footer = const [],
  });

  final String location;
  final String eyebrow;
  final String title;
  final String subtitle;
  final List<Widget> children;

  /// Shown under the card (e.g. "New here? Create account").
  final List<Widget> footer;

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.sm;
    return PageBody(
      location: location,
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 448),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                HmsCard(
                  padding: EdgeInsets.all(wide ? AppSpacing.x8 : AppSpacing.x6),
                  child: AutofillGroup(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          eyebrow.toUpperCase(),
                          style: AppTypography.caption(weight: FontWeight.w600)
                              .copyWith(letterSpacing: 1.2),
                        ),
                        const SizedBox(height: AppSpacing.x1),
                        Semantics(
                          header: true,
                          child: Text(
                            title,
                            style: AppTypography.style(
                              24,
                              weight: FontWeight.w600,
                              height: 32,
                              color: AppColors.onCard,
                              letterSpacing: -0.6,
                            ),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.x1),
                        Text(subtitle, style: AppTypography.body()),
                        const SizedBox(height: AppSpacing.x6),
                        ...children,
                      ],
                    ),
                  ),
                ),
                for (final widget in footer) ...[
                  const SizedBox(height: AppSpacing.x4),
                  widget,
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }
}

enum AuthNoticeTone { error, info }

/// An inline message inside the teal card (error or confirmation).
class AuthNotice extends StatelessWidget {
  const AuthNotice({
    super.key,
    required this.message,
    this.tone = AuthNoticeTone.error,
  });

  final String message;
  final AuthNoticeTone tone;

  @override
  Widget build(BuildContext context) {
    final error = tone == AuthNoticeTone.error;
    return Semantics(
      liveRegion: true,
      child: Container(
        margin: const EdgeInsets.only(bottom: AppSpacing.x4),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.x3,
          vertical: AppSpacing.x2_5,
        ),
        decoration: BoxDecoration(
          color: error ? AppColors.cardTintDanger : AppColors.cardTintBrand,
          borderRadius: AppRadii.button,
          border: Border.all(color: AppColors.onCardLineStrong),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              error ? LucideIcons.circleAlert : LucideIcons.info,
              size: 17,
              color: AppColors.onCard,
            ),
            const SizedBox(width: AppSpacing.x2),
            Expanded(child: Text(message, style: AppTypography.small())),
          ],
        ),
      ),
    );
  }
}

/// A small text link inside the card ("Forgot password?", "Resend code").
class AuthLink extends StatelessWidget {
  const AuthLink({
    super.key,
    required this.label,
    required this.onTap,
    this.icon,
  });

  final String label;
  final VoidCallback? onTap;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.button,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 40),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.x1),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[
                  Icon(icon, size: 14, color: AppColors.onCard),
                  const SizedBox(width: AppSpacing.x1_5),
                ],
                Flexible(
                  child: Text(
                    label,
                    style: AppTypography.small(weight: FontWeight.w500),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
