import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/security/session_controller.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/hms_dialog.dart';
import '../../shared/widgets/hms_search_field.dart';
import 'nav_config.dart';

/// QuickJump (Navbar.jsx): search the menu and open a page. Resolves to the
/// chosen item, or null when dismissed.
Future<NavItem?> showQuickJump(BuildContext context, List<NavGroup> groups) {
  return showHmsModal<NavItem>(
    context,
    title: context.l10n.jumpToPage,
    body: _QuickJumpBody(groups: groups),
  );
}

/// Hospital switcher: the hospitals the signed-in person belongs to.
/// Resolves to the chosen hospital id, or null when dismissed.
Future<int?> showHospitalPicker(BuildContext context, SessionState session) {
  return showHmsModal<int>(
    context,
    title: context.l10n.selectHospital,
    body: _HospitalPickerBody(session: session),
  );
}

class _QuickJumpBody extends StatefulWidget {
  const _QuickJumpBody({required this.groups});

  final List<NavGroup> groups;

  @override
  State<_QuickJumpBody> createState() => _QuickJumpBodyState();
}

class _QuickJumpBodyState extends State<_QuickJumpBody> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final q = _query.trim().toLowerCase();
    final entries =
        [
              for (final group in widget.groups)
                for (final item in group.items)
                  (
                    item: item,
                    title: item.label(l10n),
                    group: group.label(l10n),
                  ),
            ]
            .where(
              (e) =>
                  q.isEmpty ||
                  '${e.title} ${e.group}'.toLowerCase().contains(q),
            )
            .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsSearchField(
          hint: l10n.typeModuleName,
          semanticLabel: l10n.searchPages,
          autofocus: true,
          onChanged: (value) => setState(() => _query = value),
          onSubmitted: (_) {
            if (entries.isNotEmpty) {
              Navigator.of(context).pop(entries.first.item);
            }
          },
        ),
        const SizedBox(height: AppSpacing.x3),
        if (entries.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.x6),
            child: Text(
              l10n.noPageMatches(_query),
              textAlign: TextAlign.center,
              style: AppTypography.body(),
            ),
          ),
        for (final entry in entries)
          InkWell(
            onTap: () => Navigator.of(context).pop(entry.item),
            borderRadius: AppRadii.button,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 44),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.x3,
                  vertical: AppSpacing.x2,
                ),
                child: Row(
                  children: [
                    Icon(entry.item.icon, size: 17, color: AppColors.onCard),
                    const SizedBox(width: AppSpacing.x3),
                    Expanded(
                      child: Text(
                        entry.title,
                        style: AppTypography.body(weight: FontWeight.w500),
                      ),
                    ),
                    Text(entry.group, style: AppTypography.caption()),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _HospitalPickerBody extends StatefulWidget {
  const _HospitalPickerBody({required this.session});

  final SessionState session;

  @override
  State<_HospitalPickerBody> createState() => _HospitalPickerBodyState();
}

class _HospitalPickerBodyState extends State<_HospitalPickerBody> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final hospitals = widget.session.hospitals;
    final q = _query.trim().toLowerCase();
    final shown = hospitals
        .where((h) => h.name.toLowerCase().contains(q))
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsSearchField(
          hint: l10n.searchByNameOrCity,
          semanticLabel: l10n.searchHospitals,
          onChanged: (value) => setState(() => _query = value),
        ),
        const SizedBox(height: AppSpacing.x2),
        if (shown.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.x8),
            child: Text(
              hospitals.isEmpty
                  ? l10n.notMemberOfAnyHospital
                  : l10n.noHospitalMatches,
              textAlign: TextAlign.center,
              style: AppTypography.small(),
            ),
          ),
        for (final hospital in shown)
          _HospitalRow(
            hospital: hospital,
            selected: hospital.id == widget.session.activeHospitalId,
          ),
        const SizedBox(height: AppSpacing.x2),
        Text(l10n.switchingHospitalNote, style: AppTypography.caption()),
      ],
    );
  }
}

class _HospitalRow extends StatelessWidget {
  const _HospitalRow({required this.hospital, required this.selected});

  final HospitalContext hospital;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected ? AppColors.cardTintBrand : Colors.transparent,
        borderRadius: AppRadii.button,
        child: InkWell(
          onTap: () => Navigator.of(context).pop(hospital.id),
          borderRadius: AppRadii.button,
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.x2_5),
            child: Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: selected
                        ? AppColors.cardButton
                        : AppColors.onCardFill,
                    borderRadius: const BorderRadius.all(
                      Radius.circular(AppRadii.md),
                    ),
                  ),
                  child: Icon(
                    selected ? LucideIcons.check : LucideIcons.hospital,
                    size: 15,
                    color: AppColors.onCard,
                  ),
                ),
                const SizedBox(width: AppSpacing.x2_5),
                Expanded(
                  child: Text(
                    hospital.name,
                    style: AppTypography.small(weight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
