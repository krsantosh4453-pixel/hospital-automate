import 'package:flutter/widgets.dart';

/// Spacing on Tailwind's 4 px scale, as used by the web pages.
abstract final class AppSpacing {
  static const double x0_5 = 2;
  static const double x1 = 4;
  static const double x1_5 = 6;
  static const double x2 = 8;
  static const double x2_5 = 10;
  static const double x3 = 12;
  static const double x3_5 = 14;
  static const double x4 = 16;
  static const double x5 = 20;
  static const double x6 = 24;
  static const double x8 = 32;
  static const double x10 = 40;

  /// Page padding: `px-4 py-5` on phones, `sm:px-6 sm:py-6`.
  static const EdgeInsets pagePhone = EdgeInsets.fromLTRB(x4, x5, x4, x8);
  static const EdgeInsets pageWide = EdgeInsets.fromLTRB(x6, x6, x6, x8);

  /// Card header and body rows: `px-5 py-4`; list rows: `px-5 py-3`.
  static const EdgeInsets cardHeader = EdgeInsets.symmetric(
    horizontal: x5,
    vertical: x4,
  );
  static const EdgeInsets cardRow = EdgeInsets.symmetric(
    horizontal: x5,
    vertical: x3,
  );
}

/// Fixed sizes from the web layout.
abstract final class AppDimensions {
  /// Header height (`h-16`).
  static const double headerHeight = 64;

  /// Desktop sidebar (`w-64`) and its collapsed icon rail (`w-[72px]`).
  static const double sidebarWidth = 256;
  static const double sidebarRailWidth = 72;

  /// Mobile drawer: `w-[min(18rem,85vw)]`.
  static const double drawerMaxWidth = 288;
  static const double drawerViewportFraction = 0.85;

  /// Controls: `h-10` buttons and icon buttons, `h-8` small buttons.
  static const double control = 40;
  static const double controlSmall = 32;
  static const double controlLarge = 44;

  /// Minimum touch target on phones (Material guidance), never below the web size.
  static const double touchTarget = 48;

  /// Page content is capped at `max-w-[1600px]`.
  static const double contentMaxWidth = 1600;
}

/// Breakpoints, matching Tailwind's `sm`, `md`, `lg`, `xl`.
abstract final class AppBreakpoints {
  static const double sm = 640;
  static const double md = 768;
  static const double lg = 1024;
  static const double xl = 1280;
}

/// Corner radii (`--radius-*` in index.css).
abstract final class AppRadii {
  static const double md = 6;
  static const double lg = 8;
  static const double xl = 10;
  static const double xxl = 12;
  static const double xxxl = 16;

  static const BorderRadius button = BorderRadius.all(Radius.circular(lg));
  static const BorderRadius input = BorderRadius.all(Radius.circular(lg));
  static const BorderRadius iconTile = BorderRadius.all(Radius.circular(xl));
  static const BorderRadius card = BorderRadius.all(Radius.circular(xxl));
  static const BorderRadius popover = BorderRadius.all(Radius.circular(xl));
  static const BorderRadius pill = BorderRadius.all(Radius.circular(999));
}
