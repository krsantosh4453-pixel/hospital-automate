import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/tone.dart';
import '../../operations/ops_ui.dart';
import '../../patient/ui/patient_ui.dart' show formatDateTime;
import '../data/emergency_models.dart';

/// Emergency pages keep the web's path; a visit opens below it, so the
/// breadcrumb and the router's `Emergency` module check still apply.
abstract final class EmergencyRoutes {
  static const list = '/emergency';

  static String visit(int id) => '$list/$id';
}

/// Permission module of these pages (users/role_permissions.py).
const emergencyModule = 'Emergency';

String erStatusLabel(AppLocalizations t, String status) => switch (status) {
  ErStatus.registered => t.erStatusRegistered,
  ErStatus.triage => t.erStatusTriage,
  ErStatus.waiting => t.statusWaiting,
  ErStatus.underConsultation => t.erStatusUnderConsultation,
  ErStatus.investigations => t.erStatusInvestigations,
  ErStatus.treatment => t.erStatusTreatment,
  ErStatus.observation => t.erStatusObservation,
  ErStatus.admitted => t.erStatusAdmitted,
  ErStatus.discharged => t.erStatusDischarged,
  ErStatus.referred => t.erStatusReferred,
  ErStatus.leftAgainstAdvice => t.erStatusLeftAgainstAdvice,
  ErStatus.expired => t.erStatusExpired,
  _ => status.isEmpty ? '—' : status,
};

String triageLabel(AppLocalizations t, String level) => switch (level) {
  'Critical' => t.triageCritical,
  'Emergency' => t.triageEmergency,
  'Urgent' => t.triageUrgent,
  'Semi-Urgent' => t.triageSemiUrgent,
  'Non-Urgent' => t.triageNonUrgent,
  _ => level.isEmpty ? '—' : level,
};

AlertTone triageTone(String level) => switch (level) {
  'Critical' || 'Emergency' => AlertTone.danger,
  'Urgent' || 'Semi-Urgent' => AlertTone.warning,
  _ => AlertTone.info,
};

AlertTone erStatusTone(String status) => switch (status) {
  ErStatus.discharged || ErStatus.admitted => AlertTone.success,
  ErStatus.expired || ErStatus.leftAgainstAdvice => AlertTone.danger,
  ErStatus.referred => AlertTone.warning,
  _ => AlertTone.info,
};

/// Position of [level] in [triageLevels] (unknown levels last).
int triageRank(String level) {
  final index = triageLevels.indexOf(level);
  return index < 0 ? triageLevels.length : index;
}

/// Most urgent first; within a level, who arrived first.
List<EmergencyVisit> byUrgency(Iterable<EmergencyVisit> visits) {
  final sorted = [...visits];
  sorted.sort((a, b) {
    final rank = triageRank(a.triageLevel).compareTo(triageRank(b.triageLevel));
    if (rank != 0) return rank;
    return (a.arrivalTime ?? DateTime(0)).compareTo(
      b.arrivalTime ?? DateTime(0),
    );
  });
  return List.unmodifiable(sorted);
}

class TriageBadge extends StatelessWidget {
  const TriageBadge({super.key, required this.level});

  final String level;

  @override
  Widget build(BuildContext context) => ToneBadge(
    label: triageLabel(context.l10n, level),
    tone: triageTone(level),
  );
}

class ErStatusBadge extends StatelessWidget {
  const ErStatusBadge({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) => ToneBadge(
    label: erStatusLabel(context.l10n, status),
    tone: erStatusTone(status),
  );
}

/// One visit in a list: patient, visit number, arrival, doctor and badges.
class EmergencyVisitRow extends StatelessWidget {
  const EmergencyVisitRow({super.key, required this.visit, this.onTap});

  final EmergencyVisit visit;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final subtitle = [
      ?visit.visitNumber,
      formatDateTime(t, visit.arrivalTime),
      visit.attendingDoctorName ?? t.erNoDoctorYet,
    ].join(' · ');
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    visit.patientName ?? '—',
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  const SizedBox(height: 2),
                  Text(subtitle, style: AppTypography.small()),
                  const SizedBox(height: AppSpacing.x2),
                  Wrap(
                    spacing: AppSpacing.x2,
                    runSpacing: AppSpacing.x1,
                    children: [
                      TriageBadge(level: visit.triageLevel),
                      ErStatusBadge(status: visit.status),
                    ],
                  ),
                ],
              ),
            ),
            if (onTap != null) const Icon(LucideIcons.chevronRight, size: 18),
          ],
        ),
      ),
    );
  }
}
