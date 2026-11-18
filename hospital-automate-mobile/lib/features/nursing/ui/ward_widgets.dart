import 'package:flutter/material.dart';

import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';

/// A ward-record card: a title, the saved records, and a form below them.
class WardSectionCard extends StatelessWidget {
  const WardSectionCard({
    super.key,
    required this.title,
    required this.icon,
    required this.list,
    this.form,
  });

  final String title;
  final IconData icon;
  final Widget list;
  final Widget? form;

  @override
  Widget build(BuildContext context) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(title: title, icon: icon),
        list,
        if (form != null) ...[
          const Divider(height: 1),
          Padding(padding: const EdgeInsets.all(AppSpacing.x4), child: form),
        ],
      ],
    ),
  );
}

/// One saved record in a ward list: when and who, then what.
class WardRecordRow extends StatelessWidget {
  const WardRecordRow({
    super.key,
    required this.heading,
    required this.body,
    this.trailing,
  });

  final String heading;
  final String body;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => Padding(
    padding: AppSpacing.cardRow,
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(heading, style: AppTypography.caption()),
              const SizedBox(height: 2),
              Text(body, style: AppTypography.small()),
            ],
          ),
        ),
        ?trailing,
      ],
    ),
  );
}
