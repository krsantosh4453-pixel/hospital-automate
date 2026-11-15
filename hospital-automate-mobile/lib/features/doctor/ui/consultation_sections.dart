import 'dart:async';

import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/doctor_models.dart';
import '../data/doctor_repository.dart';
import 'doctor_ui.dart';

/// What every consultation section needs to know about the visit.
class ConsultationContext {
  const ConsultationContext({
    required this.repository,
    required this.visit,
    required this.userId,
    required this.canWrite,
    this.doctor,
  });

  final DoctorRepository repository;
  final Visit visit;

  /// The signed-in user (author of drafts they may sign).
  final int? userId;

  /// The visit is open and this doctor's own (or unassigned).
  final bool canWrite;
  final DoctorProfile? doctor;
}

/// A card with a title, a list and (when allowed) a form below it.
class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.list,
    this.form,
  });

  final String title;
  final IconData icon;
  final Widget list;
  final Widget? form;

  @override
  Widget build(BuildContext context) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(title: title, icon: icon),
        list,
        if (form != null) ...[
          const Divider(height: 1),
          Padding(padding: const EdgeInsets.all(AppSpacing.x4), child: form),
        ],
      ],
    ),
  );
}

/// Labelled text input used by the clinical forms.
class ClinicalField extends StatelessWidget {
  const ClinicalField({
    super.key,
    required this.label,
    required this.controller,
    this.errorText,
    this.numeric = false,
    this.maxLines = 1,
    this.enabled = true,
    this.onChanged,
  });

  final String label;
  final TextEditingController controller;
  final String? errorText;
  final bool numeric;
  final int maxLines;
  final bool enabled;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.x3),
    child: TextField(
      controller: controller,
      enabled: enabled,
      maxLines: maxLines,
      keyboardType: numeric
          ? const TextInputType.numberWithOptions(decimal: true)
          : TextInputType.multiline,
      decoration: InputDecoration(labelText: label, errorText: errorText),
      onChanged: onChanged,
    ),
  );
}

/// Shows [message] in a danger alert above a form, when there is one.
Widget formError(String? message) => message == null
    ? const SizedBox.shrink()
    : Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.x3),
        child: HmsAlert(tone: AlertTone.danger, title: message),
      );

String vitalLabel(AppLocalizations t, VitalField field) =>
    '${switch (field) {
      VitalField.systolicBp => t.vitalSystolic,
      VitalField.diastolicBp => t.vitalDiastolic,
      VitalField.heartRate => t.vitalPulse,
      VitalField.respiratoryRate => t.vitalRespiratoryRate,
      VitalField.temperature => t.vitalTemperature,
      VitalField.spo2 => t.vitalSpo2,
      VitalField.weight => t.vitalWeight,
      VitalField.height => t.vitalHeight,
      VitalField.bloodSugar => t.vitalBloodSugar,
      VitalField.painScore => t.vitalPainScore,
    }} (${field.unit})';

String vitalErrorText(AppLocalizations t, VitalError error) => switch (error) {
  VitalError.notANumber => t.vitalNotANumber,
  VitalError.negative => t.vitalNegative,
  VitalError.wholeNumber => t.vitalWholeNumber,
  VitalError.tooPrecise => t.vitalTooPrecise,
  VitalError.tooHigh => t.vitalTooHigh,
};

/// Vitals of the visit and, while it is open, a form for a new reading.
/// A new reading never replaces an earlier one.
class VitalsSection extends StatefulWidget {
  const VitalsSection({super.key, required this.context});

  final ConsultationContext context;

  @override
  State<VitalsSection> createState() => _VitalsSectionState();
}

