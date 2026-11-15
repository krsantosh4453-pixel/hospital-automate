import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_spacing.dart';
import 'app_typography.dart';

/// The one Material theme for the app, built only from HMS tokens.
///
/// Material widgets (dialogs, sheets, menus, inputs, snack bars) are styled
/// like the web app's teal surfaces so a stock widget never shows a
/// different design language.
abstract final class AppTheme {
  static ThemeData light() {
    const scheme = ColorScheme(
      brightness: Brightness.light,
      primary: AppColors.brand600,
      onPrimary: Colors.white,
      primaryContainer: AppColors.brand100,
      onPrimaryContainer: AppColors.brand900,
      secondary: AppColors.accent600,
      onSecondary: Colors.white,
      error: AppColors.red600,
      onError: Colors.white,
      surface: AppColors.canvas,
      onSurface: AppColors.ink900,
      onSurfaceVariant: AppColors.ink500,
      outline: AppColors.lineStrong,
      outlineVariant: AppColors.line,
      scrim: AppColors.scrim,
    );

    final text = TextTheme(
      headlineSmall: AppTypography.pageTitle(),
      titleLarge: AppTypography.style(18, weight: FontWeight.w600, height: 28),
      titleMedium: AppTypography.style(16, weight: FontWeight.w600, height: 24),
      titleSmall: AppTypography.cardTitle(color: AppColors.ink900),
      bodyLarge: AppTypography.style(15, height: 24),
      bodyMedium: AppTypography.body(color: AppColors.ink900),
      bodySmall: AppTypography.small(color: AppColors.ink500),
      labelLarge: AppTypography.body(
        weight: FontWeight.w500,
        color: AppColors.ink900,
      ),
      labelMedium: AppTypography.small(
        weight: FontWeight.w500,
        color: AppColors.ink700,
      ),
      labelSmall: AppTypography.caption(
        weight: FontWeight.w500,
        color: AppColors.ink500,
      ),
    );

    const onCardRounded = RoundedRectangleBorder(borderRadius: AppRadii.card);

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      fontFamily: AppTypography.fontFamily,
      textTheme: text,
      scaffoldBackgroundColor: AppColors.canvas,
      splashFactory: InkRipple.splashFactory,
      visualDensity: VisualDensity.standard,
      iconTheme: const IconThemeData(color: AppColors.ink600, size: 20),
      dividerTheme: const DividerThemeData(
        color: AppColors.onCardLine,
        thickness: 1,
        space: 1,
      ),
      // Modal.jsx: teal surface, rounded-2xl, bottom sheet on phones.
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.card,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(AppRadii.xxxl)),
        ),
        titleTextStyle: AppTypography.style(
          16,
          weight: FontWeight.w600,
          height: 24,
          color: AppColors.onCard,
        ),
        contentTextStyle: AppTypography.body(color: AppColors.onCard)
            .copyWith(height: 24 / 14),
        barrierColor: AppColors.ink950.withValues(alpha: 0.45),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.card,
        surfaceTintColor: Colors.transparent,
        modalBarrierColor: Color(0x730D1319),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadii.xxxl),
          ),
        ),
        showDragHandle: true,
        dragHandleColor: AppColors.onCardLineStrong,
      ),
      // Header popovers (`popoverPanel` inside the teal header): raised teal.
      popupMenuTheme: PopupMenuThemeData(
        color: AppColors.cardRaised,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: AppRadii.popover,
          side: BorderSide(color: AppColors.onCardLine),
        ),
        textStyle: AppTypography.small(),
        elevation: 8,
      ),
      cardTheme: const CardThemeData(
        color: AppColors.card,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: onCardRounded,
      ),
      // `.hms-input` on a light surface.
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.x3,
          vertical: 10,
        ),
        hintStyle: AppTypography.body(color: AppColors.ink400),
        border: _inputBorder(AppColors.lineStrong),
        enabledBorder: _inputBorder(AppColors.lineStrong),
        focusedBorder: _inputBorder(AppColors.brand500),
        errorBorder: _inputBorder(AppColors.red500),
        focusedErrorBorder: _inputBorder(AppColors.red500),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.ink900,
        contentTextStyle: AppTypography.body(color: Colors.white),
        shape: const RoundedRectangleBorder(borderRadius: AppRadii.card),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.brand500,
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: AppColors.ink900,
          borderRadius: BorderRadius.circular(AppRadii.md),
        ),
        textStyle: AppTypography.caption(color: Colors.white),
      ),
    );
  }

  static OutlineInputBorder _inputBorder(Color color) => OutlineInputBorder(
    borderRadius: AppRadii.input,
    borderSide: BorderSide(color: color),
  );
}
