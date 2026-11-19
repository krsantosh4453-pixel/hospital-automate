import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_search_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/ui/doctor_ui.dart' show today;
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/pharmacy_models.dart';
import '../data/pharmacy_repository.dart';
import 'pharmacy_home_panel.dart';
import 'pharmacy_ui.dart';

enum PharmacyView { prescriptions, medicines, activity }

enum QueueTab { toDispense, awaitingVerification, dispensed }

enum StockFilter { all, lowStock, outOfStock, expired }

/// Whether [m] shows under [filter] on [day]. Stock figures are the server's.
bool matchesStockFilter(Medicine m, StockFilter filter, DateTime day) =>
    switch (filter) {
      StockFilter.all => true,
      StockFilter.lowStock => m.isLowStock,
      StockFilter.outOfStock => m.isOutOfStock,
      StockFilter.expired => m.isExpired(day) && !m.isOutOfStock,
    };

/// `/pharmacy` for pharmacy staff: the prescription queue, the medicine
/// stock and recent activity. Stock is read-only here.
class PharmacyScreen extends StatefulWidget {
  const PharmacyScreen({super.key, this.now});

  final DateTime Function()? now;

  @override
  State<PharmacyScreen> createState() => _PharmacyScreenState();
}

class _PharmacyScreenState extends State<PharmacyScreen> {
  PharmacyView _view = PharmacyView.prescriptions;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    String label(PharmacyView v) => switch (v) {
      PharmacyView.prescriptions => t.prescriptionQueue,
      PharmacyView.medicines => t.medicineStock,
      PharmacyView.activity => t.pharmacyActivity,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.navPharmacy, description: t.pharmacyIntro),
        const SizedBox(height: AppSpacing.x4),
        SegmentedButton<PharmacyView>(
          showSelectedIcon: false,
          segments: [
            for (final v in PharmacyView.values)
              ButtonSegment(value: v, label: Text(label(v))),
          ],
          selected: {_view},
          onSelectionChanged: (s) => setState(() => _view = s.first),
        ),
        const SizedBox(height: AppSpacing.x4),
        switch (_view) {
          PharmacyView.prescriptions => const _QueueView(),
          PharmacyView.medicines => _StockView(now: widget.now),
          PharmacyView.activity => const _ActivityView(),
        },
      ],
    );
  }
}

class _QueueView extends StatefulWidget {
  const _QueueView();

  @override
  State<_QueueView> createState() => _QueueViewState();
}

class _QueueViewState extends State<_QueueView> {
  late final PharmacyRepository _repo = AppScope.read(context).pharmacy;
  late final RecordLoader<Counted<Prescription>> _loader = RecordLoader(
    () => _repo.prescriptions(
      statuses: switch (_tab) {
        QueueTab.toDispense => PharmacyQueue.toDispense,
        QueueTab.awaitingVerification => PharmacyQueue.awaitingVerification,
        QueueTab.dispensed => PharmacyQueue.dispensed,
      },
      search: _search,
      oldestFirst: _tab != QueueTab.dispensed,
    ),
  );
  QueueTab _tab = QueueTab.toDispense;
  String _search = '';

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

  void _setTab(QueueTab tab) {
    setState(() => _tab = tab);
    _loader.load();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    String label(QueueTab q) => switch (q) {
      QueueTab.toDispense => t.toDispense,
      QueueTab.awaitingVerification => t.awaitingVerification,
      QueueTab.dispensed => t.statusDispensed,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsSearchField(
          hint: t.searchPrescriptionsHint,
          onChanged: (value) => _search = value,
          onSubmitted: (value) {
            _search = value;
            _loader.load();
          },
        ),
        const SizedBox(height: AppSpacing.x3),
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final q in QueueTab.values)
              ChoiceChip(
                label: Text(label(q)),
                selected: _tab == q,
                onSelected: (_) => _setTab(q),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<Counted<Prescription>>(
          loader: _loader,
          builder: (context, page) {
            if (page.rows.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.fileText,
                  title: t.noPrescriptionsInQueue,
                ),
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if ((page.count ?? 0) > page.rows.length)
                  Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.x2),
                    child: Text(
                      t.showingFirstOf(page.rows.length, page.count!),
                      style: AppTypography.caption(color: AppColors.ink500),
                    ),
                  ),
                HmsCard(
                  child: HmsDividedColumn(
                    children: [
                      for (final rx in page.rows) _QueueRow(prescription: rx),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _QueueRow extends StatelessWidget {
  const _QueueRow({required this.prescription});

  final Prescription prescription;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final rx = prescription;
    return InkWell(
      onTap: () => context.go(PharmacyRoutes.prescription(rx.id)),
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${t.prescriptionCode(rx.id)} · ${rx.patientName ?? t.patientLabel}',
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  Text(
                    [
                      if (rx.patientUhid != null)
                        '${t.patientId}: ${rx.patientUhid}',
                      ?rx.doctorName,
                      formatDateTime(t, rx.createdAt),
                      t.medicineCount(rx.items.length),
                    ].join(' · '),
                    style: AppTypography.caption(),
                  ),
                ],
              ),
            ),
            StatusBadge(status: rx.status),
            const SizedBox(width: AppSpacing.x2),
            const Icon(
              LucideIcons.chevronRight,
              size: 16,
              color: AppColors.onCardMuted,
            ),
          ],
        ),
      ),
    );
  }
}

