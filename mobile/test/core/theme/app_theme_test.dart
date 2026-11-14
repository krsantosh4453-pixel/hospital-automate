import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/theme/app_colors.dart';
import 'package:hms_mobile/core/theme/app_theme.dart';
import 'package:hms_mobile/core/theme/app_typography.dart';

void main() {
  test('colour tokens equal the web values in src/index.css', () {
    expect(AppColors.brand600, const Color(0xFF186D79));
    expect(AppColors.brand950, const Color(0xFF0B272D));
    expect(AppColors.canvas, const Color(0xFFD6EAEB));
    expect(AppColors.card, const Color(0xFF176E79), reason: '--card-surface');
    expect(
      AppColors.cardRaised,
      const Color(0xFF105861),
      reason: '--card-raised',
    );
    expect(AppColors.ink900, const Color(0xFF172029));
  });

  test('teal-surface tints match the web color-mix() results', () {
    // color-mix(in srgb, #258893 32%, #0b3f46)
    expect(AppColors.cardTintBrand, const Color(0xFF13565F));
    // color-mix(in srgb, #d9493c 30%, #0b3f46)
    expect(AppColors.cardTintDanger, const Color(0xFF494243));
  });

  test('the Material theme is built from HMS tokens, not a seed colour', () {
    final theme = AppTheme.light();

    expect(theme.colorScheme.primary, AppColors.brand600);
    expect(theme.scaffoldBackgroundColor, AppColors.canvas);
    expect(theme.dialogTheme.backgroundColor, AppColors.card);
    expect(theme.textTheme.bodyMedium?.fontFamily, AppTypography.fontFamily);
  });

  test('type styles set the variable font weight axis', () {
    final style = AppTypography.pageTitle();

    expect(style.fontSize, 22);
    expect(style.fontWeight, FontWeight.w600);
    expect(style.fontVariations?.single.value, 600);
  });
}
