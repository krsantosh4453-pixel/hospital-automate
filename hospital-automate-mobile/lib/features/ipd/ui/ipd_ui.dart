import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/tone.dart';
import '../../operations/ops_ui.dart';
import '../../patient/ui/patient_ui.dart' show formatDay;
import '../data/ipd_models.dart';

/// IPD pages keep the web's path; a stay opens below it.
abstract final class IpdRoutes {
  static const list = '/ipd';

  static String admission(int id) => '$list/$id';
}

/// Permission module of these pages (users/role_permissions.py).
const ipdModule = 'IPD';

String admissionStatusLabel(AppLocalizations t, String status) =>
    switch (status) {
      AdmissionStatus.admitted => t.ipdAdmitted,
      AdmissionStatus.dischargeInitiated => t.ipdDischargeInitiated,
      AdmissionStatus.discharged => t.ipdDischarged,
      AdmissionStatus.transferred => t.ipdTransferred,
      AdmissionStatus.cancelled => t.statusCancelled,
      _ => status.isEmpty ? '—' : status,
    };

AlertTone admissionTone(String status) => switch (status) {
  AdmissionStatus.dischargeInitiated => AlertTone.warning,
  AdmissionStatus.discharged => AlertTone.success,
  AdmissionStatus.cancelled => AlertTone.danger,
  _ => AlertTone.info,
};

String bedStatusLabel(AppLocalizations t, String status) => switch (status) {
  BedStatus.available => t.bedAvailable,
  BedStatus.occupied => t.bedOccupied,
  BedStatus.reserved => t.bedReserved,
  BedStatus.cleaning => t.bedCleaning,
  BedStatus.maintenance => t.bedMaintenance,
  _ => status.isEmpty ? '—' : status,
};

AlertTone bedTone(String status) => switch (status) {
  BedStatus.available => AlertTone.success,
  BedStatus.occupied => AlertTone.info,
  BedStatus.reserved => AlertTone.warning,
  _ => AlertTone.danger,
};

/// A checklist item in the reader's language, by its server field name.
String checklistLabel(AppLocalizations t, ChecklistItem item) =>
    switch (item.field) {
      'medications_reconciled' => t.ipdCheckMedications,
      'patient_counselled' => t.ipdCheckCounselled,
      'follow_up_arranged' => t.ipdCheckFollowUp,
      'documents_handed_over' => t.ipdCheckDocuments,
      _ => item.label,
    };

/// Why a discharge cannot be completed yet, from the readiness fields. Falls
/// back to the server's own sentences when none of the known reasons apply.
List<String> dischargeBlockers(
  AppLocalizations t,
  IpdAdmission admission,
  DischargeReadiness readiness,
) {
  if (readiness.ready) return const [];
  final reasons = [
    if (!admission.isDischarging) t.ipdNotStarted,
    if (!readiness.hasPlan) t.ipdNoPlan,
    for (final item in readiness.checklist)
      if (!item.done) checklistLabel(t, item),
    if (!readiness.summaryFinalized) t.ipdSummaryNotFinalized,
    if (readiness.finalBill == null) t.ipdNoFinalBill,
    if (readiness.finalBill != null && !readiness.billPaid) t.ipdBillDue,
  ];
  return List.unmodifiable(
    reasons.isEmpty ? readiness.serverBlockers : reasons,
  );
}

class AdmissionBadge extends StatelessWidget {
  const AdmissionBadge({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) => ToneBadge(
    label: admissionStatusLabel(context.l10n, status),
    tone: admissionTone(status),
  );
}

class BedBadge extends StatelessWidget {
  const BedBadge({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) => ToneBadge(
    label: bedStatusLabel(context.l10n, status),
    tone: bedTone(status),
  );
}

/// The bed line of a stay: the bed held now, the bed released at
/// discharge, or "Waiting for a bed" (BUG-10).
String bedLabel(AppLocalizations t, IpdAdmission admission) {
  final bed = admission.currentBed?.place.label;
  if (bed != null && bed.isNotEmpty) return bed;
  final released = admission.releasedBed;
  if (released != null) {
    return t.ipdBedReleased(
      released.place.label,
      formatDay(t, released.releasedAt),
    );
  }
  return t.ipdAwaitingBed;
}

/// One stay in a list: patient, bed, admission day, doctor and status.
class AdmissionRow extends StatelessWidget {
  const AdmissionRow({super.key, required this.admission, this.onTap});

  final IpdAdmission admission;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final subtitle = [
      bedLabel(t, admission),
      formatDay(t, admission.admissionDate),
      ?admission.admittingDoctorName,
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
                    admission.patientName ?? '—',
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  const SizedBox(height: 2),
                  Text(subtitle, style: AppTypography.small()),
                  const SizedBox(height: AppSpacing.x2),
                  AdmissionBadge(status: admission.status),
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
