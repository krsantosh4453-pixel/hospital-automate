import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_search_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../dashboard/dashboard_stats.dart';
import '../../doctor/ui/doctor_lists_screens.dart' show DoctorLabScreen;
import '../../doctor/ui/doctor_ui.dart' show isDoctor;
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/lab_workflow.dart';
import 'lab_ui.dart';

/// `/laboratory` for the lab desk (Lab Staff, Nurse, Admin, Hospital
/// Manager): the hospital's counts, the order worklist by stage, and a
/// sample-number lookup. Doctors keep their own list of ordered tests.
class LaboratoryScreen extends StatefulWidget {
  const LaboratoryScreen({super.key});

  @override
  State<LaboratoryScreen> createState() => _LaboratoryScreenState();
}

class _LaboratoryScreenState extends State<LaboratoryScreen> {
  late final _services = AppScope.read(context);
  late final RecordLoader<List<LabTest>> _orders = RecordLoader(
    _services.laboratory.orders,
  );
  late final RecordLoader<DashboardStats?> _stats = RecordLoader(() async {
    final hospital = _services.session.activeHospitalId;
    return hospital == null ? null : _services.dashboard.fetch(hospital);
  });
  LabQueue? _queue;
  String _search = '';
  bool _findingSample = false;
  String? _sampleError;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void dispose() {
    _orders.dispose();
    _stats.dispose();
    super.dispose();
  }

  Future<void> _refresh() => Future.wait([_orders.load(), _stats.load()]);

  /// The order whose sample carries [number] (barcode label or typed).
  Future<void> _findSample(String number) async {
    if (number.trim().isEmpty || _findingSample) return;
    final t = context.l10n;
    setState(() {
      _findingSample = true;
      _sampleError = null;
    });
    try {
      final test = await _services.laboratory.findBySample(number);
      if (mounted) context.go(LabRoutes.order(test.id));
    } catch (error) {
      if (mounted) setState(() => _sampleError = labErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _findingSample = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final session = _services.session.state;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.navLaboratory,
          description: t.labDeskIntro,
          actions: [
            HmsButton(
              label: t.refresh,
              icon: LucideIcons.refreshCw,
              variant: HmsButtonVariant.secondary,
              onPressed: _refresh,
            ),
            if (mayOrderLabTests(session))
              HmsButton(
                key: const Key('new-lab-order'),
                label: t.labNewOrder,
                icon: LucideIcons.plus,
                onPressed: () => context.go(LabRoutes.newOrder),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        _LabCounts(loader: _stats),
        const SizedBox(height: AppSpacing.x4),
        HmsSearchField(
          key: const Key('lab-find-sample'),
          hint: t.labFindSampleHint,
          semanticLabel: t.labFindSample,
          surface: HmsSurface.canvas,
          onChanged: (_) {},
          onSubmitted: _findSample,
        ),
        if (_findingSample) const LinearProgressIndicator(),
        if (_sampleError != null) ...[
          const SizedBox(height: AppSpacing.x2),
          HmsAlert(tone: AlertTone.warning, title: _sampleError!),
        ],
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<LabTest>>(
          loader: _orders,
          builder: (context, tests) => _worklist(context, tests),
        ),
      ],
    );
  }

  Widget _worklist(BuildContext context, List<LabTest> tests) {
    final t = context.l10n;
    final query = _search.trim().toLowerCase();
    final shown = [
      for (final test in tests)
        if ((_queue == null || _queue!.statuses.contains(test.status)) &&
            (query.isEmpty || _matches(test, query)))
          test,
    ];
    int count(LabQueue q) =>
        tests.where((test) => q.statuses.contains(test.status)).length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            ChoiceChip(
              label: Text('${t.filterAll} (${tests.length})'),
              selected: _queue == null,
              onSelected: (_) => setState(() => _queue = null),
            ),
            for (final queue in LabQueue.values)
              ChoiceChip(
                key: Key('lab-queue-${queue.name}'),
                label: Text('${labQueueLabel(t, queue)} (${count(queue)})'),
                selected: _queue == queue,
                onSelected: (_) => setState(() => _queue = queue),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x3),
        HmsSearchField(
          key: const Key('lab-search'),
          hint: t.labSearchHint,
          surface: HmsSurface.canvas,
          onChanged: (value) => setState(() => _search = value),
        ),
        const SizedBox(height: AppSpacing.x3),
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.labWorklist,
                description: t.labWorklistNewestFirst,
                icon: LucideIcons.flaskConical,
              ),
              if (shown.isEmpty)
                HmsEmptyState(
                  icon: LucideIcons.flaskConical,
                  title: tests.isEmpty ? t.labNoOrdersYet : t.labNoOrdersMatch,
                )
              else
                HmsDividedColumn(
                  children: [
                    for (final test in shown)
                      LabOrderRow(
                        key: Key('lab-order-${test.id}'),
                        test: test,
                        onTap: () => context.go(LabRoutes.order(test.id)),
                      ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }

  static bool _matches(LabTest test, String query) => [
    test.name,
    test.patientName,
    test.sample?.sampleId,
    test.doctorName,
  ].any((field) => field != null && field.toLowerCase().contains(query));
}

/// The hospital's laboratory counts as the server computes them
/// (`home/stats/detail/`), not counted from the rows on this phone.
class _LabCounts extends StatelessWidget {
  const _LabCounts({required this.loader});

  final RecordLoader<DashboardStats?> loader;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return ListenableBuilder(
      listenable: loader,
      builder: (context, _) {
        final stats = loader.data;
        String? value(String key) =>
            stats == null ? null : '${stats.count('laboratory', key)}';
        if (loader.error != null && stats == null) {
          return HmsAlert(
            tone: AlertTone.warning,
            title: t.labCountsUnavailable,
            message: apiErrorMessage(t, loader.error!),
          );
        }
        return StatTileGrid(
          children: [
            StatTile(
              label: t.labTotalOrders,
              value: value('total'),
              icon: LucideIcons.flaskConical,
            ),
            StatTile(
              label: t.tileLabPending,
              value: value('pending'),
              icon: LucideIcons.hourglass,
              tone: HmsTone.warning,
            ),
            StatTile(
              label: t.tileLabUrgent,
              value: value('urgent'),
              icon: LucideIcons.siren,
              tone: HmsTone.danger,
            ),
            StatTile(
              label: t.tileLabCompleted,
              value: value('completed'),
              icon: LucideIcons.circleCheck,
              tone: HmsTone.success,
            ),
          ],
        );
      },
    );
  }
}

/// `/laboratory`: doctors keep their list of the tests they ordered; every
/// other role that may view the module gets the lab desk. Rebuilt when the
/// hospital (and so the role) changes, by the page around it.
class LabHomeScreen extends StatelessWidget {
  const LabHomeScreen({super.key});

  @override
  Widget build(BuildContext context) =>
      isDoctor(AppScope.of(context).session.state)
      ? const DoctorLabScreen()
      : const LaboratoryScreen();
}
