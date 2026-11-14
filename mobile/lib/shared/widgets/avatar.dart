import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';

enum AvatarSize {
  small(28, 11),
  medium(36, 12),
  large(48, 14);

  const AvatarSize(this.diameter, this.fontSize);

  final double diameter;
  final double fontSize;
}

/// Avatar (Data.jsx): up to two initials in a tinted circle. Decorative,
/// so screen readers read the name next to it instead.
class HmsAvatar extends StatelessWidget {
  const HmsAvatar({
    super.key,
    required this.name,
    this.size = AvatarSize.medium,
  });

  final String name;
  final AvatarSize size;

  static String initialsOf(String name) {
    final parts = name
        .trim()
        .split(RegExp(r'\s+'))
        .where((p) => p.isNotEmpty)
        .take(2);
    final initials = parts.map((p) => p.characters.first.toUpperCase()).join();
    return initials.isEmpty ? '?' : initials;
  }

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: Container(
        width: size.diameter,
        height: size.diameter,
        alignment: Alignment.center,
        // brand-100 / brand-800 inside a teal surface.
        decoration: const BoxDecoration(
          color: Color(0xFF176069),
          shape: BoxShape.circle,
        ),
        child: Text(
          initialsOf(name),
          style: AppTypography.style(
            size.fontSize,
            weight: FontWeight.w600,
            color: AppColors.onCard,
          ),
        ),
      ),
    );
  }
}
