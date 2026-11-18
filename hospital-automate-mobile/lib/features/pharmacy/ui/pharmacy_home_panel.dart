import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/pharmacy_models.dart';
import '../data/pharmacy_repository.dart';
import 'pharmacy_ui.dart';

/// What the pharmacy home shows, each part loaded on its own: a part that
/// fails is null and shows "not available", the others still show.
class PharmacyDay {
  const PharmacyDay({
    this.stock,
    this.queue,
    this.recentSales,
    this.recentMovements,
  });

  static Future<PharmacyDay> load(
    PharmacyRepository repository, {
    required int hospitalId,
  }) async {
    Future<T?> settle<T>(Future<T> future) async {
      try {
        return await future;
      } on ApiException {
        return null;
      }
    }

    final results = await Future.wait(<Future<Object?>>[
      settle(repository.stockSummary(hospitalId)),
      settle(
        repository.prescriptions(
          statuses: PharmacyQueue.toDispense,
          oldestFirst: true,
        ),
      ),
      settle(repository.sales()),
      settle(repository.stockMovements(hospitalId: hospitalId)),
    ]);
    return PharmacyDay(
      stock: results[0] as PharmacyStockSummary?,
      queue: results[1] as Counted<Prescription>?,
      recentSales: results[2] as List<PharmacySale>?,
      recentMovements: results[3] as List<StockMovement>?,
    );
  }

  final PharmacyStockSummary? stock;
  final Counted<Prescription>? queue;
  final List<PharmacySale>? recentSales;
  final List<StockMovement>? recentMovements;
}

/// The pharmacy part of the staff home (below the role dashboard).
class PharmacyHomePanel extends StatefulWidget {
  const PharmacyHomePanel({
    super.key,
    required this.repository,
    required this.hospitalId,
  });

  final PharmacyRepository repository;
  final int hospitalId;

  @override
  State<PharmacyHomePanel> createState() => _PharmacyHomePanelState();
}

class _PharmacyHomePanelState extends State<PharmacyHomePanel> {
  late final RecordLoader<PharmacyDay> _loader = RecordLoader(
    () => PharmacyDay.load(widget.repository, hospitalId: widget.hospitalId),
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
  Widget build(BuildContext context) => RecordSection<PharmacyDay>(
    loader: _loader,
    skeletons: 2,
    builder: (context, day) => PharmacyDayBody(day: day),
  );
}

class PharmacyDayBody extends StatelessWidget {
  const PharmacyDayBody({super.key, required this.day});

  final PharmacyDay day;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final stock = day.stock;
    Widget unavailable() =>
        HmsEmptyState(compact: true, title: t.notAvailableNow);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        StatTileGrid(
          children: [
            StatTile(
              label: t.totalMedicines,
              value: stock?.totalMedicines?.toString(),
              icon: LucideIcons.pill,
            ),
            StatTile(
              label: t.inStockMedicines,
              value: stock?.inStock?.toString(),
              icon: LucideIcons.packageCheck,
              tone: HmsTone.success,
            ),
            StatTile(
              label: t.lowStock,
              value: stock?.lowStock?.toString(),
              icon: LucideIcons.trendingDown,
              tone: HmsTone.warning,
            ),
            StatTile(
              label: t.outOfStock,
              value: stock?.outOfStock?.toString(),
              icon: LucideIcons.packageX,
              tone: HmsTone.danger,
            ),
            StatTile(
              label: t.expiredInStock,
              value: stock?.expired?.toString(),
              icon: LucideIcons.calendarX,
              tone: HmsTone.danger,
            ),
            StatTile(
              label: t.pendingPrescriptions,
              value: day.queue?.count?.toString(),
              icon: LucideIcons.fileText,
              tone: HmsTone.accent,
            ),
          ],
        ),
        if (stock?.expiringSoon != null && stock!.expiringSoon! > 0) ...[
          const SizedBox(height: AppSpacing.x4),
          HmsAlert(
            tone: AlertTone.warning,
            title: t.expiringSoonCount(stock.expiringSoon!),
          ),
        ],
        const SizedBox(height: AppSpacing.x4),
        _ListCard(
          title: t.recentDispensing,
          icon: LucideIcons.receipt,
          child: day.recentSales == null
              ? unavailable()
              : day.recentSales!.isEmpty
              ? HmsEmptyState(compact: true, title: t.noDispensingYet)
              : HmsDividedColumn(
                  children: [
                    for (final sale in day.recentSales!.take(5))
                      SaleRow(sale: sale),
                  ],
                ),
        ),
        const SizedBox(height: AppSpacing.x4),
        _ListCard(
          title: t.recentStockMovements,
          icon: LucideIcons.arrowLeftRight,
          child: day.recentMovements == null
              ? unavailable()
              : day.recentMovements!.isEmpty
              ? HmsEmptyState(compact: true, title: t.noStockMovements)
              : HmsDividedColumn(
                  children: [
                    for (final m in day.recentMovements!.take(5))
                      MovementRow(movement: m),
                  ],
                ),
        ),
      ],
    );
  }
}

class _ListCard extends StatelessWidget {
  const _ListCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(
          title: title,
          icon: icon,
          trailing: TextButton(
            onPressed: () => context.go(PharmacyRoutes.home),
            child: Text(
              context.l10n.viewAll,
              style: AppTypography.small(color: AppColors.onCard),
            ),
          ),
        ),
        child,
      ],
    ),
  );
}

/// One sale: what was issued, to whom, when.
class SaleRow extends StatelessWidget {
  const SaleRow({super.key, required this.sale});

  final PharmacySale sale;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final row = DetailRow(
      label: formatDateTime(t, sale.createdAt),
      value: [
        '${sale.medicineName ?? t.medicineName} × ${sale.quantity}',
        ?sale.patientName,
        if (sale.substitutedFor != null) t.substituteFor(sale.substitutedFor!),
      ].join(' · '),
    );
    final rx = sale.prescriptionId;
    return rx == null
        ? row
        : InkWell(
            onTap: () => context.go(PharmacyRoutes.prescription(rx)),
            child: row,
          );
  }
}

/// One stock ledger row.
class MovementRow extends StatelessWidget {
  const MovementRow({super.key, required this.movement});

  final StockMovement movement;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return DetailRow(
      label: formatDateTime(t, movement.createdAt),
      value: [
        '${movementLabel(t, movement.type)} ${movement.quantity}',
        ?movement.medicineName,
        ?movement.reason,
      ].join(' · '),
    );
  }
}
