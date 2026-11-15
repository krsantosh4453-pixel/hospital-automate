import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/clinical_records_screens.dart' show PrescriptionCard;
import '../../patient/ui/patient_ui.dart';
import '../data/doctor_models.dart';
import '../data/doctor_repository.dart';
import 'consultation_sections.dart';
import 'doctor_ui.dart';
import 'patient_records_screens.dart' show LabTestRow;

/// Controllers for one medicine line of the form.
class _LineControllers {
  final name = TextEditingController();
  final dosage = TextEditingController();
  final frequency = TextEditingController();
  final duration = TextEditingController();
  final quantity = TextEditingController(text: '1');
  final instructions = TextEditingController();

  List<TextEditingController> get all => [
    name,
    dosage,
    frequency,
    duration,
    quantity,
    instructions,
  ];

  MedicineLine toLine() => MedicineLine(
    name: name.text,
    dosage: dosage.text,
    frequency: frequency.text,
    duration: duration.text,
    quantity: int.tryParse(quantity.text.trim()) ?? 0,
    instructions: instructions.text,
  );

  void dispose() {
    for (final controller in all) {
      controller.dispose();
    }
  }
}

/// Why the medicine lines cannot be sent, or null (web Prescription.jsx rules).
String? checkLines(AppLocalizations t, List<MedicineLine> lines) {
  if (lines.isEmpty) return t.addOneMedicine;
  for (var i = 0; i < lines.length; i++) {
    if (lines[i].name.trim().isEmpty) return t.medicineNameRequired(i + 1);
    if (lines[i].quantity < 1) return t.medicineQuantityInvalid(i + 1);
  }
  return null;
}

/// Prescriptions of this visit and, while it is open, a new one. The server
/// writes it in the signed-in doctor's name and re-checks medication safety;
/// a high-severity alert needs the doctor's reason. Nothing is suggested.
class PrescriptionSection extends StatefulWidget {
  const PrescriptionSection({super.key, required this.context});

  final ConsultationContext context;

  @override
  State<PrescriptionSection> createState() => _PrescriptionSectionState();
}

