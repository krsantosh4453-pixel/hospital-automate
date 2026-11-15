import 'package:flutter/painting.dart';

import 'app_colors.dart';

/// Type scale used by the web pages. The font is Inter (variable), bundled in
/// `assets/fonts`, as the web loads `@fontsource-variable/inter`. Devanagari
/// text falls back to the platform's Noto font, as on the web.
abstract final class AppTypography {
  static const fontFamily = 'Inter';

  /// Web body text uses `font-feature-settings: "cv11", "ss01"`.
  static const _features = [FontFeature('cv11'), FontFeature('ss01')];

  /// Tabular figures for counts and money (`tabular-nums`).
  static const tabular = [..._features, FontFeature.tabularFigures()];

  /// A text style in Inter at [size] and [weight]. The weight is also set on
  /// the variable font's `wght` axis, which Flutter does not do by itself.
  static TextStyle style(
    double size, {
    FontWeight weight = FontWeight.w400,
    double? height,
    Color color = AppColors.ink900,
    double? letterSpacing,
    bool tabularFigures = false,
  }) {
    return TextStyle(
      fontFamily: fontFamily,
      fontSize: size,
      fontWeight: weight,
      fontVariations: [FontVariation.weight(weight.value.toDouble())],
      fontFeatures: tabularFigures ? tabular : _features,
      height: height == null ? null : height / size,
      color: color,
      letterSpacing: letterSpacing,
    );
  }

  /// PageHeader `h1`: 22px/32 semibold, tracking -0.01em.
  static TextStyle pageTitle({Color color = AppColors.ink900}) => style(
    22,
    weight: FontWeight.w600,
    height: 32,
    color: color,
    letterSpacing: -0.22,
  );

  /// PageHeader description: 14px/24.
  static TextStyle pageDescription({Color color = AppColors.ink500}) =>
      style(14, height: 24, color: color);

  /// CardHeader title: 15px/24 semibold.
  static TextStyle cardTitle({Color color = AppColors.onCard}) =>
      style(15, weight: FontWeight.w600, height: 24, color: color);

  /// CardHeader description and secondary text: 13px/20.
  static TextStyle small({
    Color color = AppColors.onCard,
    FontWeight weight = FontWeight.w400,
  }) => style(13, weight: weight, height: 20, color: color);

  /// Body text: 14px/20.
  static TextStyle body({
    Color color = AppColors.onCard,
    FontWeight weight = FontWeight.w400,
  }) => style(14, weight: weight, height: 20, color: color);

  /// Hints and meta text: 12px/16.
  static TextStyle caption({
    Color color = AppColors.onCard,
    FontWeight weight = FontWeight.w400,
  }) => style(12, weight: weight, height: 16, color: color);

  /// StatTile value: 24px/32 semibold, tight tracking, tabular figures.
  static TextStyle statValue({Color color = AppColors.onCard}) => style(
    24,
    weight: FontWeight.w600,
    height: 32,
    color: color,
    letterSpacing: -0.6,
    tabularFigures: true,
  );

  /// Sidebar items: 13.5px medium.
  static TextStyle navItem({Color color = AppColors.sidebarText}) =>
      style(13.5, weight: FontWeight.w500, height: 20, color: color);

  /// Sidebar group labels: 11px semibold uppercase, tracking 0.08em.
  static TextStyle navGroup() => style(
    11,
    weight: FontWeight.w600,
    height: 16,
    color: AppColors.sidebarGroupLabel,
    letterSpacing: 0.88,
  );
}