class _StockView extends StatefulWidget {
  const _StockView({this.now});

  final DateTime Function()? now;

  @override
  State<_StockView> createState() => _StockViewState();
}

class _StockViewState extends State<_StockView> {
  late final PharmacyRepository _repo = AppScope.read(context).pharmacy;
  late final RecordLoader<List<Medicine>> _loader = RecordLoader(
    () => _repo.medicines(search: _search),
  );
  String _search = '';
  StockFilter _filter = StockFilter.all;

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
    final day = today(widget.now);
    String label(StockFilter f) => switch (f) {
      StockFilter.all => t.filterAll,
      StockFilter.lowStock => t.lowStock,
      StockFilter.outOfStock => t.outOfStock,
      StockFilter.expired => t.expiredInStock,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsSearchField(
          hint: t.searchMedicinesHint,
          onChanged: (value) => _search = value,
          onSubmitted: (value) {
            _search = value;
            _loader.load();
          },
        ),
        const SizedBox(height: AppSpacing.x3),
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final f in StockFilter.values)
              ChoiceChip(
                label: Text(label(f)),
                selected: _filter == f,
                onSelected: (_) => setState(() => _filter = f),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x3),
        HmsAlert(tone: AlertTone.info, title: t.stockChangedByStore),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<Medicine>>(
          loader: _loader,
          builder: (context, medicines) {
            final shown = [
              for (final m in medicines)
                if (matchesStockFilter(m, _filter, day)) m,
            ];
            if (shown.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.pill,
                  title: t.noMedicinesFound,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final m in shown) MedicineRow(medicine: m, today: day),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

/// One stock batch: name, batch, quantity, expiry and price.
class MedicineRow extends StatelessWidget {
  const MedicineRow({super.key, required this.medicine, required this.today});

  final Medicine medicine;
  final DateTime today;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final m = medicine;
    final flag = m.isExpired(today)
        ? t.expiredInStock
        : m.isOutOfStock
        ? t.outOfStock
        : m.isLowStock
        ? t.lowStock
        : null;
    return InkWell(
      onTap: () => context.go(PharmacyRoutes.medicine(m.id)),
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    m.name,
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  Text(
                    [
                      if (m.batch != null) t.batchCode(m.batch!),
                      t.inStockCount(m.quantity, m.unit ?? ''),
                      if (m.expiryDate != null)
                        t.expiresOn(formatDay(t, m.expiryDate)),
                      formatRupees(m.price),
                    ].join(' · '),
                    style: AppTypography.caption(),
                  ),
                ],
              ),
            ),
            if (flag != null)
              StatusBadge(
                status: m.isLowStock ? 'Held' : 'Cancelled',
                label: flag,
              ),
          ],
        ),
      ),
    );
  }
}

class _ActivityView extends StatefulWidget {
  const _ActivityView();

  @override
  State<_ActivityView> createState() => _ActivityViewState();
}

class _ActivityViewState extends State<_ActivityView> {
  late final RecordLoader<PharmacyDay> _loader = RecordLoader(() {
    final services = AppScope.read(context);
    return PharmacyDay.load(
      services.pharmacy,
      hospitalId: services.session.state.activeHospitalId ?? 0,
    );
  });

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
  Widget build(BuildContext context) => RecordSection<PharmacyDay>(
    loader: _loader,
    skeletons: 2,
    builder: (context, day) => PharmacyDayBody(day: day),
  );
}
