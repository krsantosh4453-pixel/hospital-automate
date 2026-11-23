import 'package:flutter/material.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/hms_search_field.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/data/doctor_models.dart' show PatientSummary;
import '../../doctor/ui/consultation_sections.dart' show ClinicalField;
import '../../operations/ops_ui.dart';
import '../data/emergency_models.dart';
import '../data/emergency_repository.dart';
import 'emergency_ui.dart';

/// Runs [submit] once at a time and keeps its failure for the form.
/// The sheet closes with `true` only after the server confirmed the write.
mixin ErSubmitOnce<T extends StatefulWidget> on State<T> {
  bool busy = false;
  String? failure;

  Map<String, String> fieldLabels(AppLocalizations t) => {
    'patient': t.patientLabel,
    'triage_level': t.erTriageLevel,
    'chief_complaint': t.erChiefComplaint,
    'pain_score': t.erPainScore,
    'glasgow_coma_scale': t.erGcs,
    'doctor_id': t.erAttendingDoctor,
    'note': t.erNote,
  };

  Future<void> run(Future<void> Function() submit) async {
    if (busy) return;
    setState(() {
      busy = true;
      failure = null;
    });
    try {
      await submit();
      if (mounted) Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) return;
      final t = context.l10n;
      setState(() {
        busy = false;
        failure = stepErrorMessage(t, error, fieldLabels: fieldLabels(t));
      });
    }
  }

  Widget submitRow(
    String label,
    VoidCallback? onPressed, {
    bool danger = false,
  }) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      if (failure != null) ...[
        HmsAlert(tone: AlertTone.danger, title: failure!),
        const SizedBox(height: AppSpacing.x3),
      ],
      HmsButton(
        label: label,
        loading: busy,
        expand: true,
        surface: HmsSurface.card,
        variant: danger ? HmsButtonVariant.danger : HmsButtonVariant.primary,
        onPressed: busy ? null : onPressed,
      ),
    ],
  );
}

Future<bool> showErSheet(
  BuildContext context,
  String title,
  Widget body,
) async => await showHmsModal<bool>(context, title: title, body: body) ?? false;

/// A whole number of zero or more, or null when blank; [invalid] otherwise.
int? _wholeNumber(String text, {required void Function() invalid}) {
  final value = text.trim();
  if (value.isEmpty) return null;
  final number = int.tryParse(value);
  if (number == null || number < 0) invalid();
  return number;
}

Future<bool> showRegisterErSheet(
  BuildContext context,
  EmergencyRepository repository,
) => showErSheet(
  context,
  context.l10n.erRegisterPatient,
  _RegisterBody(repository: repository),
);

class _RegisterBody extends StatefulWidget {
  const _RegisterBody({required this.repository});

  final EmergencyRepository repository;

  @override
  State<_RegisterBody> createState() => _RegisterBodyState();
}

class _RegisterBodyState extends State<_RegisterBody>
    with ErSubmitOnce<_RegisterBody> {
  final _remarks = TextEditingController();
  String _query = '';
  List<PatientSummary>? _matches;
  Object? _searchError;
  bool _searching = false;
  PatientSummary? _patient;
  String? _level;

  @override
  void dispose() {
    _remarks.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final query = _query.trim();
    if (query.isEmpty || _searching) return;
    setState(() {
      _searching = true;
      _searchError = null;
    });
    try {
      final rows = await widget.repository.searchPatients(query);
      if (mounted) setState(() => _matches = rows);
    } catch (error) {
      if (mounted) setState(() => _searchError = error);
    }
    if (mounted) setState(() => _searching = false);
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final patient = _patient;
    final level = _level;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsSearchField(
          hint: t.erSearchPatient,
          surface: HmsSurface.card,
          onChanged: (text) => _query = text,
          onSubmitted: (_) => _search(),
        ),
        const SizedBox(height: AppSpacing.x2),
        HmsButton(
          label: t.opsSearch,
          variant: HmsButtonVariant.secondary,
          surface: HmsSurface.card,
          loading: _searching,
          onPressed: _searching || busy ? null : _search,
        ),
        if (_searchError != null)
          Text(apiErrorMessage(t, _searchError!), style: AppTypography.small()),
        if (_matches != null && _matches!.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.x2),
            child: Text(t.erNoPatientMatch, style: AppTypography.small()),
          ),
        for (final match in _matches ?? const <PatientSummary>[])
          ListTile(
            key: ValueKey('er-patient-${match.id}'),
            dense: true,
            selected: match.id == patient?.id,
            title: Text(match.name),
            subtitle: Text([?match.uhid, ?match.gender].join(' · ')),
            onTap: busy ? null : () => setState(() => _patient = match),
          ),
        const SizedBox(height: AppSpacing.x3),
        DropdownButtonFormField<String>(
          key: const Key('er-triage-level'),
          initialValue: level,
          isExpanded: true,
          decoration: InputDecoration(labelText: t.erTriageLevel),
          items: [
            for (final value in triageLevels)
              DropdownMenuItem(
                value: value,
                child: Text(triageLabel(t, value)),
              ),
          ],
          onChanged: busy ? null : (value) => setState(() => _level = value),
        ),
        const SizedBox(height: AppSpacing.x3),
        ClinicalField(
          label: t.erRemarks,
          controller: _remarks,
          maxLines: 2,
          enabled: !busy,
        ),
        Text(t.erRegisterHint, style: AppTypography.caption()),
        const SizedBox(height: AppSpacing.x3),
        submitRow(
          t.erRegister,
          patient == null || level == null
              ? null
              : () => run(
                  () => widget.repository.register(
                    patientId: patient.id,
                    triageLevel: level,
                    remarks: _remarks.text,
                  ),
                ),
        ),
      ],
    );
  }
}

