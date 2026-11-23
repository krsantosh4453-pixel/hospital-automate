import 'package:flutter/material.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/ui/consultation_sections.dart' show ClinicalField;
import '../../ipd/data/ipd_models.dart';
import '../../ipd/data/ipd_repository.dart';
import '../data/emergency_models.dart';
import '../data/emergency_repository.dart';
import 'emergency_forms.dart';

const _nurseRole = 'Nurse';

String vitalLabel(AppLocalizations t, ErVitalField field) => switch (field) {
  ErVitalField.systolic => t.vitalSystolic,
  ErVitalField.diastolic => t.vitalDiastolic,
  ErVitalField.heartRate => t.vitalPulse,
  ErVitalField.respiratoryRate => t.vitalRespiratoryRate,
  ErVitalField.spo2 => t.vitalSpo2,
  ErVitalField.temperature => t.vitalTemperature,
  ErVitalField.bloodSugar => t.vitalBloodSugar,
};

String vitalErrorText(AppLocalizations t, VitalInputError error) =>
    switch (error) {
      VitalInputError.notANumber => t.vitalNotANumber,
      VitalInputError.negative => t.vitalNegative,
      VitalInputError.notWhole => t.vitalWholeNumber,
      VitalInputError.tooPrecise => t.vitalTooPrecise,
      VitalInputError.tooLong => t.vitalTooHigh,
    };

/// Records a set of vitals on [visit]. A nurse's reading is stored under
/// their own nurse profile; for other roles the server leaves it blank.
Future<bool> showErVitalsSheet(
  BuildContext context,
  EmergencyRepository repository,
  EmergencyVisit visit,
) => showErSheet(
  context,
  context.l10n.erRecordVitals,
  _VitalsBody(repository: repository, visit: visit),
);

class _VitalsBody extends StatefulWidget {
  const _VitalsBody({required this.repository, required this.visit});

  final EmergencyRepository repository;
  final EmergencyVisit visit;

  @override
  State<_VitalsBody> createState() => _VitalsBodyState();
}

class _VitalsBodyState extends State<_VitalsBody>
    with ErSubmitOnce<_VitalsBody> {
  final Map<ErVitalField, TextEditingController> _fields = {
    for (final field in ErVitalField.values) field: TextEditingController(),
  };
  final Map<ErVitalField, String> _errors = {};
  String? _formError;

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  /// The nurse profile id of this login at the acting hospital, or null.
  Future<int?> _recordedBy() async {
    final services = AppScope.read(context);
    final session = services.session.state;
    final hospitalId = session.activeHospital?.id;
    final userId = session.user?.id;
    if (session.activeRole != _nurseRole ||
        hospitalId == null ||
        userId == null) {
      return null;
    }
    final profile = await services.nursing.myProfile(
      hospitalId: hospitalId,
      userId: userId,
    );
    return profile?.id;
  }

  void _submit() {
    final t = context.l10n;
    final values = {
      for (final entry in _fields.entries)
        if (entry.value.text.trim().isNotEmpty) entry.key: entry.value.text,
    };
    final errors = <ErVitalField, String>{
      for (final entry in values.entries)
        if (checkVital(entry.key, entry.value) case final error?)
          entry.key: vitalErrorText(t, error),
    };
    setState(() {
      _errors
        ..clear()
        ..addAll(errors);
      _formError = values.isEmpty ? t.erVitalsEmpty : null;
    });
    if (values.isEmpty || errors.isNotEmpty) return;
    run(() async {
      final recordedBy = await _recordedBy();
      await widget.repository.addVitals(
        widget.visit.id,
        values,
        recordedBy: recordedBy,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final field in ErVitalField.values)
          ClinicalField(
            key: ValueKey('er-vital-${field.key}'),
            label: vitalLabel(t, field),
            controller: _fields[field]!,
            numeric: true,
            enabled: !busy,
            errorText: _errors[field],
          ),
        if (_formError != null) ...[
          HmsAlert(tone: AlertTone.warning, title: _formError!),
          const SizedBox(height: AppSpacing.x3),
        ],
        submitRow(t.saveVitals, _submit),
      ],
    );
  }
}

