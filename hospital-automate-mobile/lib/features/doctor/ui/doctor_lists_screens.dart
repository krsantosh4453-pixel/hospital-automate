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
import '../../../shared/widgets/states.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/clinical_records_screens.dart' show PrescriptionCard;
import '../../patient/ui/patient_ui.dart';
import 'doctor_ui.dart';
import 'patient_records_screens.dart' show LabTestRow;

/// `/prescription` for a doctor: prescriptions of patients in their care,
/// newest first. New ones are written in a consultation (the server only
/// accepts a doctor's prescription on their own visit), so this list links there.
class DoctorPrescriptionsScreen extends StatefulWidget {
  const DoctorPrescriptionsScreen({super.key});

  @override
  State<DoctorPrescriptionsScreen> createState() =>
      _DoctorPrescriptionsScreenState();
}

class _DoctorPrescriptionsScreenState extends State<DoctorPrescriptionsScreen> {
  late final RecordLoader<List<Prescription>> _loader = RecordLoader(
    () => AppScope.read(context).doctor.prescriptions(),
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
        PageHeader(
          title: t.navPrescription,
          description: t.doctorPrescriptionsIntro,
          actions: [
            HmsButton(
              label: t.writeInConsultation,
              icon: LucideIcons.stethoscope,
              onPressed: () => context.go(DoctorRoutes.consultation),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<Prescription>>(
          loader: _loader,
          builder: (context, rows) {
            if (rows.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.pill,
                  title: t.noPrescriptionsYet,
                ),
              );
            }
            final sorted = [...rows]
              ..sort(
                (a, b) => (b.createdAt ?? DateTime(0)).compareTo(
                  a.createdAt ?? DateTime(0),
                ),
              );
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final rx in sorted) ...[
                  if (rx.patientName != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.x1),
                      child: Text(
                        rx.patientName!,
                        style: AppTypography.small(weight: FontWeight.w600),
                      ),
                    ),
                  PrescriptionCard(prescription: rx),
                  const SizedBox(height: AppSpacing.x3),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

/// `/laboratory` for a doctor: tests of patients in their care with their
/// status; values appear only after the laboratory releases them.
class DoctorLabScreen extends StatefulWidget {
  const DoctorLabScreen({super.key});

  @override
  State<DoctorLabScreen> createState() => _DoctorLabScreenState();
}

class _DoctorLabScreenState extends State<DoctorLabScreen> {
  late final RecordLoader<List<LabTest>> _loader = RecordLoader(
    () => AppScope.read(context).doctor.labTests(),
  );
  bool _releasedOnly = false;

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
        PageHeader(title: t.navLaboratory, description: t.doctorLabIntro),
        const SizedBox(height: AppSpacing.x4),
        Wrap(
          spacing: AppSpacing.x2,
          children: [
            ChoiceChip(
              label: Text(t.filterAll),
              selected: !_releasedOnly,
              onSelected: (_) => setState(() => _releasedOnly = false),
            ),
            ChoiceChip(
              label: Text(t.releasedResults),
              selected: _releasedOnly,
              onSelected: (_) => setState(() => _releasedOnly = true),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<LabTest>>(
          loader: _loader,
          builder: (context, tests) {
            final shown = [
              for (final test in tests)
                if (!_releasedOnly || test.status == 'Released') test,
            ];
            if (shown.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.flaskConical,
                  title: t.noLabReportsYet,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [for (final test in shown) LabTestRow(test: test)],
              ),
            );
          },
        ),
      ],
    );
  }
}
