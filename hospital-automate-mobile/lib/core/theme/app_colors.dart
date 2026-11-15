import 'package:flutter/painting.dart';

/// HMS colour tokens ("Clinical Calm"), copied from the web app's
/// `src/index.css` @theme block so web and mobile share one palette.
///
/// The web app draws two kinds of surface:
/// * the light page canvas and white popovers, with `ink` text;
/// * teal surfaces (the top header and every card on a page) with white
///   text, from the `.hms-surface-dark` rule. [card] and the `onCard*` and
///   `cardTint*` tokens are that second set.
abstract final class AppColors {
  // Brand: deep clinical teal. 600 is the primary action colour.
  static const brand50 = Color(0xFFEEF8F8);
  static const brand100 = Color(0xFFD6EEEF);
  static const brand200 = Color(0xFFAFDDE0);
  static const brand300 = Color(0xFF7EC4CA);
  static const brand400 = Color(0xFF46A5AE);
  static const brand500 = Color(0xFF258893);
  static const brand600 = Color(0xFF186D79);
  static const brand700 = Color(0xFF155964);
  static const brand800 = Color(0xFF154A53);
  static const brand900 = Color(0xFF143E46);
  static const brand950 = Color(0xFF0B272D);

  // Accent: muted indigo, used sparingly.
  static const accent50 = Color(0xFFF2F3FB);
  static const accent100 = Color(0xFFE4E6F7);
  static const accent500 = Color(0xFF6369BB);
  static const accent600 = Color(0xFF4E54A3);
  static const accent700 = Color(0xFF414586);

  // Neutrals: cool blue-green grey.
  static const ink50 = Color(0xFFF5F7F8);
  static const ink100 = Color(0xFFEDF0F2);
  static const ink200 = Color(0xFFE0E5E9);
  static const ink300 = Color(0xFFC8D0D6);
  static const ink400 = Color(0xFF8D99A4);
  static const ink500 = Color(0xFF56636F);
  static const ink600 = Color(0xFF4D5965);
  static const ink700 = Color(0xFF3B4652);
  static const ink800 = Color(0xFF27303A);
  static const ink900 = Color(0xFF172029);
  static const ink950 = Color(0xFF0D1319);

  // Status colours.
  static const green500 = Color(0xFF2F9A5C);
  static const green600 = Color(0xFF23804A);
  static const green700 = Color(0xFF1D683D);
  static const red500 = Color(0xFFD9493C);
  static const red600 = Color(0xFFBE3529);
  static const red700 = Color(0xFF9D2B21);
  static const amber500 = Color(0xFFD48F12);
  static const amber600 = Color(0xFFA86D0B);
  static const amber700 = Color(0xFF87560D);

  // Page canvas (body) and its backdrop gradient (AppBackground.css).
  static const canvas = Color(0xFFD6EAEB);
  static const canvasTop = Color(0xFFDBEDEE);
  static const canvasBottom = Color(0xFFD1E6E8);

  // Light surfaces: popovers, dialogs, inputs on the canvas.
  static const surface = Color(0xFFFFFFFF);
  static const line = ink200;
  static const lineStrong = ink300;

  // Teal surfaces: header and cards (`--card-surface`, `--card-raised`).
  static const card = Color(0xFF176E79);
  static const cardRaised = Color(0xFF105861);

  /// Primary button fill on a teal surface (darker so it stays visible).
  static const cardButton = Color(0xFF0B4950);
  static const onCard = Color(0xFFFFFFFF);

  /// `--color-ink-300` inside a teal surface: quiet icons and chevrons.
  static const onCardMuted = Color(0xFF8CC3C9);

  /// `--color-line` inside a teal surface (white at 14%).
  static const onCardLine = Color(0x24FFFFFF);

  /// `--color-line-strong` inside a teal surface (white at 26%).
  static const onCardLineStrong = Color(0x42FFFFFF);

  /// `--color-ink-100` inside a teal surface: quiet fills and bar tracks.
  static const onCardFill = Color(0xFF125962);

  /// `--color-ink-50` inside a teal surface: hover / pressed rows.
  static const onCardHover = Color(0xFF135F69);

  // Tints inside a teal surface: color-mix(<tone> 30-32%, #0b3f46).
  static const cardTintBrand = Color(0xFF13565F);
  static const cardTintAccent = Color(0xFF274C6B);
  static const cardTintSuccess = Color(0xFF165A4D);
  static const cardTintWarning = Color(0xFF475736);
  static const cardTintDanger = Color(0xFF494243);

  // Sidebar (`bg-brand-950`) and its text.
  static const sidebar = brand950;
  static const sidebarText = ink300;
  static const sidebarIcon = ink400;
  static const sidebarActiveText = Color(0xFFFFFFFF);
  static const sidebarActiveIcon = brand200;
  static const sidebarActiveFill = Color(0x17FFFFFF); // white/[0.09]
  static const sidebarActiveBar = brand300;
  static const sidebarDivider = Color(0x1AFFFFFF); // white/10
  static const sidebarGroupLabel = Color(0x80AFDDE0); // brand-200/50
  static const sidebarSubtitle = Color(0xB3AFDDE0); // brand-200/70
  static const sidebarFooterText = ink200;
  static const brandMarkFill = Color(0x2646A5AE); // brand-400/15
  static const brandMarkRing = Color(0x4D7EC4CA); // brand-300/30

  /// Backdrop behind the mobile drawer (`bg-ink-950/50`).
  static const scrim = Color(0x800D1319);

  // Guest hero (`bg-brand-900` with brand-100/200 text).
  static const hero = brand900;
  static const heroEyebrow = brand200;
  static const heroBody = Color(0xE6D6EEEF); // brand-100/90
  static const heroOutline = Color(0x4DFFFFFF); // white/30
}