Future<bool> showTriageSheet(
  BuildContext context,
  EmergencyRepository repository,
  EmergencyVisit visit,
) => showErSheet(
  context,
  context.l10n.erCompleteTriage,
  _TriageBody(repository: repository, visit: visit),
);

class _TriageBody extends StatefulWidget {
  const _TriageBody({required this.repository, required this.visit});

  final EmergencyRepository repository;
  final EmergencyVisit visit;

  @override
  State<_TriageBody> createState() => _TriageBodyState();
}

class _TriageBodyState extends State<_TriageBody>
    with ErSubmitOnce<_TriageBody> {
  final _complaint = TextEditingController();
  final _pain = TextEditingController();
  final _gcs = TextEditingController();
  final _notes = TextEditingController();
  late String _level = triageLevels.contains(widget.visit.triageLevel)
      ? widget.visit.triageLevel
      : defaultTriageLevel;
  final Map<String, String> _errors = {};

  @override
  void dispose() {
    for (final c in [_complaint, _pain, _gcs, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  void _submit() {
    final t = context.l10n;
    final errors = <String, String>{};
    if (_complaint.text.trim().isEmpty) {
      errors['complaint'] = t.erChiefComplaintRequired;
    }
    final pain = _wholeNumber(
      _pain.text,
      invalid: () => errors['pain'] = t.vitalWholeNumber,
    );
    final gcs = _wholeNumber(
      _gcs.text,
      invalid: () => errors['gcs'] = t.vitalWholeNumber,
    );
    setState(
      () => _errors
        ..clear()
        ..addAll(errors),
    );
    if (errors.isNotEmpty) return;
    final draft = TriageDraft(
      chiefComplaint: _complaint.text,
      triageLevel: _level,
      painScore: pain,
      glasgowComaScale: gcs,
      notes: _notes.text,
    );
    run(() => widget.repository.completeTriage(widget.visit.id, draft));
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ClinicalField(
          key: const Key('er-complaint'),
          label: t.erChiefComplaint,
          controller: _complaint,
          maxLines: 2,
          enabled: !busy,
          errorText: _errors['complaint'],
        ),
        DropdownButtonFormField<String>(
          initialValue: _level,
          isExpanded: true,
          decoration: InputDecoration(labelText: t.erTriageLevel),
          items: [
            for (final value in triageLevels)
              DropdownMenuItem(
                value: value,
                child: Text(triageLabel(t, value)),
              ),
          ],
          onChanged: busy
              ? null
              : (value) => setState(() => _level = value ?? _level),
        ),
        const SizedBox(height: AppSpacing.x3),
        ClinicalField(
          label: t.erPainScore,
          controller: _pain,
          numeric: true,
          enabled: !busy,
          errorText: _errors['pain'],
        ),
        ClinicalField(
          label: t.erGcs,
          controller: _gcs,
          numeric: true,
          enabled: !busy,
          errorText: _errors['gcs'],
        ),
        ClinicalField(
          label: t.erTriageNotes,
          controller: _notes,
          maxLines: 3,
          enabled: !busy,
        ),
        submitRow(t.erCompleteTriage, _submit),
      ],
    );
  }
}

Future<bool> showConsultationSheet(
  BuildContext context,
  EmergencyRepository repository,
  EmergencyVisit visit,
) => showErSheet(
  context,
  context.l10n.erStartConsultation,
  _ConsultationBody(repository: repository, visit: visit),
);

class _ConsultationBody extends StatefulWidget {
  const _ConsultationBody({required this.repository, required this.visit});

  final EmergencyRepository repository;
  final EmergencyVisit visit;

  @override
  State<_ConsultationBody> createState() => _ConsultationBodyState();
}

class _ConsultationBodyState extends State<_ConsultationBody>
    with ErSubmitOnce<_ConsultationBody> {
  late final Future<List<DoctorOption>> _doctors = widget.repository.doctors();
  int? _doctorId;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final current = widget.visit.attendingDoctorName;
    return FutureBuilder<List<DoctorOption>>(
      future: _doctors,
      builder: (context, snapshot) {
        final doctors = snapshot.data ?? const <DoctorOption>[];
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (snapshot.hasError)
              Text(
                apiErrorMessage(t, snapshot.error!),
                style: AppTypography.small(),
              ),
            if (snapshot.connectionState != ConnectionState.done)
              const HmsLoading(),
            DropdownButtonFormField<int?>(
              key: const Key('er-doctor'),
              initialValue: _doctorId,
              isExpanded: true,
              decoration: InputDecoration(labelText: t.erAttendingDoctor),
              items: [
                DropdownMenuItem<int?>(
                  value: null,
                  child: Text(
                    current == null ? t.erNoDoctorYet : t.erKeepDoctor(current),
                  ),
                ),
                for (final doctor in doctors)
                  DropdownMenuItem<int?>(
                    value: doctor.id,
                    child: Text([doctor.name, ?doctor.specialty].join(' · ')),
                  ),
              ],
              onChanged: busy ? null : (id) => setState(() => _doctorId = id),
            ),
            const SizedBox(height: AppSpacing.x3),
            submitRow(
              t.erStartConsultation,
              () => run(
                () => widget.repository.startConsultation(
                  widget.visit.id,
                  doctorId: _doctorId,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

/// Discharge from the ER, or referral out when [refer] is true.
Future<bool> showDispositionSheet(
  BuildContext context,
  EmergencyRepository repository,
  EmergencyVisit visit, {
  required bool refer,
}) => showErSheet(
  context,
  refer ? context.l10n.erRefer : context.l10n.erDischarge,
  _DispositionBody(repository: repository, visit: visit, refer: refer),
);

class _DispositionBody extends StatefulWidget {
  const _DispositionBody({
    required this.repository,
    required this.visit,
    required this.refer,
  });

  final EmergencyRepository repository;
  final EmergencyVisit visit;
  final bool refer;

  @override
  State<_DispositionBody> createState() => _DispositionBodyState();
}

class _DispositionBodyState extends State<_DispositionBody>
    with ErSubmitOnce<_DispositionBody> {
  final _place = TextEditingController();
  final _diagnosis = TextEditingController();
  final _followUp = TextEditingController();
  String? _placeError;

  @override
  void dispose() {
    for (final c in [_place, _diagnosis, _followUp]) {
      c.dispose();
    }
    super.dispose();
  }

  void _submit() {
    final t = context.l10n;
    if (widget.refer && _place.text.trim().isEmpty) {
      setState(() => _placeError = t.erReferredToRequired);
      return;
    }
    setState(() => _placeError = null);
    final repo = widget.repository;
    final id = widget.visit.id;
    run(
      () => widget.refer
          ? repo.refer(
              id,
              referredTo: _place.text,
              diagnosis: _diagnosis.text,
              followUp: _followUp.text,
            )
          : repo.discharge(
              id,
              diagnosis: _diagnosis.text,
              followUp: _followUp.text,
            ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          widget.refer ? t.erReferWarning : t.erDischargeWarning,
          style: AppTypography.small(),
        ),
        const SizedBox(height: AppSpacing.x3),
        if (widget.refer)
          ClinicalField(
            key: const Key('er-referred-to'),
            label: t.erReferredTo,
            controller: _place,
            enabled: !busy,
            errorText: _placeError,
          ),
        ClinicalField(
          label: t.erDischargeDiagnosis,
          controller: _diagnosis,
          maxLines: 2,
          enabled: !busy,
        ),
        ClinicalField(
          label: t.erFollowUp,
          controller: _followUp,
          maxLines: 3,
          enabled: !busy,
        ),
        submitRow(
          widget.refer ? t.erRefer : t.erDischarge,
          _submit,
          danger: true,
        ),
      ],
    );
  }
}

Future<bool> showErNoteSheet(
  BuildContext context,
  EmergencyRepository repository,
  EmergencyVisit visit,
) => showErSheet(
  context,
  context.l10n.erAddNote,
  _NoteBody(repository: repository, visit: visit),
);

class _NoteBody extends StatefulWidget {
  const _NoteBody({required this.repository, required this.visit});

  final EmergencyRepository repository;
  final EmergencyVisit visit;

  @override
  State<_NoteBody> createState() => _NoteBodyState();
}

class _NoteBodyState extends State<_NoteBody> with ErSubmitOnce<_NoteBody> {
  final _note = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ClinicalField(
          key: const Key('er-note'),
          label: t.erNote,
          controller: _note,
          maxLines: 4,
          enabled: !busy,
          errorText: _error,
        ),
        Text(t.erNoteHint, style: AppTypography.caption()),
        const SizedBox(height: AppSpacing.x3),
        submitRow(t.erAddNote, () {
          if (_note.text.trim().isEmpty) {
            setState(() => _error = t.erNoteRequired);
            return;
          }
          setState(() => _error = null);
          run(() => widget.repository.addNote(widget.visit.id, _note.text));
        }),
      ],
    );
  }
}