class _VitalsSectionState extends State<VitalsSection> {
  ConsultationContext get _c => widget.context;
  late final RecordLoader<List<VitalReading>> _loader = RecordLoader(
    () => _c.repository.vitals(_c.visit.id),
  );
  final Map<VitalField, TextEditingController> _fields = {
    for (final field in VitalField.values) field: TextEditingController(),
  };
  final _comments = TextEditingController();
  final Map<VitalField, VitalError> _errors = {};
  bool _saving = false;
  String? _error;
  String? _saved;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    _comments.dispose();
    _loader.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    final t = context.l10n;
    final errors = {
      for (final entry in _fields.entries)
        entry.key: ?entry.key.check(entry.value.text),
    };
    final values = {
      for (final entry in _fields.entries)
        if (entry.value.text.trim().isNotEmpty)
          entry.key: entry.value.text.trim(),
    };
    setState(() {
      _errors
        ..clear()
        ..addAll(errors);
      _saved = null;
      _error = errors.isNotEmpty
          ? t.fixHighlightedFields
          : (values.isEmpty ? t.enterAtLeastOneVital : null);
    });
    if (_error != null) return;
    setState(() => _saving = true);
    try {
      await _c.repository.addVitals(
        _c.visit.id,
        values,
        comments: _comments.text,
      );
      for (final controller in _fields.values) {
        controller.clear();
      }
      _comments.clear();
      if (mounted) setState(() => _saved = t.vitalsSaved);
      await _loader.load();
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = clinicalErrorMessage(
            t,
            error,
            fieldLabels: {
              for (final field in VitalField.values)
                field.key: vitalLabel(t, field),
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
    return _SectionCard(
      title: t.vitals,
      icon: LucideIcons.heartPulse,
      list: RecordSection<List<VitalReading>>(
        loader: _loader,
        skeletons: 1,
        builder: (context, readings) => readings.isEmpty
            ? HmsEmptyState(compact: true, title: t.noVitalsYet)
            : HmsDividedColumn(
                children: [
                  for (final reading in readings)
                    Padding(
                      padding: AppSpacing.cardRow,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            [
                              formatDateTime(t, reading.recordedAt),
                              ?reading.recordedByName,
                            ].join(' · '),
                            style: AppTypography.caption(),
                          ),
                          Text(
                            [
                              for (final entry in reading.values.entries)
                                '${vitalLabel(t, entry.key)}: ${entry.value}',
                              if (reading.bmi != null)
                                '${t.bmi}: ${reading.bmi}',
                            ].join(' · '),
                            style: AppTypography.small(),
                          ),
                          if (reading.comments != null)
                            Text(
                              reading.comments!,
                              style: AppTypography.small(),
                            ),
                        ],
                      ),
                    ),
                ],
              ),
      ),
      form: !_c.canWrite
          ? null
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                formError(_error),
                if (_saved != null) ...[
                  HmsAlert(tone: AlertTone.success, title: _saved!),
                  const SizedBox(height: AppSpacing.x3),
                ],
                for (final field in VitalField.values)
                  ClinicalField(
                    key: ValueKey('vital-${field.key}'),
                    label: vitalLabel(t, field),
                    controller: _fields[field]!,
                    numeric: true,
                    enabled: !_saving,
                    errorText: _errors[field] == null
                        ? null
                        : vitalErrorText(t, _errors[field]!),
                  ),
                ClinicalField(
                  label: t.comments,
                  controller: _comments,
                  maxLines: 2,
                  enabled: !_saving,
                ),
                Text(t.bmiByServer, style: AppTypography.caption()),
                const SizedBox(height: AppSpacing.x3),
                HmsButton(
                  key: const Key('save-vitals'),
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

/// Confirms signing: a signed record is final (corrections are new records).
Future<bool> confirmSign(BuildContext context) {
  final t = context.l10n;
  return showHmsConfirm(
    context,
    title: t.signRecordTitle,
    message: t.signRecordBody,
    confirmLabel: t.signRecord,
  );
}

/// Diagnoses of the visit: ICD-10 suggestions from the server's terminology,
/// drafts the author may sign, and signed ones that no longer change.
class DiagnosisSection extends StatefulWidget {
  const DiagnosisSection({super.key, required this.context});

  final ConsultationContext context;

  @override
  State<DiagnosisSection> createState() => _DiagnosisSectionState();
}

class _DiagnosisSectionState extends State<DiagnosisSection> {
  ConsultationContext get _c => widget.context;
  late final RecordLoader<List<DiagnosisRecord>> _loader = RecordLoader(
    () => _c.repository.diagnoses(_c.visit.id),
  );
  final _name = TextEditingController();
  final _icdQuery = TextEditingController();
  final _remarks = TextEditingController();
  String _type = diagnosisTypes.first;
  Icd10Code? _code;
  List<Icd10Code> _suggestions = const [];
  Timer? _debounce;
  final Set<int> _signing = {};
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _name.dispose();
    _icdQuery.dispose();
    _remarks.dispose();
    _loader.dispose();
    super.dispose();
  }

  void _searchIcd(String text) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () async {
      final query = text.trim();
      if (query.length < 2) {
        if (mounted) setState(() => _suggestions = const []);
        return;
      }
      try {
        final codes = await _c.repository.icd10(query);
        if (mounted && _icdQuery.text.trim() == query) {
          setState(() => _suggestions = codes);
        }
      } catch (_) {
        // Suggestions are optional: the doctor can still type the diagnosis.
        if (mounted) setState(() => _suggestions = const []);
      }
    });
  }

