import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../data/patient_overview.dart';
import '../data/patient_repository.dart';
import '../record_loader.dart';
import 'appointments_screen.dart';
import 'bills_screen.dart';
import 'patient_routes.dart';
import 'patient_ui.dart';
import 'queue_screen.dart';

/// The live part of the patient home: today's token, figures, upcoming
/// visits, recent prescriptions and reports, and quick actions.
class PatientOverviewPanel extends StatefulWidget {
  const PatientOverviewPanel({super.key, required this.repository});

  final PatientRepository repository;

  @override
  State<PatientOverviewPanel> createState() => _PatientOverviewPanelState();
}

class _PatientOverviewPanelState extends State<PatientOverviewPanel> {
  late final RecordLoader<PatientOverview> _loader = RecordLoader(
    () => PatientOverview.load(widget.repository),
  );

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        RecordSection<PatientOverview>(
          loader: _loader,
          skeletons: 2,
          builder: (context, overview) {
            if (overview.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.circleAlert,
                  title: t.somethingWentWrong,
                  description: t.patientDataUnavailable,
                ),
              );
            }
            return _OverviewBody(overview: overview, onRetry: _loader.load);
          },
        ),
        const SizedBox(height: AppSpacing.x6),
        const _QuickActions(),
      ],
    );
  }
}

class _OverviewBody extends StatelessWidget {
  const _OverviewBody({required this.overview, required this.onRetry});

  final PatientOverview overview;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    String? count(int? value) => value?.toString();
    final balance = overview.invoices == null
        ? null
        : outstandingBalance(overview.invoices!);
    final upcoming = overview.upcoming.take(3).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (overview.isPartial) ...[
          HmsAlert(
            tone: AlertTone.warning,
            title: t.somePatientDataUnavailable,
            action: TextButton(onPressed: onRetry, child: Text(t.tryAgain)),
          ),
          const SizedBox(height: AppSpacing.x4),
        ],
        for (final token in overview.activeTokens) ...[
          QueueTokenCard(token: token),
          const SizedBox(height: AppSpacing.x4),
        ],
        StatTileGrid(
          children: [
            StatTile(
              label: t.upcomingAppointments,
              value: overview.appointments == null
                  ? null
                  : '${overview.upcoming.length}',
              icon: LucideIcons.calendarDays,
            ),
            StatTile(
              label: t.pastVisits,
              value: count(overview.pastVisits),
              icon: LucideIcons.history,
              tone: HmsTone.neutral,
            ),
            StatTile(
              label: t.currentPrescriptions,
              value: count(overview.currentPrescriptions),
              icon: LucideIcons.pill,
              tone: HmsTone.accent,
            ),
            StatTile(
              label: t.billsWithBalance,
              value: count(overview.billsWithBalance),
              hint: balance == null ? null : formatRupees(balance),
              icon: LucideIcons.receiptIndianRupee,
              tone: (overview.billsWithBalance ?? 0) > 0
                  ? HmsTone.warning
                  : HmsTone.success,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x6),
        _ListCard(
          title: t.upcomingAppointments,
          icon: LucideIcons.calendarDays,
          path: PatientRoutes.appointments,
          unavailable: overview.appointments == null,
          emptyTitle: t.noUpcomingAppointments,
          children: [for (final a in upcoming) AppointmentRow(appointment: a)],
        ),
        const SizedBox(height: AppSpacing.x6),
        _ListCard(
          title: t.recentPrescriptions,
          icon: LucideIcons.pill,
          path: PatientRoutes.prescriptions,
          unavailable: overview.prescriptions == null,
          emptyTitle: t.noPrescriptionsYet,
          children: [
            for (final p in overview.recentPrescriptions(3))
              _LinkRow(
                title: p.doctorName ?? t.doctor,
                subtitle: [
                  formatDay(t, p.createdAt),
                  t.medicineCount(p.items.length),
                ].join(' · '),
                trailing: StatusBadge(status: p.status),
                path: PatientRoutes.prescriptions,
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x6),
        _ListCard(
          title: t.recentLabReports,
          icon: LucideIcons.flaskConical,
          path: PatientRoutes.labResults,
          unavailable: overview.labTests == null,
          emptyTitle: t.noLabReportsYet,
          children: [
            for (final test in overview.recentLabTests(3))
              _LinkRow(
                title: test.name,
                subtitle: formatDay(t, test.releasedAt ?? test.testDate),
                trailing: StatusBadge(status: test.status),
                path: PatientRoutes.labResults,
              ),
          ],
        ),
        if ((overview.unreadNotifications ?? 0) > 0) ...[
          const SizedBox(height: AppSpacing.x6),
          HmsAlert(
            title: t.unreadNotifications(overview.unreadNotifications!),
            action: TextButton(
              onPressed: () => context.go(PatientRoutes.notifications),
              child: Text(t.viewAll),
            ),
          ),
        ],
      ],
    );
  }
}

class _ListCard extends StatelessWidget {
  const _ListCard({
    required this.title,
    required this.icon,
    required this.path,
    required this.unavailable,
    required this.emptyTitle,
    required this.children,
  });

