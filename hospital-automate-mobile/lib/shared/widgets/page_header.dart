import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';

/// PageHeader.jsx: page title and description on the canvas, with actions
/// that wrap below the title on narrow screens.
class PageHeader extends StatelessWidget {
  const PageHeader({
    super.key,
    required this.title,
    this.description,
    this.actions = const [],
  });

  final String title;
  final String? description;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.end,
      spacing: AppSpacing.x6,
      runSpacing: AppSpacing.x3,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Semantics(
              header: true,
              child: Text(title, style: AppTypography.pageTitle()),
            ),
            if (description != null) ...[
              const SizedBox(height: AppSpacing.x1),
              Text(
                description!,
                style: AppTypography.pageDescription(color: AppColors.ink500),
              ),
            ],
          ],
        ),
        if (actions.isNotEmpty)
          Wrap(
            spacing: AppSpacing.x2,
            runSpacing: AppSpacing.x2,
            children: actions,
          ),
      ],
    );
  }
}

/// A section heading on the canvas (`text-base font-semibold` + description).
class SectionHeading extends StatelessWidget {
  const SectionHeading({super.key, required this.title, this.description});

  final String title;
  final String? description;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          header: true,
          child: Text(
            title,
            style: AppTypography.style(16, weight: FontWeight.w600, height: 24),
          ),
        ),
        if (description != null) ...[
          const SizedBox(height: AppSpacing.x1),
          Text(
            description!,
            style: AppTypography.body(color: AppColors.ink500),
          ),
        ],
      ],
    );
  }
}
