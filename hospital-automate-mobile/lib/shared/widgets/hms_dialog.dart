import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import 'hms_button.dart';

/// Modal.jsx: a teal panel that rises from the bottom on phones and is
/// centred on wider screens, with a title row, body and footer actions.
Future<T?> showHmsModal<T>(
  BuildContext context, {
  required String title,
  String? description,
  required Widget body,
  List<Widget> Function(BuildContext context)? actions,
}) {
  final sheet = MediaQuery.sizeOf(context).width < AppBreakpoints.sm;
  Widget panel(BuildContext dialogContext) => _ModalPanel(
    title: title,
    description: description,
    body: body,
    actions: actions?.call(dialogContext) ?? const [],
  );
  if (sheet) {
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: true,
      showDragHandle: false,
      useSafeArea: true,
      builder: panel,
    );
  }
  return showDialog<T>(
    context: context,
    builder: (dialogContext) => Dialog(
      insetPadding: const EdgeInsets.all(AppSpacing.x4),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 512),
        child: panel(dialogContext),
      ),
    ),
  );
}

/// ConfirmDialog: asks before an action. Resolves to true only on confirm.
Future<bool> showHmsConfirm(
  BuildContext context, {
  required String title,
  required String message,
  required String confirmLabel,
  bool destructive = false,
}) async {
  final confirmed = await showHmsModal<bool>(
    context,
    title: title,
    body: Text(message, style: AppTypography.body().copyWith(height: 24 / 14)),
    actions: (dialogContext) => [
      HmsButton(
        label: dialogContext.l10n.cancel,
        variant: HmsButtonVariant.secondary,
        surface: HmsSurface.card,
        onPressed: () => Navigator.of(dialogContext).pop(false),
      ),
      HmsButton(
        label: confirmLabel,
        variant: destructive
            ? HmsButtonVariant.danger
            : HmsButtonVariant.primary,
        surface: HmsSurface.card,
        onPressed: () => Navigator.of(dialogContext).pop(true),
      ),
    ],
  );
  return confirmed ?? false;
}

class _ModalPanel extends StatelessWidget {
  const _ModalPanel({
    required this.title,
    this.description,
    required this.body,
    required this.actions,
  });

  final String title;
  final String? description;
  final Widget body;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.x5,
            AppSpacing.x4,
            AppSpacing.x3,
            AppSpacing.x4,
          ),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: AppColors.onCardLine)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Semantics(
                      header: true,
                      child: Text(
                        title,
                        style: AppTypography.style(
                          16,
                          weight: FontWeight.w600,
                          height: 24,
                          color: AppColors.onCard,
                        ),
                      ),
                    ),
                    if (description != null) ...[
                      const SizedBox(height: 2),
                      Text(description!, style: AppTypography.small()),
                    ],
                  ],
                ),
              ),
              IconButton(
                onPressed: () => Navigator.of(context).maybePop(),
                tooltip: context.l10n.close,
                icon: const Icon(
                  LucideIcons.x,
                  size: 20,
                  color: AppColors.onCard,
                ),
              ),
            ],
          ),
        ),
        Flexible(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.x5,
              vertical: AppSpacing.x4,
            ),
            child: body,
          ),
        ),
        if (actions.isNotEmpty)
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.x5,
              vertical: AppSpacing.x3,
            ),
            decoration: const BoxDecoration(
              color: Color(0x99135F69), // bg-ink-50/60 on teal
              border: Border(top: BorderSide(color: AppColors.onCardLine)),
            ),
            child: SafeArea(
              top: false,
              child: Wrap(
                alignment: WrapAlignment.end,
                spacing: AppSpacing.x2,
                runSpacing: AppSpacing.x2,
                children: actions,
              ),
            ),
          ),
      ],
    );
  }
}
