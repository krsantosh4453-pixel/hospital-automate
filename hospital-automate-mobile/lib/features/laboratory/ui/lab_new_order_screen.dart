import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/record_picker.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/data/doctor_models.dart' show PatientSummary;
import '../../doctor/data/doctor_repository.dart' show labPriorities;
import '../../patient/ui/patient_ui.dart';
import '../data/lab_repository.dart';
import '../data/lab_workflow.dart';
import 'lab_ui.dart';

/// Maximum length of `LabTest.name`.
const _maxTestName = 150;

/// `/laboratory/new`: a walk-in order from the lab desk. Pick the patient,
/// name the test, review, then send; the order exists only once the server
/// answers. Doctors order from the consultation instead (linked to the visit).
class LabNewOrderScreen extends StatefulWidget {
  const LabNewOrderScreen({super.key});

  @override
  State<LabNewOrderScreen> createState() => _LabNewOrderScreenState();
}

class _LabNewOrderScreenState extends State<LabNewOrderScreen> {
  late final _services = AppScope.read(context);
  final _testName = TextEditingController();
  PatientSummary? _patient;
  String _priority = labPriorities.first;
  bool _reviewing = false;
  bool _saving = false;

  /// Set when the last attempt got no answer: the order may exist already.
  bool _maybeCreated = false;
  String? _error;

  @override
  void dispose() {
    _testName.dispose();
    super.dispose();
  }

  String? _validate(AppLocalizations t) {
    if (_patient == null) return t.labChoosePatient;
    final name = _testName.text.trim();
    if (name.isEmpty) return t.labTestNameRequired;
    if (name.length > _maxTestName) return t.labTestNameTooLong(_maxTestName);
    return null;
  }

  void _review() {
    final problem = _validate(context.l10n);
    setState(() {
      _error = problem;
      _reviewing = problem == null;
    });
  }

  Future<void> _submit() async {
    if (_saving) return;
    final t = context.l10n;
    final hospital = _services.session.activeHospitalId;
    final patient = _patient;
    if (hospital == null || patient == null) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final created = await _services.laboratory.createOrder(
        LabOrderDraft(
          hospitalId: hospital,
          patientId: patient.id,
          testName: _testName.text,
          priority: _priority,
        ),
      );
      if (mounted) context.go(LabRoutes.order(created.id));
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _maybeCreated = outcomeUnknown(error);
        _error = _maybeCreated
            ? t.labOrderMaybeCreated
            : labErrorMessage(t, error);
      });
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    if (!mayOrderLabTests(_services.session.state)) {
      return HmsCard(
        child: HmsEmptyState(
          icon: LucideIcons.lock,
          title: t.notEligibleForPage,
          description: t.labOrderNotAllowed,
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.labNewOrder, description: t.labNewOrderIntro),
        const SizedBox(height: AppSpacing.x4),
        if (_error != null) ...[
          HmsAlert(
            tone: _maybeCreated ? AlertTone.warning : AlertTone.danger,
            title: _error!,
            action: _maybeCreated
                ? HmsButton(
                    label: t.labOpenWorklist,
                    surface: HmsSurface.card,
                    onPressed: () => context.go(LabRoutes.worklist),
                  )
                : null,
          ),
          const SizedBox(height: AppSpacing.x4),
        ],
        if (_reviewing) _reviewCard(t) else _formCard(t),
      ],
    );
  }

  Widget _formCard(AppLocalizations t) => HmsCard(
    padding: const EdgeInsets.all(AppSpacing.x4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('1. ${t.patientLabel}', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: AppSpacing.x2),
        RecordPicker<PatientSummary>(
          hint: t.labPatientSearchHint,
          search: _services.laboratory.lookupPatients,
          selected: _patient,
          title: (p) => p.name,
          subtitle: patientSubtitle,
          onSelected: (p) => setState(() => _patient = p),
        ),
        const SizedBox(height: AppSpacing.x4),
        Text('2. ${t.labTestName}', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: AppSpacing.x2),
        Text(t.labCommonTestsNote, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: AppSpacing.x2),
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final name in commonLabTests)
              ActionChip(
                label: Text(name),
                onPressed: () => setState(() => _testName.text = name),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x2),
        HmsTextField(
          key: const Key('lab-order-test-name'),
          label: t.labTestName,
          required: true,
          controller: _testName,
          maxLength: _maxTestName,
        ),
        Text('3. ${t.priority}', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: AppSpacing.x2),
        Wrap(
          spacing: AppSpacing.x2,
          children: [
            for (final p in labPriorities)
              ChoiceChip(
                label: Text(p == 'Urgent' ? t.statusUrgent : t.labPriorityNormal),
                selected: _priority == p,
                onSelected: (_) => setState(() => _priority = p),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsButton(
          key: const Key('lab-order-review'),
          label: t.labReviewOrder,
          surface: HmsSurface.card,
          expand: true,
          onPressed: _review,
        ),
      ],
    ),
  );

  Widget _reviewCard(AppLocalizations t) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(
          title: t.labReviewOrder,
          description: t.labReviewOrderHint,
          icon: LucideIcons.clipboardCheck,
        ),
        HmsDividedColumn(
          children: [
            DetailRow(label: t.patientLabel, value: _patient?.name),
            DetailRow(label: t.patientId, value: _patient?.uhid),
            DetailRow(label: t.labTestName, value: _testName.text.trim()),
            DetailRow(
              label: t.priority,
              value: _priority == 'Urgent' ? t.statusUrgent : t.labPriorityNormal,
            ),
            DetailRow(
              label: t.hospital,
              value: _services.session.state.activeHospital?.name,
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: Wrap(
            alignment: WrapAlignment.end,
            spacing: AppSpacing.x2,
            runSpacing: AppSpacing.x2,
            children: [
              HmsButton(
                label: t.goBack,
                variant: HmsButtonVariant.secondary,
                surface: HmsSurface.card,
                onPressed: _saving
                    ? null
                    : () => setState(() => _reviewing = false),
              ),
              HmsButton(
                key: const Key('lab-order-submit'),
                label: t.labPlaceOrder,
                surface: HmsSurface.card,
                loading: _saving,
                // After an unanswered attempt, check the worklist first.
                onPressed: _saving || _maybeCreated ? null : _submit,
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

/// UHID, age and gender: what tells two same-name patients apart.
String patientSubtitle(PatientSummary p) => [
  ?p.uhid,
  if (p.age != null) '${p.age}',
  ?p.gender,
  ?p.phone,
].join(' · ');