  void _pick(Icd10Code code) => setState(() {
    _code = code;
    _suggestions = const [];
    _icdQuery.text = '${code.code} — ${code.description}';
    if (_name.text.trim().isEmpty) _name.text = code.description;
  });

  Future<void> _save() async {
    if (_saving) return;
    final t = context.l10n;
    if (_name.text.trim().isEmpty) {
      setState(() => _error = t.diagnosisNameRequired);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await _c.repository.addDiagnosis(
        visitId: _c.visit.id,
        name: _name.text,
        icd10Code: _code?.code,
        type: _type,
        remarks: _remarks.text,
      );
      _name.clear();
      _icdQuery.clear();
      _remarks.clear();
      _code = null;
      await _loader.load();
    } catch (error) {
      if (mounted) setState(() => _error = clinicalErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _sign(DiagnosisRecord record) async {
    if (_signing.contains(record.id) ||
        !await confirmSign(context) ||
        !mounted) {
      return;
    }
    setState(() => _signing.add(record.id));
    try {
      await _c.repository.signDiagnosis(record.id);
      await _loader.load();
    } catch (error) {
      if (mounted) {
        setState(() => _error = clinicalErrorMessage(context.l10n, error));
      }
    } finally {
      if (mounted) setState(() => _signing.remove(record.id));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return _SectionCard(
      title: t.diagnoses,
      icon: LucideIcons.clipboardList,
      list: RecordSection<List<DiagnosisRecord>>(
        loader: _loader,
        skeletons: 1,
        builder: (context, rows) => rows.isEmpty
            ? HmsEmptyState(compact: true, title: t.noDiagnosesYet)
            : HmsDividedColumn(
                children: [
                  for (final d in rows)
                    Padding(
                      padding: AppSpacing.cardRow,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            [?d.icd10Code, d.name].join(' · '),
                            style: AppTypography.body(weight: FontWeight.w600),
                          ),
                          Text(
                            [?d.diagnosisType, ?d.remarks].join(' · '),
                            style: AppTypography.small(),
                          ),
                          _SignState(
                            signedAt: d.signedAt,
                            canSign:
                                !d.isSigned &&
                                d.recordedBy == _c.userId &&
                                _c.userId != null,
                            busy: _signing.contains(d.id),
                            onSign: () => _sign(d),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
      ),
      form: !_c.canWrite
          ? null
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                formError(_error),
                ClinicalField(
                  label: t.icd10Search,
                  controller: _icdQuery,
                  enabled: !_saving,
                  onChanged: (text) {
                    _code = null;
                    _searchIcd(text);
                  },
                ),
                for (final code in _suggestions)
                  ListTile(
                    dense: true,
                    title: Text('${code.code} — ${code.description}'),
                    onTap: () => _pick(code),
                  ),
                ClinicalField(
                  key: const Key('diagnosis-name'),
                  label: t.diagnosisName,
                  controller: _name,
                  enabled: !_saving,
                ),
                DropdownButtonFormField<String>(
                  initialValue: _type,
                  isExpanded: true,
                  decoration: InputDecoration(labelText: t.diagnosisType),
                  items: [
                    for (final type in diagnosisTypes)
                      DropdownMenuItem(value: type, child: Text(type)),
                  ],
                  onChanged: _saving
                      ? null
                      : (type) => setState(() => _type = type ?? _type),
                ),
                const SizedBox(height: AppSpacing.x3),
                ClinicalField(
                  label: t.remarks,
                  controller: _remarks,
                  maxLines: 2,
                  enabled: !_saving,
                ),
                HmsButton(
                  key: const Key('save-diagnosis'),
                  label: t.addDiagnosis,
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

/// "Draft" with a Sign button for the author, or "Signed on …".
class _SignState extends StatelessWidget {
  const _SignState({
    required this.signedAt,
    required this.canSign,
    required this.busy,
    required this.onSign,
  });

  final DateTime? signedAt;
  final bool canSign;
  final bool busy;
  final VoidCallback onSign;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    if (signedAt != null) {
      return Text(
        t.signedOn(formatDateTime(t, signedAt)),
        style: AppTypography.caption(),
      );
    }
    return Row(
      children: [
        Text(t.draft, style: AppTypography.caption(weight: FontWeight.w600)),
        const SizedBox(width: AppSpacing.x2),
        if (canSign)
          HmsButton(
            label: t.signRecord,
            size: HmsButtonSize.small,
            surface: HmsSurface.card,
            variant: HmsButtonVariant.secondary,
            loading: busy,
            onPressed: busy ? null : onSign,
          ),
      ],
    );
  }
}

String noteSectionLabel(AppLocalizations t, NoteSection section) =>
    switch (section) {
      NoteSection.chiefComplaint => t.noteChiefComplaint,
      NoteSection.presentIllness => t.notePresentIllness,
      NoteSection.pastHistory => t.notePastHistory,
      NoteSection.currentMedications => t.noteCurrentMedications,
      NoteSection.examination => t.noteExamination,
      NoteSection.assessment => t.noteAssessment,
      NoteSection.plan => t.notePlan,
      NoteSection.other => t.noteOther,
    };

/// Structured clinical notes of the visit (ClinicalNote.SECTIONS). A new
/// note is a draft; only its author signs it, and signing is final.
class NotesSection extends StatefulWidget {
  const NotesSection({super.key, required this.context});

  final ConsultationContext context;

  @override
  State<NotesSection> createState() => _NotesSectionState();
}

class _NotesSectionState extends State<NotesSection> {
  ConsultationContext get _c => widget.context;
  late final RecordLoader<List<ClinicalNoteRecord>> _loader = RecordLoader(
    () => _c.repository.notes(_c.visit.id),
  );
  final Map<NoteSection, TextEditingController> _fields = {
    for (final section in NoteSection.values) section: TextEditingController(),
  };
  final Set<int> _signing = {};
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    _loader.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    final t = context.l10n;
    final sections = {
      for (final entry in _fields.entries)
        if (entry.value.text.trim().isNotEmpty) entry.key: entry.value.text,
    };
    if (sections.isEmpty) {
      setState(() => _error = t.noteNeedsOneSection);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await _c.repository.addNote(_c.visit.id, sections);
      for (final controller in _fields.values) {
        controller.clear();
      }
      await _loader.load();
    } catch (error) {
      // The text stays in the form so nothing typed is lost.
      if (mounted) setState(() => _error = clinicalErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _sign(ClinicalNoteRecord note) async {
    if (_signing.contains(note.id) || !await confirmSign(context) || !mounted) {
      return;
    }
    setState(() => _signing.add(note.id));
    try {
      await _c.repository.signNote(note.id);
      await _loader.load();
    } catch (error) {
      if (mounted) {
        setState(() => _error = clinicalErrorMessage(context.l10n, error));
      }
    } finally {
      if (mounted) setState(() => _signing.remove(note.id));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    // A note's author is the Doctor profile; the doctor may sign their own.
    final ownDoctorId = _c.doctor?.id;
    return _SectionCard(
      title: t.clinicalNotes,
      icon: LucideIcons.notebookPen,
      list: RecordSection<List<ClinicalNoteRecord>>(
        loader: _loader,
        skeletons: 1,
        builder: (context, notes) => notes.isEmpty
            ? HmsEmptyState(compact: true, title: t.noNotesYet)
            : HmsDividedColumn(
                children: [
                  for (final note in notes)
                    Padding(
                      padding: AppSpacing.cardRow,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            formatDateTime(t, note.createdAt),
                            style: AppTypography.caption(),
                          ),
                          for (final entry in note.sections.entries)
                            Text(
                              '${noteSectionLabel(t, entry.key)}: ${entry.value}',
                              style: AppTypography.small(),
                            ),
                          _SignState(
                            signedAt: note.signedAt,
                            canSign:
                                !note.isSigned &&
                                ownDoctorId != null &&
                                note.doctorId == ownDoctorId,
                            busy: _signing.contains(note.id),
                            onSign: () => _sign(note),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
      ),
      form: !_c.canWrite
          ? null
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                formError(_error),
                for (final section in NoteSection.values)
                  ClinicalField(
                    key: ValueKey('note-${section.key}'),
                    label: noteSectionLabel(t, section),
                    controller: _fields[section]!,
                    maxLines: 3,
                    enabled: !_saving,
                  ),
                HmsButton(
                  key: const Key('save-note'),
                  label: t.saveNoteDraft,
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
