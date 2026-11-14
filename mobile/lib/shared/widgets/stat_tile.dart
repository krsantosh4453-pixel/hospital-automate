import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import 'hms_card.dart';
import 'tone.dart';

/// StatTile (Data.jsx): icon tile, label, big value and an optional hint.
/// A missing value shows "—", never an invented number.
class StatTile extends StatelessWidget {
  const StatTile({
    super.key,
    required this.label,
    this.value,
    required this.icon,
    this.tone = HmsTone.brand,
    this.hint,
  });

  final String label;
  final String? value;
  final IconData icon;
  final HmsTone tone;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    final shown = (value == null || value!.isEmpty) ? '—' : value!;
    return HmsCard(
      padding: const EdgeInsets.all(AppSpacing.x4),
      semanticLabel: '$label: $shown${hint == null ? '' : ', $hint'}',
      child: ExcludeSemantics(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            HmsIconTile(icon: icon, fill: tone.cardTint),
            const SizedBox(width: AppSpacing.x3_5),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: AppTypography.small(weight: FontWeight.w500),
                  ),
                  const SizedBox(height: 2),
                  Text(shown, style: AppTypography.statValue()),
                  if (hint != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      hint!,
                      style: AppTypography.caption(color: AppColors.onCard),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Grid of stat tiles: two columns on phones, four from `xl` (as `grid-cols-2 xl:grid-cols-4`).
class StatTileGrid extends StatelessWidget {
  const StatTileGrid({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    // Tailwind breakpoints are viewport widths, so read the screen, not the parent.
    final viewport = MediaQuery.sizeOf(context).width;
    final columns = viewport >= AppBreakpoints.xl ? 4 : 2;
    final gap = viewport >= AppBreakpoints.sm ? AppSpacing.x4 : AppSpacing.x3;
    return ResponsiveGrid(columns: columns, gap: gap, children: children);
  }
}

/// Lays [children] out in rows of [columns], each row as tall as its tallest cell.
class ResponsiveGrid extends StatelessWidget {
  const ResponsiveGrid({
    super.key,
    required this.columns,
    required this.gap,
    required this.children,
  });

  final int columns;
  final double gap;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];
    for (var start = 0; start < children.length; start += columns) {
      final cells = children.sublist(
        start,
        (start + columns).clamp(0, children.length),
      );
      rows.add(
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (var i = 0; i < columns; i++) ...[
                if (i > 0) SizedBox(width: gap),
                Expanded(
                  child: i < cells.length ? cells[i] : const SizedBox.shrink(),
                ),
              ],
            ],
          ),
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < rows.length; i++) ...[
          if (i > 0) SizedBox(height: gap),
          rows[i],
        ],
      ],
    );
  }
}
