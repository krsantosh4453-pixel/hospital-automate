import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../operations/ops_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart' show RecordSection;
import '../data/ipd_models.dart';
import '../data/ipd_repository.dart';
import 'ipd_ui.dart';

enum IpdFilter { current, discharged, all }

/// The stays [filter] keeps. "Current" are the ones still in hospital.
List<IpdAdmission> filterAdmissions(
  List<IpdAdmission> rows,
  IpdFilter filter,
) => List.unmodifiable(switch (filter) {
  IpdFilter.current => rows.where((a) => a.isAdmitted || a.isDischarging),
  IpdFilter.discharged => rows.where(
    (a) => a.status == AdmissionStatus.discharged,
  ),
  IpdFilter.all => rows,
});

/// `/ipd`: inpatient stays and the bed board of the acting hospital.
class IpdScreen extends StatefulWidget {
  const IpdScreen({super.key});

  @override
  State<IpdScreen> createState() => _IpdScreenState();
}

class _IpdScreenState extends State<IpdScreen> with PullToRefresh<IpdScreen> {
  late final IpdRepository _repository = AppScope.read(context).ipd;
  late final int? _hospitalId = AppScope.read(context).session.activeHospitalId;
  late final RecordLoader<IpdOverview> _overview = RecordLoader(
    () => _repository.overview(_hospitalId ?? 0),
  );
  late final RecordLoader<List<IpdAdmission>> _admissions = RecordLoader(
    _repository.admissions,
  );
  late final RecordLoader<BedBoard> _beds = RecordLoader(_repository.bedBoard);
  bool _showBeds = false;
  IpdFilter _filter = IpdFilter.current;

  @override
  void initState() {
    super.initState();
    reload();
  }

  @override
  void dispose() {
    _overview.dispose();
    _admissions.dispose();
    _beds.dispose();
    super.dispose();
  }

  @override
  Future<void> reload() =>
      Future.wait([_overview.load(), _admissions.load(), _beds.load()]);

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final canEdit = AppScope.of(context).session.state.can(ipdModule, 'Edit');
    String count(int? value) => value == null ? '—' : '$value';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.navIpd,
          description: t.ipdIntro,
          actions: [
            HmsButton(
              label: t.refresh,
              icon: LucideIcons.refreshCw,
              variant: HmsButtonVariant.secondary,
              onPressed: reload,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        if (!canEdit) ReadOnlyNotice(message: t.ipdReadOnly),
        RecordSection<IpdOverview>(
          loader: _overview,
          skeletons: 1,
          builder: (context, o) => StatTileGrid(
            children: [
              StatTile(
                label: t.ipdAdmitted,
                value: count(o.admitted),
                icon: LucideIcons.bedDouble,
              ),
              StatTile(
                label: t.ipdDischargeInitiated,
                value: count(o.dischargeInitiated),
                icon: LucideIcons.logOut,
                tone: HmsTone.warning,
              ),
              StatTile(
                label: t.ipdDischarged,
                value: count(o.discharged),
                icon: LucideIcons.circleCheck,
                tone: HmsTone.success,
              ),
              StatTile(
                label: t.ipdAvailableBeds,
                value: count(o.availableBeds),
                icon: LucideIcons.bed,
                tone: HmsTone.accent,
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        SegmentedButton<bool>(
          segments: [
            ButtonSegment(value: false, label: Text(t.ipdTabAdmissions)),
            ButtonSegment(value: true, label: Text(t.ipdTabBeds)),
          ],
          selected: {_showBeds},
          onSelectionChanged: (value) =>
              setState(() => _showBeds = value.first),
        ),
        const SizedBox(height: AppSpacing.x4),
        if (_showBeds)
          _BedBoardSection(loader: _beds)
        else
          _admissionsSection(t),
      ],
    );
  }

  Widget _admissionsSection(AppLocalizations t) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Wrap(
        spacing: AppSpacing.x2,
        children: [
          for (final filter in IpdFilter.values)
            ChoiceChip(
              label: Text(switch (filter) {
                IpdFilter.current => t.ipdFilterCurrent,
                IpdFilter.discharged => t.ipdDischarged,
                IpdFilter.all => t.filterAll,
              }),
              selected: _filter == filter,
              onSelected: (_) => setState(() => _filter = filter),
            ),
        ],
      ),
      const SizedBox(height: AppSpacing.x4),
      RecordSection<List<IpdAdmission>>(
        loader: _admissions,
        builder: (context, rows) {
          final shown = filterAdmissions(rows, _filter);
          if (shown.isEmpty) {
            return HmsCard(
              child: HmsEmptyState(
                icon: LucideIcons.bedDouble,
                title: t.ipdNoAdmissions,
              ),
            );
          }
          return HmsCard(
            child: HmsDividedColumn(
              children: [
                for (final admission in shown)
                  AdmissionRow(
                    key: ValueKey('admission-${admission.id}'),
                    admission: admission,
                    onTap: () => context.go(IpdRoutes.admission(admission.id)),
                  ),
              ],
            ),
          );
        },
      ),
    ],
  );
}

class _BedBoardSection extends StatelessWidget {
  const _BedBoardSection({required this.loader});

  final RecordLoader<BedBoard> loader;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return RecordSection<BedBoard>(
      loader: loader,
      builder: (context, board) {
        if (board.beds.isEmpty) {
          return HmsCard(
            child: HmsEmptyState(icon: LucideIcons.bed, title: t.ipdNoBeds),
          );
        }
        final wards = board.byWard();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (!board.complete) ...[
              HmsAlert(
                tone: AlertTone.warning,
                title: t.ipdBedsPartial(board.beds.length),
              ),
              const SizedBox(height: AppSpacing.x3),
            ],
            Wrap(
              spacing: AppSpacing.x2,
              runSpacing: AppSpacing.x2,
              children: [
                for (final status in BedStatus.all)
                  ToneBadge(
                    label:
                        '${bedStatusLabel(t, status)}: ${board.count(status)}',
                    tone: bedTone(status),
                  ),
              ],
            ),
            const SizedBox(height: AppSpacing.x4),
            for (final entry in wards.entries) ...[
              HmsCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    HmsCardHeader(
                      title: entry.key,
                      icon: LucideIcons.bedDouble,
                    ),
                    for (final bed in entry.value) _BedRow(bed: bed),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.x3),
            ],
          ],
        );
      },
    );
  }
}

class _BedRow extends StatelessWidget {
  const _BedRow({required this.bed});

  final HospitalBed bed;

  @override
  Widget build(BuildContext context) {
    final place = [
      bed.place.room,
      bed.place.bed,
    ].whereType<String>().join(' · ');
    return Padding(
      key: ValueKey('bed-${bed.id}'),
      padding: AppSpacing.cardRow,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(place, style: AppTypography.body(weight: FontWeight.w600)),
                if (bed.currentPatient != null)
                  Text(bed.currentPatient!, style: AppTypography.small()),
              ],
            ),
          ),
          BedBadge(status: bed.status),
        ],
      ),
    );
  }
}
