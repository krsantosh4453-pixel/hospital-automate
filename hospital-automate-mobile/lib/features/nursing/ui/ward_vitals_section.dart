import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/data/doctor_models.dart';
import '../../doctor/ui/consultation_sections.dart'
    show ClinicalField, formError, vitalErrorText, vitalLabel;
import '../../doctor/ui/doctor_ui.dart' show clinicalErrorMessage;
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/nursing_models.dart';
import 'nursing_ui.dart';
import 'ward_patient_screen.dart';
import 'ward_widgets.dart';

/// Where a reading is recorded: on the patient's stay (a nursing
/// assessment, as the web does) or on an open OPD visit (`clinical/vitals/`).
@immutable
sealed class VitalsTarget {
  const VitalsTarget();

  List<VitalField> get fields;
}

class AdmissionTarget extends VitalsTarget {
  const AdmissionTarget(this.admission);

  final Admission admission;

  @override
  List<VitalField> get fields => wardVitalFields;

  @override
  bool operator ==(Object other) =>
      other is AdmissionTarget && other.admission.id == admission.id;

  @override
  int get hashCode => Object.hash('admission', admission.id);
}

class VisitTarget extends VitalsTarget {
  const VisitTarget(this.visit);

  final Visit visit;

  @override
  List<VitalField> get fields => VitalField.values;

  @override
  bool operator ==(Object other) =>
      other is VisitTarget && other.visit.id == visit.id;

  @override
  int get hashCode => Object.hash('visit', visit.id);
}

/// A saved reading, as shown in the history.
typedef VitalsEntry = ({DateTime? at, String? by, String values});

/// Why a reading cannot be sent, or null. Checks each value with the
/// server's own limits ([VitalField.check]) and that blood pressure, on a
/// stay, has both numbers.
({Map<VitalField, VitalError> fields, bool bpIncomplete, bool empty})
checkVitals(VitalsTarget target, Map<VitalField, String> values) {
  final errors = {
    for (final field in target.fields)
      field: ?field.check(values[field] ?? ''),
  };
  final filled = [
    for (final field in target.fields)
      if ((values[field] ?? '').trim().isNotEmpty) field,
  ];
  final bpIncomplete =
      target is AdmissionTarget &&
      filled.contains(VitalField.systolicBp) !=
          filled.contains(VitalField.diastolicBp);
  return (fields: errors, bpIncomplete: bpIncomplete, empty: filled.isEmpty);
}

/// Vitals of the patient and a form for a new reading. A new reading
/// never replaces an earlier one; nothing is edited or deleted here.
class WardVitalsSection extends StatefulWidget {
  const WardVitalsSection({super.key, required this.ward});

  final WardContext ward;

  @override
  State<WardVitalsSection> createState() => _WardVitalsSectionState();
}

class _WardVitalsSectionState extends State<WardVitalsSection> {
  WardContext get _w => widget.ward;
  late final List<VitalsTarget> _targets = [
    for (final a in _w.admissions) AdmissionTarget(a),
    for (final v in _w.openVisits) VisitTarget(v),
  ];
  late VitalsTarget? _target = _targets.isEmpty ? null : _targets.first;
  late final RecordLoader<List<VitalsEntry>> _loader = RecordLoader(_history);
  final Map<VitalField, TextEditingController> _fields = {
    for (final field in VitalField.values) field: TextEditingController(),
  };
  final Map<VitalField, VitalError> _errors = {};
  bool _saving = false;
  String? _error;
  String? _saved;