class _PrescriptionSectionState extends State<PrescriptionSection> {
  ConsultationContext get _c => widget.context;
  late final RecordLoader<List<Prescription>> _loader = RecordLoader(
    () async => [
      for (final rx in await _c.repository.prescriptions(
        patientId: _c.visit.patientId,
      ))
        if (rx.visitId == _c.visit.id) rx,
    ],
  );
  final List<_LineControllers> _lines = [_LineControllers()];
  final _overrideReason = TextEditingController();
  bool _saving = false;
  String? _error;
  String? _saved;
  // One key per draft, kept when a save fails: if the server did save it and
  // only the answer was lost, the retry gets that prescription back instead
  // of a second one. Cleared once a save succeeds.
  String? _idempotencyKey;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    for (final line in _lines) {
      line.dispose();
    }
    _overrideReason.dispose();
    _loader.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_saving) return;
    final t = context.l10n;
    final lines = [for (final c in _lines) c.toLine()];
    final problem = checkLines(t, lines);
    final hospital = _c.visit.hospitalId;
    final patient = _c.visit.patientId;
    if (problem != null || hospital == null || patient == null) {
      setState(() => _error = problem ?? t.errorUnknown);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
      _saved = null;
    });
    try {
      final alerts = await _c.repository.safetyCheck(
        hospitalId: hospital,
        patientId: patient,
        medicines: [for (final line in lines) line.name],
      );
      if (!mounted) return;
      var reason = '';
      if (alerts.isNotEmpty) {
        final answer = await _reviewAlerts(context, alerts, _overrideReason);
        if (answer == null || !mounted) return;
        reason = answer;
      }
      final created = await _c.repository.createPrescription(
        PrescriptionDraft(
          hospitalId: hospital,
          patientId: patient,
          visitId: _c.visit.id,
          lines: lines,
          overrideReason: reason,
        ),
        idempotencyKey: _idempotencyKey ??= ApiClient.newIdempotencyKey(),
      );
      if (!mounted) return;
      _idempotencyKey = null;
      setState(() {
        for (final line in _lines) {
          line.dispose();
        }
        _lines
          ..clear()
          ..add(_LineControllers());
        _saved = t.prescriptionSaved('${created.id}');
      });
      await _loader.load();
    } catch (error) {
      // The lines stay in the form; nothing typed is lost.
      final keyConflict =
          error is ApiException && error.kind == ApiErrorKind.conflict;
      if (keyConflict) {
        // The key already wrote a prescription with other lines (the first
        // try was saved, then the form was edited). Show what is saved; a new
        // key lets the doctor save the edited lines on purpose.
        _idempotencyKey = null;
        _loader.load();
      }
      if (mounted) {
        setState(
          () => _error = keyConflict
              ? t.prescriptionMaybeSaved
              : clinicalErrorMessage(
                  t,
                  error,
                  fieldLabels: {
                    'items': t.medicines,
                    'safety_override_reason': t.overrideReason,
                    'visit': t.visits,
                  },
                ),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.prescription, icon: LucideIcons.pill),
          RecordSection<List<Prescription>>(
            loader: _loader,
            skeletons: 1,
            builder: (context, rows) => rows.isEmpty
                ? HmsEmptyState(compact: true, title: t.noPrescriptionsForVisit)
                : Padding(
                    padding: const EdgeInsets.all(AppSpacing.x3),
                    child: Column(
                      children: [
                        for (final rx in rows) ...[
                          PrescriptionCard(prescription: rx),
                          const SizedBox(height: AppSpacing.x2),
                        ],
                      ],
                    ),
                  ),
          ),
          if (_c.canWrite) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(AppSpacing.x4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  formError(_error),
                  if (_saved != null) ...[
                    HmsAlert(tone: AlertTone.success, title: _saved!),
                    const SizedBox(height: AppSpacing.x3),
                  ],
                  Text(
                    t.prescriptionFreeTextNote,
                    style: AppTypography.caption(),
                  ),
                  const SizedBox(height: AppSpacing.x3),
                  for (var i = 0; i < _lines.length; i++) _lineForm(t, i),
                  HmsButton(
                    label: t.addMedicine,
                    icon: LucideIcons.plus,
                    surface: HmsSurface.card,
                    variant: HmsButtonVariant.secondary,
                    onPressed: _saving
                        ? null
                        : () => setState(() => _lines.add(_LineControllers())),
                  ),
                  const SizedBox(height: AppSpacing.x3),
                  HmsButton(
                    key: const Key('save-prescription'),
                    label: t.checkAndSavePrescription,
                    surface: HmsSurface.card,
                    loading: _saving,
                    expand: true,
                    onPressed: _saving ? null : _submit,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _lineForm(AppLocalizations t, int index) {
    final line = _lines[index];
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.x3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  t.medicineNumber(index + 1),
                  style: AppTypography.small(weight: FontWeight.w600),
                ),
              ),
              if (_lines.length > 1)
                IconButton(
                  tooltip: t.removeMedicine,
                  icon: const Icon(LucideIcons.trash2, size: 18),
                  onPressed: _saving
                      ? null
                      : () => setState(() => _lines.removeAt(index).dispose()),
                ),
            ],
          ),
          ClinicalField(
            key: ValueKey('medicine-name-$index'),
            label: t.medicineName,
            controller: line.name,
            enabled: !_saving,
          ),
          ClinicalField(
            label: t.dosage,
            controller: line.dosage,
            enabled: !_saving,
          ),
          ClinicalField(
            label: t.frequency,
            controller: line.frequency,
            enabled: !_saving,
          ),
          ClinicalField(
            label: t.duration,
            controller: line.duration,
            enabled: !_saving,
          ),
          ClinicalField(
            key: ValueKey('medicine-quantity-$index'),
            label: t.quantity,
            controller: line.quantity,
            numeric: true,
            enabled: !_saving,
          ),
          ClinicalField(
            label: t.instructions,
            controller: line.instructions,
            enabled: !_saving,
          ),
        ],
      ),
    );
  }
}

