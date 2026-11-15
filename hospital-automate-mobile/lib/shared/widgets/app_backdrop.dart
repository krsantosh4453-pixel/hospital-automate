import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// AppBackground.jsx: the canvas gradient with a fine dot grid that fades
/// towards the bottom. The pointer glow is desktop-only on the web and is
/// left out on touch screens.
class AppBackdrop extends StatelessWidget {
  const AppBackdrop({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          stops: [0, 0.42, 1],
          colors: [
            AppColors.canvasTop,
            AppColors.canvas,
            AppColors.canvasBottom,
          ],
        ),
      ),
      child: CustomPaint(painter: const _DotGridPainter(), child: child),
    );
  }
}

class _DotGridPainter extends CustomPainter {
  const _DotGridPainter();

  static const _spacing = 24.0;
  static const _radius = 1.0;
  static const _dot = Color(0x21155964); // rgb(21 89 100 / 0.13)

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final paint = Paint();
    for (var y = _spacing / 2; y < size.height; y += _spacing) {
      // Fade like the web mask: full at the top, 55% at mid-height, none at the bottom.
      final t = y / size.height;
      final fade = t < 0.55
          ? 1 - 0.45 * (t / 0.55)
          : 0.55 * (1 - (t - 0.55) / 0.45);
      paint.color = _dot.withValues(alpha: _dot.a * fade);
      for (var x = _spacing / 2; x < size.width; x += _spacing) {
        canvas.drawCircle(Offset(x, y), _radius, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _DotGridPainter oldDelegate) => false;
}
