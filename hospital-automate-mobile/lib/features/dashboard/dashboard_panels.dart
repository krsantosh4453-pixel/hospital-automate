import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/avatar.dart';
import '../../shared/widgets/hms_card.dart';
import '../../shared/widgets/states.dart';
import '../../shared/widgets/stat_tile.dart';
import '../../shared/widgets/tone.dart';
import 'dashboard_stats.dart';
import 'role_homes.dart';

/// Indian digit grouping, as the web's `Intl.NumberFormat("en-IN")`.
final indianNumber = NumberFormat.decimalPattern('en_IN');
final indianRupees = NumberFormat.currency(
  locale: 'en_IN',
  symbol: '₹',
  decimalDigits: 0,
);

/// Opens a route; panels never navigate by themselves.
typedef OpenPath = void Function(String path);

/// One part of a [SplitBar].
@immutable
class SplitPart {
  const SplitPart(this.label, this.value, this.color);

  final String label;
  final int value;
  final Color color;
}

/// SplitBar (Home.jsx): one bar split into labelled parts, from real counts only.
class SplitBar extends StatelessWidget {
  const SplitBar({super.key, required this.label, required this.parts});

  final String label;
  final List<SplitPart> parts;

  @override
  Widget build(BuildContext context) {
    final sum = parts.fold<int>(0, (total, p) => total + p.value);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          label:
              '$label: ${parts.map((p) => '${p.label} ${p.value}').join(', ')}',
          child: ClipRRect(
            borderRadius: AppRadii.pill,
            child: SizedBox(
              height: 10,
              child: ColoredBox(
                color: AppColors.onCardFill,
                child: sum == 0
                    ? const SizedBox.expand()
                    : Row(
                        children: [
                          for (final p in parts)
                            if (p.value > 0)
                              Expanded(
                                flex: p.value,
                                child: ColoredBox(color: p.color),
                              ),
                        ],
                      ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.x3),
        ExcludeSemantics(
          child: Wrap(
            spacing: AppSpacing.x5,
            runSpacing: AppSpacing.x1_5,
            children: [
              for (final p in parts)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: p.color,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.x2),
                    Text(p.label, style: AppTypography.small()),
                    const SizedBox(width: AppSpacing.x2),
                    Text(
                      indianNumber.format(p.value),
                      style: AppTypography.style(
                        13,
                        weight: FontWeight.w600,
                        height: 20,
                        color: AppColors.onCard,
                        tabularFigures: true,
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }
}

/// "Open ›" link in a card row.
class _OpenLink extends StatelessWidget {
  const _OpenLink({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      link: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: AppRadii.button,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.x1,
            vertical: AppSpacing.x1_5,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label, style: AppTypography.small(weight: FontWeight.w500)),
              const Icon(
                LucideIcons.chevronRight,
                size: 14,
                color: AppColors.onCard,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// "Today's patient flow": queue, appointments and laboratory split bars.
class PatientFlowCard extends StatelessWidget {
  const PatientFlowCard({
    super.key,
    required this.stats,
    required this.canView,
    required this.open,
  });

  final DashboardStats stats;
  final bool Function(String module) canView;
  final OpenPath open;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final s = stats;
    Widget row(IconData icon, String title, String? path, Widget bar) =>
        Padding(
          padding: AppSpacing.cardHeader,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Icon(icon, size: 16, color: AppColors.onCard),
                  const SizedBox(width: AppSpacing.x2),
                  Expanded(
                    child: Text(
                      title,
                      style: AppTypography.body(weight: FontWeight.w600),
                    ),
                  ),
                  if (path != null)
                    _OpenLink(label: t.open, onTap: () => open(path)),
                ],
              ),
              const SizedBox(height: AppSpacing.x3),
              bar,
            ],
          ),
        );
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.todaysPatientFlow, description: t.liveCounts),
          HmsDividedColumn(
            children: [
              row(
                LucideIcons.listOrdered,
                t.deptQueue,
                canView('Queue') ? '/queue' : null,
                SplitBar(
                  label: t.queueStatus,
                  parts: [
                    SplitPart(
                      t.statusWaiting,
                      s.count('queue', 'waiting'),
                      AppColors.amber500,
                    ),
                    SplitPart(
                      t.statusInConsultation,
                      s.count('queue', 'in_consultation'),
                      AppColors.brand500,
                    ),
                    SplitPart(
                      t.statusCompleted,
                      s.count('queue', 'completed'),
                      AppColors.green500,
                    ),
                  ],
                ),
              ),
              row(
                LucideIcons.calendarDays,
                t.navAppointments,
                canView('Appointments') ? '/appointments' : null,
                SplitBar(
                  label: t.appointmentStatus,
                  parts: [
                    SplitPart(
                      t.statusPending,
                      s.count('appointments', 'pending'),
                      AppColors.amber500,
                    ),
                    SplitPart(
                      t.statusCompleted,
                      s.count('appointments', 'completed'),
                      AppColors.green500,
                    ),
                  ],
                ),
              ),
              if (canView('Laboratory'))
                row(
                  LucideIcons.flaskConical,
                  t.navLaboratory,
                  '/laboratory',
                  SplitBar(
                    label: t.labTestStatus,
                    parts: [
                      SplitPart(
                        t.statusPending,
                        s.count('laboratory', 'pending'),
                        AppColors.amber500,
                      ),
                      SplitPart(
                        t.statusCompleted,
                        s.count('laboratory', 'completed'),
                        AppColors.green500,
                      ),
                      SplitPart(
                        t.statusUrgent,
                        s.count('laboratory', 'urgent'),
                        AppColors.red500,
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// "Recently registered patients": the six newest, as the web shows.
class RecentPatientsCard extends StatelessWidget {
  const RecentPatientsCard({
    super.key,
    required this.patients,
    required this.loading,
    required this.onViewAll,
  });

  final List<RecentPatient> patients;
  final bool loading;
  final VoidCallback? onViewAll;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final dates = DateFormat.yMd(t.localeName);
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.recentlyRegistered,
            trailing: onViewAll == null
                ? null
                : _OpenLink(label: t.viewAll, onTap: onViewAll!),
          ),
          if (patients.isEmpty)
            HmsEmptyState(
              compact: true,
              icon: LucideIcons.usersRound,
              title: loading ? t.loading : t.noPatientsYet,
            )
          else
            HmsDividedColumn(
              children: [
                for (final p in patients.take(6))
                  Padding(
                    padding: AppSpacing.cardRow,
                    child: Row(
                      children: [
                        HmsAvatar(name: p.name, size: AvatarSize.small),
                        const SizedBox(width: AppSpacing.x3),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                p.name,
                                overflow: TextOverflow.ellipsis,
                                style: AppTypography.body(
                                  weight: FontWeight.w500,
                                ),
                              ),
                              Text(
                                [
                                  p.patientId ?? 'ID ${p.id}',
                                  if (p.gender != null) p.gender!,
                                  if (p.age != null) t.ageYears('${p.age}'),
                                ].join(' · '),
                                style: AppTypography.caption().copyWith(
                                  fontFeatures: AppTypography.tabular,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (p.createdAt != null)
                          Text(
                            dates.format(p.createdAt!.toLocal()),
                            style: AppTypography.caption(),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

/// One "Needs attention" row.
@immutable
class AttentionItem {
  const AttentionItem({
    required this.tone,
    required this.icon,
    required this.path,
    required this.text,
  });

  final HmsTone tone;
  final IconData icon;
  final String path;
  final String text;
}

class AttentionCard extends StatelessWidget {
  const AttentionCard({
    super.key,
    required this.items,
    required this.checking,
    required this.open,
  });

  final List<AttentionItem> items;
  final bool checking;
  final OpenPath open;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.needsAttention),
          if (items.isEmpty)
            HmsEmptyState(
              compact: true,
              icon: LucideIcons.shieldCheck,
              title: checking ? t.checking : t.nothingNeedsAttention,
              description: checking ? null : t.nothingNeedsAttentionText,
            )
          else
            HmsDividedColumn(
              children: [
                for (final item in items)
                  InkWell(
                    onTap: () => open(item.path),
                    child: Padding(
                      padding: AppSpacing.cardRow,
                      child: Row(
                        children: [
                          HmsIconTile(
                            icon: item.icon,
                            fill: item.tone.cardTint,
                            size: 32,
                            iconSize: 16,
                          ),
                          const SizedBox(width: AppSpacing.x3),
                          Expanded(
                            child: Text(item.text, style: AppTypography.body()),
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
              ],
            ),
        ],
      ),
    );
  }
}

class QuickActionsCard extends StatelessWidget {
  const QuickActionsCard({
    super.key,
    required this.actions,
    required this.open,
  });

  final List<QuickAction> actions;
  final OpenPath open;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.quickActions),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x3),
            child: ResponsiveGrid(
              columns: 2,
              gap: AppSpacing.x2,
              children: [
                for (final action in actions)
                  Semantics(
                    button: true,
                    label: action.label(t),
                    excludeSemantics: true,
                    child: InkWell(
                      onTap: () => open(action.path),
                      borderRadius: AppRadii.card,
                      hoverColor: AppColors.onCardHover,
                      child: Padding(
                        padding: const EdgeInsets.all(AppSpacing.x3),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              action.icon,
                              size: 18,
                              color: AppColors.onCard,
                            ),
                            const SizedBox(height: AppSpacing.x2),
                            Text(
                              action.label(t),
                              style: AppTypography.small(
                                weight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// "Operations": admissions, emergency visits and money, per permission.
class OperationsCard extends StatelessWidget {
  const OperationsCard({super.key, required this.stats, required this.canView});

  final DashboardStats stats;
  final bool Function(String module) canView;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final s = stats;
    final revenue = s.money('billing', 'today_revenue');
    Widget row(String label, String value) => Padding(
      padding: AppSpacing.cardRow,
      child: Row(
        children: [
          Expanded(child: Text(label, style: AppTypography.body())),
          Text(
            value,
            style: AppTypography.body(weight: FontWeight.w600)
                .copyWith(fontFeatures: AppTypography.tabular),
          ),
        ],
      ),
    );
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.operations),
          HmsDividedColumn(
            children: [
              if (canView('IPD'))
                row(
                  t.tileCurrentAdmissions,
                  indianNumber.format(s.count('admissions', 'current')),
                ),
              if (canView('Emergency'))
                row(
                  t.emergencyVisitsToday,
                  indianNumber.format(s.count('emergency', 'today')),
                ),
              if (canView('Billing')) ...[
                // The server withholds money from roles outside its revenue roles.
                row(
                  t.tileCollectedToday,
                  revenue == null ? '—' : indianRupees.format(revenue),
                ),
                row(
                  t.invoicesPaidTotal,
                  '${indianNumber.format(s.count('billing', 'paid'))} / ${indianNumber.format(s.count('billing', 'total_invoices'))}',
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

/// The stat tile for [tile], from real figures; `—` until they load.
StatTile dashboardTile(
  AppLocalizations t,
  DashboardTile tile,
  DashboardStats? s,
) {
  String? n(int Function(DashboardStats s) read) =>
      s == null ? null : indianNumber.format(read(s));
  return switch (tile) {
    DashboardTile.patients => StatTile(
      icon: LucideIcons.usersRound,
      label: t.tilePatientsToday,
      value: n((s) => s.count('patients', 'today')),
      hint: s == null
          ? null
          : t.registeredInTotal(
              indianNumber.format(s.count('patients', 'total')),
            ),
    ),
    DashboardTile.appointments => StatTile(
      icon: LucideIcons.calendarDays,
      tone: HmsTone.accent,
      label: t.tileAppointmentsToday,
      value: n((s) => s.count('appointments', 'today')),
      hint: s == null
          ? null
          : t.countPending(
              indianNumber.format(s.count('appointments', 'pending')),
            ),
    ),
    DashboardTile.queue => StatTile(
      icon: LucideIcons.listOrdered,
      tone: HmsTone.warning,
      label: t.tileWaitingInQueue,
      value: n((s) => s.count('queue', 'waiting')),
      hint: s != null && s.count('queue', 'current_token') > 0
          ? t.nowServingToken('${s.count('queue', 'current_token')}')
          : t.noTokenServed,
    ),
    DashboardTile.beds => StatTile(
      icon: LucideIcons.bedDouble,
      tone: HmsTone.success,
      label: t.tileBedsAvailable,
      value: n((s) => s.bedsAvailable),
      hint: s == null
          ? null
          : t.bedsOccupiedOf(
              indianNumber.format(s.bedsOccupied),
              indianNumber.format(s.bedsTotal),
            ),
    ),
    DashboardTile.admissions => StatTile(
      icon: LucideIcons.bedDouble,
      label: t.tileCurrentAdmissions,
      value: n((s) => s.count('admissions', 'current')),
    ),
    DashboardTile.labPending => StatTile(
      icon: LucideIcons.flaskConical,
      tone: HmsTone.warning,
      label: t.tileLabPending,
      value: n((s) => s.count('laboratory', 'pending')),
    ),
    DashboardTile.labUrgent => StatTile(
      icon: LucideIcons.flaskConical,
      tone: HmsTone.warning,
      label: t.tileLabUrgent,
      value: n((s) => s.count('laboratory', 'urgent')),
    ),
    DashboardTile.labCompleted => StatTile(
      icon: LucideIcons.clipboardCheck,
      tone: HmsTone.success,
      label: t.tileLabCompleted,
      value: n((s) => s.count('laboratory', 'completed')),
    ),
    DashboardTile.billingPending => StatTile(
      icon: LucideIcons.receiptIndianRupee,
      tone: HmsTone.warning,
      label: t.tileBillingPending,
      value: n((s) => s.count('billing', 'pending')),
    ),
    DashboardTile.revenueToday => StatTile(
      icon: LucideIcons.receiptIndianRupee,
      tone: HmsTone.success,
      label: t.tileCollectedToday,
      value: s == null
          ? null
          : (s.money('billing', 'today_revenue') == null
                ? null
                : indianRupees.format(s.money('billing', 'today_revenue'))),
    ),
  };
}
