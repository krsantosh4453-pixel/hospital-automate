import 'package:flutter/painting.dart';

/// Shadows from index.css (`--shadow-*`), all tinted `rgb(15 30 40)`.
abstract final class AppShadows {
  static const _tint = Color(0xFF0F1E28);

  static final sm = [
    BoxShadow(
      color: _tint.withValues(alpha: 0.05),
      offset: const Offset(0, 1),
      blurRadius: 2,
    ),
  ];

  static final md = [
    BoxShadow(
      color: _tint.withValues(alpha: 0.08),
      offset: const Offset(0, 3),
      blurRadius: 8,
      spreadRadius: -2,
    ),
    BoxShadow(
      color: _tint.withValues(alpha: 0.04),
      offset: const Offset(0, 2),
      blurRadius: 4,
      spreadRadius: -2,
    ),
  ];

  static final xl = [
    BoxShadow(
      color: _tint.withValues(alpha: 0.18),
      offset: const Offset(0, 16),
      blurRadius: 36,
      spreadRadius: -10,
    ),
    BoxShadow(
      color: _tint.withValues(alpha: 0.06),
      offset: const Offset(0, 6),
      blurRadius: 12,
      spreadRadius: -6,
    ),
  ];

  static final xxl = [
    BoxShadow(
      color: _tint.withValues(alpha: 0.22),
      offset: const Offset(0, 24),
      blurRadius: 48,
      spreadRadius: -12,
    ),
  ];
}