  Future<List<VitalsEntry>> _history() async {
    final t = context.l10n;
    final target = _target;
    switch (target) {
      case null:
        return const [];
      case AdmissionTarget(:final admission):
        final rows = await _w.repository.assessments(_w.patient.id);
        return [
          for (final a in rows)
            if (a.hasVitals && a.admissionId == admission.id)
              (
                at: a.assessedAt,
                by: a.nurseName,
                values: [
                  for (final e in a.vitals.entries)
                    '${wardVitalLabel(t, e.key)}: ${e.value}',
                ].join(' · '),
              ),
        ];
      case VisitTarget(:final visit):
        final rows = await _w.repository.visitVitals(visit.id);
        return [
          for (final r in rows)
            (
              at: r.recordedAt,
              by: r.recordedByName,
              values: [
                for (final e in r.values.entries)
                  '${vitalLabel(t, e.key)}: ${e.value}',
              ].join(' · '),
            ),
        ];
    }
  }

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    for (final c in _fields.values) {
      c.dispose();
    }
    _loader.dispose();
    super.dispose();
  }

  void _select(VitalsTarget target) {
    if (_saving || target == _target) return;
    setState(() {
      _target = target;
      _errors.clear();
      _error = null;
      _saved = null;
    });
    _loader.load();
  }

  Future<void> _save() async {
    final target = _target;
    if (_saving || target == null) return;
    final t = context.l10n;
    final values = {
      for (final field in target.fields)
        if (_fields[field]!.text.trim().isNotEmpty)
          field: _fields[field]!.text.trim(),
    };
    final check = checkVitals(target, values);
    setState(() {
      _errors
        ..clear()
        ..addAll(check.fields);
      _saved = null;
      _error = check.fields.isNotEmpty
          ? t.fixHighlightedFields
          : check.bpIncomplete
          ? t.bpNeedsBoth
          : check.empty
          ? t.enterAtLeastOneVital
          : null;
    });
    if (_error != null) return;
    setState(() => _saving = true);
    try {
      switch (target) {
        case AdmissionTarget(:final admission):
          await _w.repository.addWardVitals(
            hospitalId: _w.hospitalId,
            patientId: _w.patient.id,
            admissionId: admission.id,
            vitals: wardVitalsJson(values)!,
          );
        case VisitTarget(:final visit):
          await _w.repository.addVisitVitals(visit.id, values);
      }
      for (final c in _fields.values) {
        c.clear();
      }
      if (mounted) setState(() => _saved = t.vitalsSaved);
      await _loader.load();
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = clinicalErrorMessage(
            t,
            error,
            fieldLabels: {
              for (final f in VitalField.values) f.key: vitalLabel(t, f),
              'vitals': t.vitals,
            },
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String _targetLabel(AppLocalizations t, VitalsTarget target) =>
      switch (target) {
        AdmissionTarget(:final admission) => [
          t.onThisStay,
          ?admission.wardName,
          if (admission.bedNumber != null) t.bedNumber(admission.bedNumber!),
        ].join(' · '),
        VisitTarget(:final visit) => t.opdVisitOn(
          formatDay(t, visit.visitDate),
        ),
      };

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final target = _target;
    return WardSectionCard(
      title: t.vitals,
      icon: LucideIcons.activity,
      list: target == null
          ? HmsEmptyState(compact: true, title: t.noEncounterForVitals)
          : RecordSection<List<VitalsEntry>>(
              loader: _loader,
              skeletons: 1,
              builder: (context, rows) => rows.isEmpty
                  ? HmsEmptyState(compact: true, title: t.noReadingsYet)
                  : HmsDividedColumn(
                      children: [
                        for (final row in rows)
                          WardRecordRow(
                            heading: [formatDateTime(t, row.at), ?row.by]
                                .join(' · '),
                            body: row.values,
                          ),
                      ],
                    ),
            ),
      form: target == null
          ? null
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_targets.length > 1) ...[
                  Text(t.recordOn, style: AppTypography.small()),
                  const SizedBox(height: AppSpacing.x2),
                  Wrap(
                    spacing: AppSpacing.x2,
                    runSpacing: AppSpacing.x2,
                    children: [
                      for (final option in _targets)
                        ChoiceChip(
                          label: Text(_targetLabel(t, option)),
                          selected: option == target,
                          onSelected: _saving ? null : (_) => _select(option),
                        ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.x3),
                ] else ...[
                  Text(
                    _targetLabel(t, target),
                    style: AppTypography.small(weight: FontWeight.w600),
                  ),
                  const SizedBox(height: AppSpacing.x3),
                ],
                formError(_error),
                if (_saved != null) ...[
                  HmsAlert(tone: AlertTone.success, title: _saved!),
                  const SizedBox(height: AppSpacing.x3),
                ],
                for (final field in target.fields)
                  ClinicalField(
                    key: ValueKey('ward-vital-${field.key}'),
                    label: vitalLabel(t, field),
                    controller: _fields[field]!,
                    numeric: true,
                    enabled: !_saving,
                    errorText: _errors[field] == null
                        ? null
                        : vitalErrorText(t, _errors[field]!),
                  ),
                HmsButton(
                  key: const Key('save-ward-vitals'),
                  label: t.saveVitals,
                  surface: HmsSurface.card,
                  loading: _saving,
                  expand: true,
                  onPressed: _saving ? null : _save,
                ),
              ],
            ),
    );
  }
}
