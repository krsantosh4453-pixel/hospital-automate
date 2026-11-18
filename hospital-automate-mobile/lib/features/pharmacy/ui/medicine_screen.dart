import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/pharmacy_models.dart';
import 'pharmacy_home_panel.dart' show MovementRow;
import 'pharmacy_ui.dart';

/// `/pharmacy/medicines/:id`: one stock batch and its ledger, read-only.
class MedicineScreen extends StatefulWidget {
  const MedicineScreen({super.key, required this.medicineId});

  final int medicineId;

  @override
  State<MedicineScreen> createState() => _MedicineScreenState();
}

class _MedicineScreenState extends State<MedicineScreen> {
  late final RecordLoader<(Medicine, List<StockMovement>?)> _loader =
      RecordLoader(() async {
        final services = AppScope.read(context);
        final repo = services.pharmacy;
        final hospitalId = services.session.state.activeHospitalId ?? 0;
        final medicine = await repo.medicine(widget.medicineId);
        List<StockMovement>? ledger;
        try {
          ledger = await repo.stockMovements(
            hospitalId: hospitalId,
            medicineId: medicine.id,
          );
        } on Exception {
          ledger = null;
        }
        return (medicine, ledger);
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
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: HmsButton(
            label: t.navPharmacy,
            icon: LucideIcons.arrowLeft,
            variant: HmsButtonVariant.ghost,
            size: HmsButtonSize.small,
            onPressed: () => context.go(PharmacyRoutes.home),
          ),
        ),
        const SizedBox(height: AppSpacing.x2),
        RecordSection<(Medicine, List<StockMovement>?)>(
          loader: _loader,
          builder: (context, data) {
            final (m, ledger) = data;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                PageHeader(title: m.name, description: m.genericName),
                const SizedBox(height: AppSpacing.x4),
                HmsCard(
                  child: HmsDividedColumn(
                    children: [
                      DetailRow(
                        label: t.inStock,
                        value: t.inStockCount(m.quantity, m.unit ?? ''),
                      ),
                      DetailRow(label: t.reorderLevel, value: m.reorderLevel?.toString()),
                      DetailRow(label: t.batch, value: m.batch),
                      DetailRow(label: t.expiryDate, value: formatDay(t, m.expiryDate)),
                      DetailRow(label: t.manufacturer, value: m.manufacturer),
                      DetailRow(label: t.category, value: m.category),
                      DetailRow(label: t.unitPrice, value: formatRupees(m.price)),
                      DetailRow(label: t.mrp, value: formatRupees(m.mrp)),
                      DetailRow(
                        label: t.drugSchedule,
                        value: (m.drugSchedule ?? '').isEmpty
                            ? t.notScheduled
                            : m.drugSchedule,
                      ),
                      DetailRow(label: t.supplier, value: m.supplierName),
                      DetailRow(label: t.status, value: m.status),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.x4),
                HmsAlert(tone: AlertTone.info, title: t.stockChangedByStore),
                const SizedBox(height: AppSpacing.x4),
                HmsCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      HmsCardHeader(
                        title: t.stockMovements,
                        icon: LucideIcons.arrowLeftRight,
                      ),
                      if (ledger == null)
                        HmsEmptyState(compact: true, title: t.notAvailableNow)
                      else if (ledger.isEmpty)
                        HmsEmptyState(compact: true, title: t.noStockMovements)
                      else
                        HmsDividedColumn(
                          children: [
                            for (final row in ledger) MovementRow(movement: row),
                          ],
                        ),
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