  final String title;
  final IconData icon;
  final String path;
  final bool unavailable;
  final String emptyTitle;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: title,
            icon: icon,
            trailing: TextButton(
              onPressed: () => context.go(path),
              child: Text(
                t.viewAll,
                style: AppTypography.small(
                  weight: FontWeight.w600,
                  color: AppColors.onCard,
                ),
              ),
            ),
          ),
          if (unavailable)
            HmsEmptyState(compact: true, title: t.notAvailableNow)
          else if (children.isEmpty)
            HmsEmptyState(compact: true, icon: icon, title: emptyTitle)
          else
            HmsDividedColumn(children: children),
        ],
      ),
    );
  }
}

class _LinkRow extends StatelessWidget {
  const _LinkRow({
    required this.title,
    required this.subtitle,
    required this.trailing,
    required this.path,
  });

  final String title;
  final String subtitle;
  final Widget trailing;
  final String path;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: () => context.go(path),
    child: Padding(
      padding: AppSpacing.cardRow,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AppTypography.body(weight: FontWeight.w600)),
                Text(subtitle, style: AppTypography.small()),
              ],
            ),
          ),
          trailing,
        ],
      ),
    ),
  );
}

/// Shortcuts to every patient page (web "Your records" card).
class _QuickActions extends StatelessWidget {
  const _QuickActions();

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final actions = [
      (LucideIcons.calendarPlus, t.bookAppointment, PatientRoutes.book),
      (
        LucideIcons.calendarDays,
        t.patientNavAppointments,
        PatientRoutes.appointments,
      ),
      (LucideIcons.ticket, t.patientNavQueue, PatientRoutes.queue),
      (
        LucideIcons.pill,
        t.patientNavPrescriptions,
        PatientRoutes.prescriptions,
      ),
      (LucideIcons.flaskConical, t.patientNavLab, PatientRoutes.labResults),
      (LucideIcons.receiptIndianRupee, t.patientNavBills, PatientRoutes.bills),
      (LucideIcons.fileText, t.patientNavRecords, PatientRoutes.documents),
      (
        LucideIcons.bell,
        t.patientNavNotifications,
        PatientRoutes.notifications,
      ),
      (LucideIcons.userRound, t.viewProfile, PatientRoutes.profile),
    ];
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.quickActions),
          HmsDividedColumn(
            children: [
              for (final (icon, label, path) in actions)
                InkWell(
                  onTap: () => context.go(path),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      minHeight: AppDimensions.touchTarget,
                    ),
                    child: Padding(
                      padding: AppSpacing.cardRow,
                      child: Row(
                        children: [
                          Icon(icon, size: 18, color: AppColors.onCard),
                          const SizedBox(width: AppSpacing.x3),
                          Expanded(
                            child: Text(
                              label,
                              style: AppTypography.body(
                                weight: FontWeight.w500,
                              ),
                            ),
                          ),
                          const Icon(
                            LucideIcons.chevronRight,
                            size: 16,
                            color: AppColors.onCardMuted,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
