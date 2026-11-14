import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/security/session_controller.dart';
import '../../core/theme/app_spacing.dart';
import '../../shared/widgets/hms_button.dart';
import '../../shared/widgets/hms_card.dart';
import '../../shared/widgets/page_header.dart';
import '../../shared/widgets/stat_tile.dart';
import '../../shared/widgets/states.dart';
import '../../shared/widgets/tone.dart';
import 'dashboard_controller.dart';
import 'dashboard_panels.dart';
import 'dashboard_repository.dart';
import 'dashboard_stats.dart';
import 'role_homes.dart';

/// The staff home page (pages/Home.jsx): greeting, today's figures, patient
/// flow, recent registrations, items needing attention, quick actions and
/// operations. Every figure comes from `/home/stats/detail/`.
class StaffDashboard extends StatefulWidget {
  const StaffDashboard({
    super.key,
    required this.session,
    required this.repository,
    this.now,
  });

  final SessionState session;
  final DashboardRepository repository;

  /// Clock for the greeting and date; tests pass a fixed one.
  final DateTime Function()? now;

  @override
  State<StaffDashboard> createState() => _StaffDashboardState();
}

class _StaffDashboardState extends State<StaffDashboard> {
  late final DashboardController _controller = DashboardController(
    widget.repository,
  );

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant StaffDashboard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.session.activeHospitalId != widget.session.activeHospitalId) {
      _load();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _load() {
    final hospital = widget.session.activeHospitalId;
    if (hospital != null) _controller.load(hospital);
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final session = widget.session;
    final hospital = session.activeHospital;
    if (hospital == null) {
      return HmsCard(
        child: HmsEmptyState(
          icon: LucideIcons.hospital,
          title: t.welcome,
          // No active membership at all: only an administrator can fix that.
          description: session.hospitals.isEmpty
              ? t.noHospitalAccess
              : t.selectHospitalForDashboard,
        ),
      );
    }
    return ListenableBuilder(
      listenable: _controller,
      builder: (context, _) => _DashboardLayout(
        session: session,
        hospitalName: hospital.name,
        stats: _controller.stats,
        loading: _controller.loading,
        error: _controller.error,
        onRetry: _load,
        now: (widget.now ?? DateTime.now)(),
      ),
    );
  }
}

class _DashboardLayout extends StatelessWidget {
  const _DashboardLayout({
    required this.session,
    required this.hospitalName,
    required this.stats,
    required this.loading,
    required this.error,
    required this.onRetry,
    required this.now,
  });

  final SessionState session;
  final String hospitalName;
  final DashboardStats? stats;
  final bool loading;
  final Object? error;
  final VoidCallback onRetry;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final role = session.activeRole;
    final roleHome = roleHomeFor(role);
    final canView = session.canView;
    void open(String path) => context.go(path);

    final tiles = roleHome?.tiles ?? fullDashboardTiles;
    final showFlow = roleHome == null || roleHome.showFlow;
    final showRecent = roleHome == null || roleHome.showRecentPatients;
    final actions = (roleHome?.actions ?? allQuickActions)
        .where((a) => canView(a.module))
        .toList();
    final s = stats;

