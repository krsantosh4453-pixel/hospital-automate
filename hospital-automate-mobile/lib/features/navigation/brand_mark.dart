import 'package:flutter/material.dart';

import '../../core/localization/l10n.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';

/// BrandMark (Sidebar.jsx): the HMS cross with a pulse notch, and the name.
class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Semantics(
      label: '${l10n.appName}, ${l10n.appSubtitle}',
      excludeSemantics: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.brandMarkFill,
              borderRadius: AppRadii.iconTile.add(
                const BorderRadius.all(Radius.circular(2)),
              ),
              border: Border.all(color: AppColors.brandMarkRing),
            ),
            child: const Center(
              child: CustomPaint(
                size: Size.square(20),
                painter: _CrossPainter(),
              ),
            ),
          ),
          if (!compact) ...[
            const SizedBox(width: AppSpacing.x2_5),
            Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    l10n.appName,
                    style: AppTypography.style(
                      15,
                      weight: FontWeight.w600,
                      height: 19,
                      color: Colors.white,
                      letterSpacing: -0.4,
                    ),
                  ),
                  Text(
                    l10n.appSubtitle,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.style(
                      11,
                      height: 14,
                      color: AppColors.sidebarSubtitle,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// The 24×24 SVG from Sidebar.jsx, scaled to [size].
class _CrossPainter extends CustomPainter {
  const _CrossPainter();

  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / 24);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        const Rect.fromLTWH(9.25, 3, 5.5, 18),
        const Radius.circular(2.2),
      ),
      Paint()..color = AppColors.brand300,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        const Rect.fromLTWH(3, 9.25, 18, 5.5),
        const Radius.circular(2.2),
      ),
      Paint()..color = AppColors.brand100,
    );
    final pulse = Path()
      ..moveTo(6.5, 12)
      ..lineTo(9.5, 12)
      ..lineTo(10.7, 9.8)
      ..lineTo(12.7, 14.2)
      ..lineTo(14, 12)
      ..lineTo(17.5, 12);
    canvas.drawPath(
      pulse,
      Paint()
        ..color = AppColors.brand950
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.4
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(covariant _CrossPainter oldDelegate) => false;
}
