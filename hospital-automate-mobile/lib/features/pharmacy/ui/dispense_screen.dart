import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/security/session_controller.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/ui/doctor_ui.dart' show today;
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/dispense_plan.dart';
import '../data/pharmacy_models.dart';
import '../data/pharmacy_repository.dart';
import 'dispense_line_card.dart';
import 'pharmacy_home_panel.dart' show SaleRow;
import 'pharmacy_ui.dart';

/// A prescription with the stock it can be issued from and what was issued.
@immutable
class DispenseData {
  const DispenseData({
    required this.prescription,
    required this.stock,
    required this.sales,
  });

  final Prescription prescription;
  final List<Medicine> stock;
  final List<PharmacySale>? sales;

  /// Lines still owed on a prescription the server would dispense.
  bool get canDispense =>
      !PharmacyQueue.blocked.contains(prescription.status) &&
      prescription.dispensedAt == null &&
      prescription.items.any((i) => i.id != null && i.remaining > 0);
}

/// Every batch at the hospital, plus a name search per prescribed medicine
/// (so a large catalogue still finds them), without duplicates.
Future<List<Medicine>> loadStockFor(
  PharmacyRepository repo,
  Prescription prescription,
) async {
  final lists = await Future.wait([
    repo.medicines(),
    for (final item in prescription.items) repo.medicines(search: item.name),
  ]);
  final byId = <int, Medicine>{};
  for (final list in lists) {
    for (final m in list) {
      byId[m.id] = m;
    }
  }
  return byId.values.toList();
}

/// `/pharmacy/prescriptions/:id`: check the prescribed medicines, choose
/// stock batches and dispense. The server validates the prescription,
/// stock, quantities and substitutes, deducts stock and writes the ledger
/// in one locked transaction; the app shows only what it confirms.
class DispenseScreen extends StatefulWidget {
  const DispenseScreen({super.key, required this.prescriptionId, this.now});

  final int prescriptionId;
  final DateTime Function()? now;

  @override
  State<DispenseScreen> createState() => _DispenseScreenState();
}

class _DispenseScreenState extends State<DispenseScreen> {
  late final PharmacyRepository _repo = AppScope.read(context).pharmacy;
  late final RecordLoader<DispenseData> _loader = RecordLoader(_fetch)
    ..addListener(_onData);
  DispenseData? _seen;
  Map<int, DispenseLine> _lines = {};
  bool _submitting = false;
  List<DispenseProblem> _problems = const [];
  String? _error;
  DispenseResult? _result;

  Future<DispenseData> _fetch() async {
    final rx = await _repo.prescription(widget.prescriptionId);
    final results = await Future.wait<Object?>([
      loadStockFor(_repo, rx),
      _repo
          .sales(prescriptionId: rx.id)
          .then<List<PharmacySale>?>(
            (rows) => rows,
            onError: (Object _) => null,
          ),
    ]);
    return DispenseData(
      prescription: rx,
      stock: results[0] as List<Medicine>,
      sales: results[1] as List<PharmacySale>?,
    );
  }

