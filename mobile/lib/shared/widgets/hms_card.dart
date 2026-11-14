import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';

/// Card.jsx: a teal surface (`rounded-2xl border border-line`) with white text.
class HmsCard extends StatelessWidget {
  const HmsCard({
    super.key,
    required this.child,
    this.padding = EdgeInsets.zero,
    this.onTap,
    this.semanticLabel,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final content = Padding(padding: padding, child: child);
    return Semantics(
      container: true,
      label: semanticLabel,
      child: Material(
        color: AppColors.card,
        shape: const RoundedRectangleBorder(
          borderRadius: AppRadii.card,
          side: BorderSide(color: AppColors.onCardLine),
        ),
        clipBehavior: Clip.antiAlias,
        child: onTap == null
            ? content
            : InkWell(
                onTap: onTap,
                hoverColor: AppColors.onCardHover,
                splashColor: AppColors.onCardLine,
                child: content,
              ),
      ),
    );
  }
}

/// CardHeader: title and optional description on the left, actions on the right.
class HmsCardHeader extends StatelessWidget {
  const HmsCardHeader({
    super.key,
    required this.title,
    this.description,
    this.icon,
    this.trailing,
  });

  final String title;
  final String? description;
  final IconData? icon;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.onCardLine)),
      ),
      child: Padding(
        padding: AppSpacing.cardHeader,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (icon != null) ...[
              Container(
                width: 32,
                height: 32,
                margin: const EdgeInsets.only(top: 2),
                decoration: const BoxDecoration(
                  color: AppColors.cardTintBrand,
                  borderRadius: BorderRadius.all(Radius.circular(AppRadii.lg)),
                ),
                child: Icon(icon, size: 17, color: AppColors.onCard),
              ),
              const SizedBox(width: AppSpacing.x3),
            ],
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Semantics(
                    header: true,
                    child: Text(title, style: AppTypography.cardTitle()),
                  ),
                  if (description != null) ...[
                    const SizedBox(height: 2),
                    Text(description!, style: AppTypography.small()),
                  ],
                ],
              ),
            ),
            if (trailing != null) ...[
              const SizedBox(width: AppSpacing.x3),
              trailing!,
            ],
          ],
        ),
      ),
    );
  }
}

/// Rows separated by the card's divider (`divide-y divide-line`).
class HmsDividedColumn extends StatelessWidget {
  const HmsDividedColumn({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0) const Divider(height: 1, color: AppColors.onCardLine),
          children[i],
        ],
      ],
    );
  }
}

/// A 40×40 rounded icon tile (`h-10 w-10 rounded-xl`), used by stat tiles and department cards.
class HmsIconTile extends StatelessWidget {
  const HmsIconTile({
    super.key,
    required this.icon,
    required this.fill,
    this.size = 40,
    this.iconSize = 20,
  });

  final IconData icon;
  final Color fill;
  final double size;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: fill, borderRadius: AppRadii.iconTile),
      child: Icon(icon, size: iconSize, color: AppColors.onCard),
    );
  }
}