    final main = [
      if (showFlow && s != null)
        PatientFlowCard(stats: s, canView: canView, open: open),
      if (showRecent)
        RecentPatientsCard(
          patients: s?.recentPatients ?? const [],
          loading: loading,
          onViewAll: canView('Patients') ? () => open('/patients') : null,
        ),
    ];
    final side = [
      AttentionCard(
        items: s == null ? const [] : _attention(t, s, canView),
        checking: loading && s == null,
        open: open,
      ),
      if (actions.isNotEmpty) QuickActionsCard(actions: actions, open: open),
      if (roleHome == null &&
          (canView('Billing') || canView('IPD')) &&
          s != null)
        OperationsCard(stats: s, canView: canView),
    ];
    final twoColumns = MediaQuery.sizeOf(context).width >= AppBreakpoints.xl;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: _title(t, session.user?.firstName),
          description: [
            if (roleHome != null) roleHome.title(t),
            DateFormat('EEEE, d MMMM', t.localeName).format(now),
            hospitalName,
            if (role != null) roleLabel(t, role),
          ].join(' · '),
          actions: [
            if (roleHome == null && canView('Appointments'))
              HmsButton(
                label: t.actionNewAppointment,
                icon: LucideIcons.calendarPlus,
                variant: HmsButtonVariant.secondary,
                onPressed: () => open('/appointments'),
              ),
            if (roleHome == null && canView('Patients'))
              HmsButton(
                label: t.actionRegisterPatient,
                icon: LucideIcons.userPlus,
                onPressed: () => open('/patients'),
              ),
          ],
        ),
        if (error != null) ...[
          const SizedBox(height: AppSpacing.x6),
          HmsAlert(
            tone: AlertTone.danger,
            title: t.dashboardLoadFailed,
            message: apiErrorMessage(t, error!),
            action: HmsButton(
              label: t.retry,
              size: HmsButtonSize.small,
              variant: HmsButtonVariant.secondary,
              onPressed: onRetry,
            ),
          ),
        ],
        if (tiles.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.x6),
          Semantics(
            label: t.todayAtAGlance,
            container: true,
            child: StatTileGrid(
              children: [
                for (final tile in tiles)
                  loading && s == null
                      ? const HmsSkeleton()
                      : dashboardTile(t, tile, s),
              ],
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.x6),
        if (twoColumns)
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 2, child: _Stack(children: main)),
              if (main.isNotEmpty) const SizedBox(width: AppSpacing.x6),
              Expanded(child: _Stack(children: side)),
            ],
          )
        else
          _Stack(children: [...main, ...side]),
      ],
    );
  }

  String _title(AppLocalizations t, String? firstName) {
    final hour = now.hour;
    final greeting = hour < 12
        ? t.goodMorning
        : hour < 17
        ? t.goodAfternoon
        : t.goodEvening;
    return firstName == null || firstName.isEmpty
        ? greeting
        : t.greetingWithName(greeting, firstName);
  }

  List<AttentionItem> _attention(
    AppLocalizations t,
    DashboardStats s,
    bool Function(String) canView,
  ) {
    final emergencies = s.count('emergency', 'active');
    final urgentLab = s.count('laboratory', 'urgent');
    final waiting = s.count('queue', 'waiting');
    final labPending = s.count('laboratory', 'pending');
    final billing = s.count('billing', 'pending');
    return [
      if (canView('Emergency') && emergencies > 0)
        AttentionItem(
          tone: HmsTone.danger,
          icon: LucideIcons.siren,
          path: '/emergency',
          text: t.attentionEmergency(emergencies),
        ),
      if (canView('Laboratory') && urgentLab > 0)
        AttentionItem(
          tone: HmsTone.danger,
          icon: LucideIcons.flaskConical,
          path: '/laboratory',
          text: t.attentionUrgentLab(urgentLab),
        ),
      if (canView('Queue') && waiting > 0)
        AttentionItem(
          tone: HmsTone.warning,
          icon: LucideIcons.listOrdered,
          path: '/queue',
          text: t.attentionQueue(waiting),
        ),
      if (canView('Laboratory') && labPending > 0)
        AttentionItem(
          tone: HmsTone.warning,
          icon: LucideIcons.clipboardCheck,
          path: '/laboratory',
          text: t.attentionLabPending(labPending),
        ),
      if (canView('Billing') && billing > 0)
        AttentionItem(
          tone: HmsTone.neutral,
          icon: LucideIcons.receiptIndianRupee,
          path: '/billing',
          text: t.attentionBilling(billing),
        ),
      if (canView('IPD') && s.bedsTotal > 0 && s.bedsAvailable == 0)
        AttentionItem(
          tone: HmsTone.warning,
          icon: LucideIcons.bedDouble,
          path: '/ipd',
          text: t.noBedsAvailable,
        ),
    ];
  }
}

/// Cards stacked with the page's 24 px gap (`space-y-6`).
class _Stack extends StatelessWidget {
  const _Stack({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0) const SizedBox(height: AppSpacing.x6),
          children[i],
        ],
      ],
    );
  }
}
