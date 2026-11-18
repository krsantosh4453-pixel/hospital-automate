import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/ui/consultation_sections.dart';
import '../data/ai_models.dart';
import 'ai_ui.dart';

/// What the draft card asks its screen to do. Each returns when the server
/// has answered; the screen reloads and reports errors.
class DraftActions {
  const DraftActions({
    required this.generate,
    required this.saveSection,
    required this.approve,
    required this.reject,
    required this.regenerate,
  });

  final Future<void> Function() generate;
  final Future<void> Function(DraftSection section, String text) saveSection;
  final Future<void> Function() approve;
  final Future<void> Function() reject;
  final Future<void> Function() regenerate;
}

/// Steps 3 and 4: the AI draft, section by section, with the doctor's edits,
/// then explicit approval. A section the consultation did not cover is shown
/// as not recorded, never filled in.
class ScribeDraftCard extends StatefulWidget {
  const ScribeDraftCard({
    super.key,
    required this.draft,
    required this.canWrite,
    required this.transcriptReady,
    required this.busy,
    required this.actions,
  });

  final ScribeDraft? draft;
  final bool canWrite;
  final bool transcriptReady;
  final bool busy;
  final DraftActions actions;

  @override
  State<ScribeDraftCard> createState() => _ScribeDraftCardState();
}

class _ScribeDraftCardState extends State<ScribeDraftCard> {
  /// The section editor's text. Owned here, not by the sheet: the sheet
  /// still uses it while it slides away.
  final TextEditingController _editor = TextEditingController();

  bool get canWrite => widget.canWrite;
  bool get transcriptReady => widget.transcriptReady;
  bool get busy => widget.busy;
  DraftActions get actions => widget.actions;

  @override
  void dispose() {
    _editor.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final draft = widget.draft;
    return HmsCard(
      key: const Key('scribe-draft'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.aiStepDraft,
            icon: LucideIcons.fileText,
            description:
                draft == null || draft.awaitingGeneration || draft.generating
                ? null
                : t.aiDraftPending(draft.version),
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: switch (draft) {
              final d? when d.generating => Row(
                key: const Key('draft-working'),
                children: [
                  const SizedBox.square(
                    dimension: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: AppSpacing.x3),
                  Expanded(
                    child: Text(t.aiWorking, style: AppTypography.small()),
                  ),
                ],
              ),
              final d? when !d.awaitingGeneration => _review(context, t, d),
              _ => _generatePrompt(t, draft),
            },
          ),
        ],
      ),
    );
  }

  Widget _generatePrompt(AppLocalizations t, ScribeDraft? draft) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      if (draft?.lastAttemptFailed ?? false) ...[
        HmsAlert(
          key: const Key('draft-failed'),
          tone: AlertTone.danger,
          title: t.aiDraftFailed,
        ),
        const SizedBox(height: AppSpacing.x3),
      ],
      Text(t.aiNoDraftYet, style: AppTypography.small()),
      if (canWrite && draft != null && transcriptReady) ...[
        const SizedBox(height: AppSpacing.x3),
        HmsButton(
          key: const Key('generate-draft'),
          label: t.aiGenerateDraft,
          icon: LucideIcons.sparkles,
          surface: HmsSurface.card,
          loading: busy,
          onPressed: busy ? null : actions.generate,
        ),
      ],
    ],
  );

  Widget _review(BuildContext context, AppLocalizations t, ScribeDraft draft) {
    final editable = canWrite && draft.canEdit;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (draft.status == DraftStatus.approved)
          HmsAlert(tone: AlertTone.success, title: t.aiDraftApproved)
        else if (draft.status == DraftStatus.rejected)
          HmsAlert(title: t.aiDraftRejected)
        else if (draft.fromMock)
          HmsAlert(tone: AlertTone.warning, title: t.aiMockDraftWarning),
        for (final section in DraftSection.values)
          _SectionView(
            section: section,
            lines: draft.lines(section),
            onEdit: editable && !busy
                ? () => _edit(context, t, draft, section)
                : null,
          ),
        if (canWrite && draft.canApprove) ...[
          const SizedBox(height: AppSpacing.x2),
          Text(t.aiStepApprove, style: AppTypography.cardTitle()),
          const SizedBox(height: AppSpacing.x2),
          Wrap(
            spacing: AppSpacing.x2,
            runSpacing: AppSpacing.x2,
            children: [
              HmsButton(
                key: const Key('approve-draft'),
                label: t.aiApprove,
                icon: LucideIcons.circleCheck,
                surface: HmsSurface.card,
                loading: busy,
                onPressed: busy ? null : () => _confirmApprove(context, t),
              ),
              HmsButton(
                key: const Key('reject-draft'),
                label: t.aiReject,
                variant: HmsButtonVariant.secondary,
                surface: HmsSurface.card,
                onPressed: busy ? null : () => _confirmReject(context, t),
              ),
              HmsButton(
                key: const Key('regenerate-draft'),
                label: t.aiRegenerate,
                variant: HmsButtonVariant.secondary,
                surface: HmsSurface.card,
                onPressed: busy ? null : actions.regenerate,
              ),
            ],
          ),
        ],
      ],
    );
  }

  Future<void> _confirmApprove(BuildContext context, AppLocalizations t) async {
    final ok = await showHmsConfirm(
      context,
      title: t.aiApproveTitle,
      message: t.aiApproveBody,
      confirmLabel: t.aiApprove,
    );
    if (ok) await actions.approve();
  }

  Future<void> _confirmReject(BuildContext context, AppLocalizations t) async {
    final ok = await showHmsConfirm(
      context,
      title: t.aiRejectTitle,
      message: t.aiRejectBody,
      confirmLabel: t.aiReject,
      destructive: true,
    );
    if (ok) await actions.reject();
  }

  Future<void> _edit(
    BuildContext context,
    AppLocalizations t,
    ScribeDraft draft,
    DraftSection section,
  ) async {
    final controller = _editor..text = draft.lines(section).join('\n');
    final text = await showHmsModal<String>(
      context,
      title: sectionLabel(t, section),
      description: t.aiEditHint,
      body: ClinicalField(
        key: const Key('section-editor'),
        label: sectionLabel(t, section),
        controller: controller,
        maxLines: 6,
      ),
      actions: (dialogContext) => [
        HmsButton(
          label: t.cancel,
          variant: HmsButtonVariant.secondary,
          onPressed: () => Navigator.of(dialogContext).pop(),
        ),
        HmsButton(
          key: const Key('save-section'),
          label: t.aiSaveSection,
          onPressed: () => Navigator.of(dialogContext).pop(controller.text),
        ),
      ],
    );
    if (text != null) await actions.saveSection(section, text);
  }
}

class _SectionView extends StatelessWidget {
  const _SectionView({
    required this.section,
    required this.lines,
    required this.onEdit,
  });

  final DraftSection section;
  final List<String> lines;
  final VoidCallback? onEdit;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.x3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              key: Key('section-${section.key}'),
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  sectionLabel(t, section),
                  style: AppTypography.small(weight: FontWeight.w600),
                ),
                if (lines.isEmpty)
                  Text(
                    t.aiNotRecorded,
                    style: AppTypography.body(
                      color: AppColors.ink500,
                    ).copyWith(fontStyle: FontStyle.italic),
                  )
                else
                  for (final line in lines)
                    Text('• $line', style: AppTypography.body()),
              ],
            ),
          ),
          if (onEdit != null)
            TextButton(
              key: Key('edit-${section.key}'),
              onPressed: onEdit,
              child: Text(t.aiEditSection),
            ),
        ],
      ),
    );
  }
}