/// Admits [visit]'s patient to a free bed of this hospital. Returns the new
/// admission once the server has created it, or null.
Future<ErAdmission?> showAdmitSheet(
  BuildContext context,
  EmergencyRepository repository,
  IpdRepository ipd,
  EmergencyVisit visit,
) async {
  ErAdmission? created;
  final done = await showErSheet(
    context,
    context.l10n.erAdmitToIpd,
    _AdmitBody(
      repository: repository,
      ipd: ipd,
      visit: visit,
      onAdmitted: (admission) => created = admission,
    ),
  );
  return done ? created : null;
}

class _AdmitBody extends StatefulWidget {
  const _AdmitBody({
    required this.repository,
    required this.ipd,
    required this.visit,
    required this.onAdmitted,
  });

  final EmergencyRepository repository;
  final IpdRepository ipd;
  final EmergencyVisit visit;
  final ValueChanged<ErAdmission> onAdmitted;

  @override
  State<_AdmitBody> createState() => _AdmitBodyState();
}

class _AdmitBodyState extends State<_AdmitBody> with ErSubmitOnce<_AdmitBody> {
  List<AvailableBed>? _beds;
  List<IpdAdmission> _openStays = const [];
  Object? _loadError;
  int? _bedId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final hospitalId = AppScope.read(context).session.activeHospitalId;
    if (hospitalId == null) return;
    setState(() => _loadError = null);
    try {
      final patientId = widget.visit.patientId;
      final beds = await widget.ipd.availableBeds(hospitalId);
      final stays = patientId == null
          ? const <IpdAdmission>[]
          : await widget.ipd.admissions(patientId: patientId);
      if (!mounted) return;
      setState(() {
        _beds = beds;
        _openStays = [
          for (final stay in stays)
            if (stay.isAdmitted || stay.isDischarging) stay,
        ];
        if (beds.every((b) => b.id != _bedId)) _bedId = null;
      });
    } catch (error) {
      if (mounted) setState(() => _loadError = error);
    }
  }

  void _submit() {
    final bedId = _bedId;
    if (bedId == null) return;
    run(() async {
      try {
        final admission = await widget.repository.admitToIpd(
          widget.visit.id,
          bedId: bedId,
        );
        widget.onAdmitted(admission);
      } on ApiException catch (error) {
        // The bed may have been taken meanwhile: show the current free beds.
        if (error.kind == ApiErrorKind.validation ||
            error.kind == ApiErrorKind.notFound) {
          await _load();
        }
        rethrow;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final beds = _beds;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_openStays.isNotEmpty) ...[
          HmsAlert(
            tone: AlertTone.warning,
            title: t.erAlreadyAdmitted,
            message: _openStays
                .map((s) => s.currentBed?.place.label ?? t.ipdAwaitingBed)
                .join('\n'),
          ),
          const SizedBox(height: AppSpacing.x3),
        ],
        if (_loadError != null)
          HmsAlert(
            tone: AlertTone.danger,
            title: apiErrorMessage(t, _loadError!),
          )
        else if (beds == null)
          const HmsLoading()
        else if (beds.isEmpty)
          Text(t.ipdNoFreeBeds, style: AppTypography.small())
        else ...[
          Text(t.ipdChooseBed, style: AppTypography.small()),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 280),
            child: ListView(
              shrinkWrap: true,
              children: [
                for (final bed in beds)
                  ListTile(
                    key: ValueKey('admit-bed-${bed.id}'),
                    dense: true,
                    selected: bed.id == _bedId,
                    title: Text(bed.place.label),
                    subtitle: bed.roomType == null ? null : Text(bed.roomType!),
                    trailing: bed.id == _bedId
                        ? const Icon(Icons.check, size: 18)
                        : null,
                    onTap: busy ? null : () => setState(() => _bedId = bed.id),
                  ),
              ],
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.x3),
        Text(t.erAdmitHint, style: AppTypography.caption()),
        const SizedBox(height: AppSpacing.x3),
        submitRow(t.erAdmitToIpd, _bedId == null ? null : _submit),
      ],
    );
  }
}
