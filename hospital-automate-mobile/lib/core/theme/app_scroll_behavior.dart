import 'package:flutter/material.dart';

/// App-wide scrolling. Material 3 on Android 12+ shows overscroll by
/// stretching the scrolled content (a vertical scale transform), which
/// elongates every line of text at the top and bottom of a page. The glow
/// indicator gives the same "end of list" feedback without resizing content.
/// Scroll physics, scrollbars and text scaling are left to the platform.
class HmsScrollBehavior extends MaterialScrollBehavior {
  const HmsScrollBehavior();

  @override
  Widget buildOverscrollIndicator(
    BuildContext context,
    Widget child,
    ScrollableDetails details,
  ) {
    switch (getPlatform(context)) {
      case TargetPlatform.android:
      case TargetPlatform.fuchsia:
        return GlowingOverscrollIndicator(
          axisDirection: details.direction,
          color: Theme.of(context).colorScheme.secondary,
          child: child,
        );
      case TargetPlatform.iOS:
      case TargetPlatform.linux:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
        return child;
    }
  }
}
