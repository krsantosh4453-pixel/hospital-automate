import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';

/// Field.jsx + `.hms-input` on a teal surface: a label (with `*` when
/// required), the input in raised teal with white text, and an optional
/// hint or error below.
class HmsTextField extends StatelessWidget {
  const HmsTextField({
    super.key,
    required this.label,
    required this.controller,
    this.required = false,
    this.hint,
    this.placeholder,
    this.error,
    this.obscure = false,
    this.keyboardType,
    this.textInputAction = TextInputAction.next,
    this.autofillHints,
    this.inputFormatters,
    this.onSubmitted,
    this.enabled = true,
    this.autofocus = false,
    this.maxLength,
    this.prefixText,
  });

  final String label;
  final TextEditingController controller;
  final bool required;
  final String? hint;
  final String? placeholder;
  final String? error;
  final bool obscure;
  final TextInputType? keyboardType;
  final TextInputAction textInputAction;
  final Iterable<String>? autofillHints;
  final List<TextInputFormatter>? inputFormatters;
  final ValueChanged<String>? onSubmitted;
  final bool enabled;
  final bool autofocus;
  final int? maxLength;
  final String? prefixText;

  @override
  Widget build(BuildContext context) {
    OutlineInputBorder border(Color color) => OutlineInputBorder(
      borderRadius: AppRadii.input,
      borderSide: BorderSide(color: color),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // The visible label is excluded from semantics: the field below
        // carries it, so a screen reader announces "Password, text field".
        ExcludeSemantics(
          child: Text(
            required ? '$label *' : label,
            style: AppTypography.small(weight: FontWeight.w500),
          ),
        ),
        const SizedBox(height: AppSpacing.x1_5),
        Semantics(
          label: label,
          textField: true,
          child: TextField(
            controller: controller,
            enabled: enabled,
            autofocus: autofocus,
            obscureText: obscure,
            enableSuggestions: !obscure,
            autocorrect: false,
            keyboardType: keyboardType,
            textInputAction: textInputAction,
            autofillHints: autofillHints,
            inputFormatters: inputFormatters,
            onSubmitted: onSubmitted,
            maxLength: maxLength,
            cursorColor: AppColors.onCard,
            style: AppTypography.body(),
            decoration: InputDecoration(
              hintText: placeholder,
              hintStyle: AppTypography.body(color: AppColors.onCardMuted),
              prefixText: prefixText,
              prefixStyle: AppTypography.body(),
              counterText: '',
              filled: true,
              fillColor: AppColors.cardRaised,
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.x3,
                vertical: 13,
              ),
              border: border(AppColors.onCardLineStrong),
              enabledBorder: border(
                error == null
                    ? AppColors.onCardLineStrong
                    : const Color(0xFFF5BCB6),
              ),
              focusedBorder: border(AppColors.brand300),
              disabledBorder: border(AppColors.onCardLine),
            ),
          ),
        ),
        if (error != null || hint != null) ...[
          const SizedBox(height: AppSpacing.x1),
          Text(
            error ?? hint!,
            style: AppTypography.caption(
              color: error == null ? AppColors.onCard : const Color(0xFFFBDEDB),
            ),
          ),
        ],
      ],
    );
  }
}
