import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../operations/ops_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart' show RecordSection;
import '../data/emergency_models.dart';
import '../data/emergency_repository.dart';
import 'emergency_forms.dart';
import 'emergency_ui.dart';

enum ErFilter { active, closed, all }

/// The visits [filter] keeps, most urgent first for active ones.
List<EmergencyVisit> filterVisits(
  List<EmergencyVisit> visits,
  ErFilter filter,
) => switch (filter) {
  ErFilter.active => byUrgency(visits.where((v) => !v.isClosed)),
  ErFilter.closed => List.unmodifiable(visits.where((v) => v.isClosed)),
  ErFilter.all => List.unmodifiable(visits),
};

/// `/emergency`: the ER board of the acting hospital.
class EmergencyScreen extends StatefulWidget {
  const EmergencyScreen({super.key});

  @override
  State<EmergencyScreen> createState() => _EmergencyScreenState();
}

class _EmergencyScreenState extends State<EmergencyScreen>
    with PullToRefresh<EmergencyScreen> {
  late final EmergencyRepository _repository = AppScope.read(context).emergency;
  late final RecordLoader<ErDashboard> _dashboard = RecordLoader(
    _repository.dashboard,
  );
  late final RecordLoader<List<EmergencyVisit>> _visits = RecordLoader(
    _repository.visits,
  );
  ErFilter _filter = ErFilter.active;
  String? _notice;

  @override
  void initState() {
    super.initState();
    reload();
  }

  @override
  void dispose() {
    _dashboard.dispose();
    _visits.dispose();
    super.dispose();
  }

  @override
  Future<void> reload() => Future.wait([_dashboard.load(), _visits.load()]);

  Future<void> _register() async {
    final registered = await showRegisterErSheet(context, _repository);
    if (!registered || !mounted) return;
    setState(() => _notice = context.l10n.erRegistered);
    await reload();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final session = AppScope.of(context).session.state;
    final canAdd = session.can(emergencyModule, 'Add');
    final canEdit = session.can(emergencyModule, 'Edit');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.navEmergency,
          description: t.erIntro,
          actions: [
            HmsButton(
              label: t.refresh,
              icon: LucideIcons.refreshCw,
              variant: HmsButtonVariant.secondary,
              onPressed: reload,
            ),
            if (canAdd)
              HmsButton(
                key: const Key('er-register'),
                label: t.erRegisterPatient,
                icon: LucideIcons.plus,
                onPressed: _register,
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        OutcomeBanner(success: _notice),
        if (!canEdit) ReadOnlyNotice(message: t.erReadOnly),
        RecordSection<ErDashboard>(
          loader: _dashboard,
          skeletons: 1,
          builder: (context, board) => StatTileGrid(
            children: [
              StatTile(
                label: t.erActiveNow,
                value: '${board.totalActive}',
                icon: LucideIcons.siren,
                tone: HmsTone.danger,
              ),
              StatTile(
                label: t.statusWaiting,
                value: '${board.status(ErStatus.waiting)}',
                icon: LucideIcons.clock,
                tone: HmsTone.warning,
              ),
              StatTile(
                label: t.erStatusUnderConsultation,
                value: '${board.status(ErStatus.underConsultation)}',
                icon: LucideIcons.stethoscope,
              ),
              StatTile(
                label: t.erStatusDischarged,
                value: '${board.status(ErStatus.discharged)}',
                icon: LucideIcons.circleCheck,
                tone: HmsTone.success,
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        Wrap(
          spacing: AppSpacing.x2,
          children: [
            for (final filter in ErFilter.values)
              ChoiceChip(
                label: Text(switch (filter) {
                  ErFilter.active => t.erFilterActive,
                  ErFilter.closed => t.erFilterClosed,
                  ErFilter.all => t.filterAll,
                }),
                selected: _filter == filter,
                onSelected: (_) => setState(() => _filter = filter),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<EmergencyVisit>>(
          loader: _visits,
          builder: (context, visits) {
            final shown = filterVisits(visits, _filter);
            if (shown.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.siren,
                  title: _filter == ErFilter.active
                      ? t.erNoActiveVisits
                      : t.erNoVisits,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final visit in shown)
                    EmergencyVisitRow(
                      key: ValueKey('er-visit-${visit.id}'),
                      visit: visit,
                      onTap: () => context.go(EmergencyRoutes.visit(visit.id)),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}
