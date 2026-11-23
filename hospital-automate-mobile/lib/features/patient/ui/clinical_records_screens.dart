import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../data/record_models.dart';
import '../record_loader.dart';
import 'patient_ui.dart';

/// `/patient/prescriptions`: medicines the doctors prescribed, read-only.
class PrescriptionsScreen extends StatefulWidget {
  const PrescriptionsScreen({super.key});

  @override
  State<PrescriptionsScreen> createState() => _PrescriptionsScreenState();
}

class _PrescriptionsScreenState extends State<PrescriptionsScreen> {
  late final RecordLoader<List<Prescription>> _loader = RecordLoader(
    AppScope.read(context).patient.prescriptions,
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
          title: t.patientNavPrescriptions,
          description: t.prescriptionsIntro,
        ),
        const SizedBox(height: AppSpacing.x6),
        RecordSection<List<Prescription>>(
          loader: _loader,
          builder: (context, prescriptions) {
            if (prescriptions.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.pill,
                  title: t.noPrescriptionsYet,
                  description: t.noPrescriptionsYetHint,
                ),
              );
            }
            final sorted = [...prescriptions]
              ..sort(
                (a, b) => (b.createdAt ?? DateTime(0)).compareTo(
                  a.createdAt ?? DateTime(0),
                ),
              );
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < sorted.length; i++) ...[
                  if (i > 0) const SizedBox(height: AppSpacing.x4),
                  PrescriptionCard(prescription: sorted[i]),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

/// One prescription with every medicine line, exactly as the doctor wrote it.
class PrescriptionCard extends StatelessWidget {
  const PrescriptionCard({super.key, required this.prescription});

  final Prescription prescription;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final p = prescription;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: p.doctorName ?? t.doctor,
            description: [
              formatDay(t, p.createdAt),
              ?p.hospitalName,
            ].join(' · '),
            icon: LucideIcons.pill,
            trailing: StatusBadge(status: p.status),
          ),
          if (p.items.isEmpty)
            HmsEmptyState(compact: true, title: t.noMedicinesListed)
          else
            HmsDividedColumn(
              children: [for (final item in p.items) _MedicineRow(item: item)],
            ),
        ],
      ),
    );
  }
}

class _MedicineRow extends StatelessWidget {
  const _MedicineRow({required this.item});

  final PrescriptionItem item;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final facts = [
      if (item.dosage != null) '${t.dosage}: ${item.dosage}',
      if (item.frequency != null) '${t.frequency}: ${item.frequency}',
      if (item.duration != null) '${t.duration}: ${item.duration}',
      if (item.quantity != null && (item.dispensedQuantity ?? 0) > 0)
        t.prescribedIssuedLeft(
          item.quantity!,
          item.dispensedQuantity!,
          item.remaining,
        )
      else if (item.quantity != null)
        '${t.quantity}: ${item.quantity}',
    ];
    return Padding(
      padding: AppSpacing.cardRow,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(item.name, style: AppTypography.body(weight: FontWeight.w600)),
          for (final fact in facts) Text(fact, style: AppTypography.small()),
          if (item.instructions != null)
            Text(
              '${t.instructions}: ${item.instructions}',
              style: AppTypography.small(),
            ),
        ],
      ),
    );
  }
}

/// `/patient/lab-results`: tests the laboratory has verified and released.
/// The server never sends pending or cancelled tests to a patient.
class LabResultsScreen extends StatefulWidget {
  const LabResultsScreen({super.key});

  @override
  State<LabResultsScreen> createState() => _LabResultsScreenState();
}

class _LabResultsScreenState extends State<LabResultsScreen> {
  late final RecordLoader<List<LabTest>> _loader = RecordLoader(
    AppScope.read(context).patient.labTests,
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
        PageHeader(title: t.patientNavLab, description: t.labIntro),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(title: t.labReleasedOnly, message: t.labNotADiagnosis),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<LabTest>>(
          loader: _loader,
          builder: (context, tests) {
            if (tests.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.flaskConical,
                  title: t.noLabReportsYet,
                  description: t.noLabReportsYetHint,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [for (final test in tests) _LabTestRow(test: test)],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _LabTestRow extends StatelessWidget {
  const _LabTestRow({required this.test});

  final LabTest test;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return InkWell(
      onTap: () => _showLabDetails(context, test),
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    test.name,
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  Text(
                    [
                      formatDay(t, test.releasedAt ?? test.testDate),
                      ?test.hospitalName,
                    ].join(' · '),
                    style: AppTypography.small(),
                  ),
                ],
              ),
            ),
            StatusBadge(status: test.status),
          ],
        ),
      ),
    );
  }
}

Future<void> _showLabDetails(BuildContext context, LabTest test) {
  final t = context.l10n;
  final result = test.result;
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.x4),
        child: HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: test.name,
                icon: LucideIcons.flaskConical,
                trailing: StatusBadge(status: test.status),
              ),
              HmsDividedColumn(
                children: [
                  DetailRow(label: t.orderedBy, value: test.doctorName),
                  DetailRow(label: t.laboratory, value: test.hospitalName),
                  DetailRow(
                    label: t.testDate,
                    value: formatDay(t, test.testDate),
                  ),
                  DetailRow(
                    label: t.releasedOn,
                    value: formatDateTime(t, test.releasedAt),
                  ),
                ],
              ),
              HmsCardHeader(title: t.results),
              if (result == null || result.isEmpty)
                HmsEmptyState(compact: true, title: t.noResultValues)
              else
                HmsDividedColumn(
                  children: [
                    for (final entry in result.values.entries)
                      DetailRow(
                        label: entry.key,
                        value: [
                          entry.value,
                          if (result.flags[entry.key] != null)
                            '(${result.flags[entry.key]})',
                          if (result.referenceRanges[entry.key] != null)
                            '· ${t.referenceRange}: '
                                '${result.referenceRanges[entry.key]}',
                        ].join(' '),
                      ),
                    if (result.text != null)
                      DetailRow(label: t.reportNotes, value: result.text),
                  ],
                ),
            ],
          ),
        ),
      ),
    ),
  );
}
