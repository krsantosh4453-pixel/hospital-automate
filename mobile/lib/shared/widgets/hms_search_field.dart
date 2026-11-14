import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import 'hms_button.dart';

/// `.hms-input` with a search icon. On a teal surface the web swaps the white
/// field for raised teal with white text; [surface] picks the variant.
class HmsSearchField extends StatelessWidget {
  const HmsSearchField({
    super.key,
    required this.hint,
    required this.onChanged,
    this.semanticLabel,
    this.autofocus = false,
    this.surface = HmsSurface.card,
    this.onSubmitted,
  });

  final String hint;
  final String? semanticLabel;
  final ValueChanged<String> onChanged;
  final ValueChanged<String>? onSubmitted;
  final bool autofocus;
  final HmsSurface surface;

  @override
  Widget build(BuildContext context) {
    final onCard = surface == HmsSurface.card;
    final text = onCard ? AppColors.onCard : AppColors.ink900;
    final hintColor = onCard ? AppColors.onCardMuted : AppColors.ink400;
    OutlineInputBorder border(Color color) => OutlineInputBorder(
      borderRadius: AppRadii.input,
      borderSide: BorderSide(color: color),
    );
    return Semantics(
      label: semanticLabel,
      textField: true,
      child: TextField(
        autofocus: autofocus,
        onChanged: onChanged,
        onSubmitted: onSubmitted,
        textInputAction: TextInputAction.search,
        cursorColor: onCard ? AppColors.onCard : AppColors.brand600,
        style: AppTypography.body(color: text),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: AppTypography.body(color: hintColor),
          filled: true,
          fillColor: onCard ? AppColors.cardRaised : AppColors.surface,
          prefixIcon: Icon(LucideIcons.search, size: 16, color: hintColor),
          prefixIconConstraints: const BoxConstraints(minWidth: 36),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.x3,
            vertical: 12,
          ),
          border: border(
            onCard ? AppColors.onCardLineStrong : AppColors.lineStrong,
          ),
          enabledBorder: border(
            onCard ? AppColors.onCardLineStrong : AppColors.lineStrong,
          ),
          focusedBorder: border(
            onCard ? AppColors.brand300 : AppColors.brand500,
          ),
        ),
      ),
    );
  }
}