  /// Fresh data from the server resets the chosen lines to the defaults.
  void _onData() {
    final data = _loader.data;
    if (data == null || identical(data, _seen)) return;
    _seen = data;
    setState(
      () => _lines = defaultLines(
        data.prescription.items,
        data.stock,
        today(widget.now),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader
      ..removeListener(_onData)
      ..dispose();
    super.dispose();
  }

  Future<void> _dispense(DispenseData data) async {
    if (_submitting) return;
    final t = context.l10n;
    final request = DispenseRequest.build(
      prescriptionId: data.prescription.id,
      items: data.prescription.items,
      lines: _lines,
      stock: data.stock,
    );
    setState(() {
      _problems = request.problems;
      _error = null;
      _result = null;
    });
    if (!request.isValid) return;
    final ok = await _confirm(data);
    if (!ok || !mounted) return;
    setState(() => _submitting = true);
    try {
      final result = await _repo.dispense(request.body!);
      if (mounted) setState(() => _result = result);
    } catch (error) {
      if (mounted) setState(() => _error = dispenseErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _submitting = false);
      // Whatever happened, show the stock and lines the server now holds.
      await _loader.load();
    }
  }

  Future<bool> _confirm(DispenseData data) {
    final t = context.l10n;
    final rx = data.prescription;
    final lines = [
      for (final item in rx.items)
        if (item.id != null && (_lines[item.id!]?.quantity ?? 0) > 0)
          '${item.name} × ${_lines[item.id!]!.quantity}'
              '${_batchSuffix(t, data.stock, _lines[item.id!]!.batchId)}',
    ];
    return showHmsConfirm(
      context,
      title: t.confirmDispenseTitle,
      message: [
        '${rx.patientName ?? t.patientLabel}'
            '${rx.patientUhid == null ? '' : ' · ${t.patientId}: ${rx.patientUhid}'}',
        ...lines,
      ].join('\n'),
      confirmLabel: t.dispense,
    );
  }

  String _batchSuffix(AppLocalizations t, List<Medicine> stock, int? id) {
    final batch = stock.where((m) => m.id == id).firstOrNull;
    return batch?.batch == null ? '' : ' (${t.batchCode(batch!.batch!)})';
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final session = AppScope.of(context).session.state;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: HmsButton(
            label: t.prescriptionQueue,
            icon: LucideIcons.arrowLeft,
            variant: HmsButtonVariant.ghost,
            size: HmsButtonSize.small,
            onPressed: () => context.go(PharmacyRoutes.home),
          ),
        ),
        const SizedBox(height: AppSpacing.x2),
        RecordSection<DispenseData>(
          loader: _loader,
          builder: (context, data) => _body(context, t, data, session),
        ),
      ],
    );
  }

  Widget _body(
    BuildContext context,
    AppLocalizations t,
    DispenseData data,
    SessionState session,
  ) {
    final rx = data.prescription;
    final day = today(widget.now);
    final editable = data.canDispense && !_submitting;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title:
              '${t.prescriptionCode(rx.id)} · ${rx.patientName ?? t.patientLabel}',
          description: [
            if (rx.patientUhid != null) '${t.patientId}: ${rx.patientUhid}',
            ?rx.doctorName,
            formatDateTime(t, rx.createdAt),
          ].join(' · '),
        ),
        const SizedBox(height: AppSpacing.x2),
        Align(
          alignment: Alignment.centerLeft,
          child: StatusBadge(status: rx.status),
        ),
        const SizedBox(height: AppSpacing.x4),
        if (rx.status == 'Cancelled')
          HmsAlert(
            tone: AlertTone.danger,
            title: t.prescriptionCancelledNoDispense,
          )
        else if (rx.status == 'Pending Verification')
          HmsAlert(
            tone: AlertTone.warning,
            title: t.prescriptionNeedsVerification,
          )
        else if (!data.canDispense)
          HmsAlert(tone: AlertTone.info, title: t.nothingLeftToDispense),
        if (_result != null) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(
            tone: AlertTone.success,
            title: _result!.isComplete ? t.dispensedInFull : t.dispensedInPart,
            message: _result!.invoiceNumber == null
                ? null
                : t.chargedOnBill(
                    _result!.invoiceNumber!,
                    formatRupees(_result!.invoiceTotal),
                  ),
          ),
        ],
        if (_error != null) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(tone: AlertTone.danger, title: _error!),
        ],
        if (_problems.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(
            tone: AlertTone.warning,
            title: t.checkDispenseLines,
            message: [for (final p in _problems) dispenseProblemText(t, p)]
                .join('\n'),
          ),
        ],
        const SizedBox(height: AppSpacing.x4),
        for (final item in rx.items) ...[
          DispenseLineCard(
            key: ValueKey('line-${item.id}-${identityHashCode(data)}'),
            item: item,
            stock: data.stock,
            today: day,
            line: item.id == null ? null : _lines[item.id!],
            editable: editable && item.id != null && item.remaining > 0,
            allowSubstitutes: maySubstitute(session),
            onChanged: (line) =>
                setState(() => _lines = {..._lines, item.id!: line}),
          ),
          const SizedBox(height: AppSpacing.x3),
        ],
        if (data.canDispense)
          HmsButton(
            key: const Key('dispense'),
            label: t.dispense,
            icon: LucideIcons.packageCheck,
            loading: _submitting,
            expand: true,
            onPressed: _submitting ? null : () => _dispense(data),
          ),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.dispensingHistory,
                icon: LucideIcons.history,
              ),
              if (data.sales == null)
                HmsEmptyState(compact: true, title: t.notAvailableNow)
              else if (data.sales!.isEmpty)
                HmsEmptyState(compact: true, title: t.noDispensingYet)
              else
                HmsDividedColumn(
                  children: [for (final s in data.sales!) SaleRow(sale: s)],
                ),
            ],
          ),
        ),
      ],
    );
  }
}
