import 'package:flutter/painting.dart';

import '../../core/theme/app_colors.dart';

/// Semantic tones used by stat tiles, attention rows and alerts (web `tone`).
enum HmsTone {
  brand(AppColors.cardTintBrand),
  accent(AppColors.cardTintAccent),
  success(AppColors.cardTintSuccess),
  warning(AppColors.cardTintWarning),
  danger(AppColors.cardTintDanger),
  neutral(AppColors.onCardFill);

  const HmsTone(this.cardTint);

  /// Icon tile fill on a teal card (`bg-<tone>-50` inside `.hms-surface-dark`).
  final Color cardTint;
}

/// Light alert colours used on the page canvas (States.jsx ALERT_TONES).
enum AlertTone {
  info(
    border: AppColors.brand200,
    fill: AppColors.brand50,
    text: AppColors.brand900,
    icon: AppColors.brand600,
  ),
  success(
    border: Color(0xFFADE0BF),
    fill: Color(0xFFEDF8F1),
    text: Color(0xFF1A5333),
    icon: AppColors.green600,
  ),
  warning(
    border: Color(0xFFF4D48C),
    fill: Color(0xFFFDF6E8),
    text: Color(0xFF6C4511),
    icon: AppColors.amber600,
  ),
  danger(
    border: Color(0xFFF5BCB6),
    fill: Color(0xFFFDF1F0),
    text: Color(0xFF7F251E),
    icon: AppColors.red600,
  );

  const AlertTone({
    required this.border,
    required this.fill,
    required this.text,
    required this.icon,
  });

  final Color border;
  final Color fill;
  final Color text;
  final Color icon;
}