/// Shows the safety alerts. Returns null to go back, '' to continue (no
/// high alert) or the doctor's override reason (high alert). [reason] is
/// owned by the caller: the sheet still uses it while it slides away.
Future<String?> _reviewAlerts(
  BuildContext context,
  List<SafetyAlert> alerts,
  TextEditingController reason,
) {
  final t = context.l10n;
  final blocking = alerts.any((a) => a.isBlocking);
  reason.clear();
  return showHmsModal<String>(
    context,
    title: t.medicationSafetyAlerts,
    // The alerts and the reason scroll; the buttons stay in the footer, so
    // they are always reachable however long the alerts are.
    body: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final alert in alerts) ...[
          HmsAlert(
            tone: alert.isBlocking ? AlertTone.danger : AlertTone.warning,
            title:
                '${alert.severity.toUpperCase()} · ${alert.medicines.join(', ')}',
            message: alert.message,
          ),
          const SizedBox(height: AppSpacing.x2),
        ],
        if (blocking)
          TextField(
            key: const Key('override-reason'),
            controller: reason,
            maxLines: 3,
            decoration: InputDecoration(
              labelText: t.overrideReason,
              helperText: t.overrideReasonHint(minOverrideReasonLength),
            ),
          ),
      ],
    ),
    actions: (dialogContext) => [
      HmsButton(
        label: t.goBack,
        variant: HmsButtonVariant.secondary,
        surface: HmsSurface.card,
        onPressed: () => Navigator.of(dialogContext).pop(),
      ),
      ValueListenableBuilder<TextEditingValue>(
        valueListenable: reason,
        builder: (_, value, _) => HmsButton(
          key: const Key('confirm-prescription'),
          label: blocking ? t.prescribeAnyway : t.continueSaving,
          surface: HmsSurface.card,
          variant: blocking
              ? HmsButtonVariant.danger
              : HmsButtonVariant.primary,
          onPressed:
              blocking && value.text.trim().length < minOverrideReasonLength
              ? null
              : () =>
                    Navigator.of(dialogContext)
                        .pop(blocking ? value.text.trim() : ''),
        ),
      ),
    ],
  );
}

/// Lab tests ordered on this visit and, while it is open, a new order. The
/// laboratory releases results; the doctor never changes them.
class LabOrderSection extends StatefulWidget {
  const LabOrderSection({super.key, required this.context});

  final ConsultationContext context;

  @override
  State<LabOrderSection> createState() => _LabOrderSectionState();
}

class _LabOrderSectionState extends State<LabOrderSection> {
  ConsultationContext get _c => widget.context;
  late final RecordLoader<List<LabTest>> _loader = RecordLoader(
    () async => [
      for (final test in await _c.repository.labTests(
        patientId: _c.visit.patientId,
      ))
        if (test.visitId == _c.visit.id) test,
    ],
  );
  final _name = TextEditingController();
  String _priority = labPriorities.first;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _name.dispose();
    _loader.dispose();
    super.dispose();
  }

  Future<void> _order() async {
    if (_saving) return;
    final t = context.l10n;
    final doctor = _c.doctor;
    final hospital = _c.visit.hospitalId;
    final patient = _c.visit.patientId;
    if (_name.text.trim().isEmpty) {
      setState(() => _error = t.labTestNameRequired);
      return;
    }
    if (doctor == null || hospital == null || patient == null) {
      setState(() => _error = t.doctorProfileMissing);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await _c.repository.orderLabTest(
        hospitalId: hospital,
        patientId: patient,
        visitId: _c.visit.id,
        doctorId: doctor.id,
        name: _name.text,
        priority: _priority,
      );
      _name.clear();
      await _loader.load();
    } catch (error) {
      if (mounted) setState(() => _error = clinicalErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.labOrders, icon: LucideIcons.flaskConical),
          RecordSection<List<LabTest>>(
            loader: _loader,
            skeletons: 1,
            builder: (context, tests) => tests.isEmpty
                ? HmsEmptyState(compact: true, title: t.noLabOrdersForVisit)
                : HmsDividedColumn(
                    children: [
                      for (final test in tests) LabTestRow(test: test),
                    ],
                  ),
          ),
          if (_c.canWrite) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(AppSpacing.x4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  formError(_error),
                  ClinicalField(
                    key: const Key('lab-test-name'),
                    label: t.labTestName,
                    controller: _name,
                    enabled: !_saving,
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: _priority,
                    isExpanded: true,
                    decoration: InputDecoration(labelText: t.priority),
                    items: [
                      for (final p in labPriorities)
                        DropdownMenuItem(value: p, child: Text(p)),
                    ],
                    onChanged: _saving
                        ? null
                        : (p) => setState(() => _priority = p ?? _priority),
                  ),
                  const SizedBox(height: AppSpacing.x3),
                  HmsButton(
                    key: const Key('order-lab'),
                    label: t.orderLabTest,
                    surface: HmsSurface.card,
                    loading: _saving,
                    expand: true,
                    onPressed: _saving ? null : _order,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
