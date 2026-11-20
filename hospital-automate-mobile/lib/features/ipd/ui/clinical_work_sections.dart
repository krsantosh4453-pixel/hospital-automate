import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_dialog.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/data/doctor_models.dart';
import '../../doctor/ui/doctor_ui.dart' show today;
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/clinical_work_repository.dart';
import '../data/ipd_models.dart';
import 'ipd_ui.dart';

/// Prompt 3: clinical work on Android that the web did alone. Every write
/// goes to the server, which checks the role and the patient's care.

/// A small labelled block used by the forms below.
Widget _label(String text) => Padding(
  padding: const EdgeInsets.only(bottom: AppSpacing.x1_5),
  child: Text(text, style: AppTypography.small(weight: FontWeight.w500)),
);

Widget _gap() => const SizedBox(height: AppSpacing.x3);

String _failure(AppLocalizations t, Object error) =>
    error is ApiException ? apiErrorMessage(t, error) : t.errorUnknown;

// ---------------------------------------------------------------------------
// Allergies (consultation)
// ---------------------------------------------------------------------------

/// Known allergies and whether the patient was asked. "Not known" and "No
/// known allergies" are different answers; adding an allergy replaces both.
class AllergiesSection extends StatefulWidget {
  const AllergiesSection({
    super.key,
    required this.patientId,
    required this.canWrite,
  });

  final int patientId;
  final bool canWrite;

  @override
  State<AllergiesSection> createState() => _AllergiesSectionState();
}

class _AllergiesSectionState extends State<AllergiesSection> {
  late final ClinicalWorkRepository _repo = AppScope.read(context).clinicalWork;
  late final RecordLoader<(String, List<AllergyRecord>)> _loader = RecordLoader(
    () async {
      final rows = await Future.wait<Object>([
        _repo.allergyStatus(widget.patientId),
        _repo.allergies(widget.patientId),
      ]);
      return (rows[0] as String, rows[1] as List<AllergyRecord>);
    },
  );
  final _name = TextEditingController();
  final _reaction = TextEditingController();
  String _category = 'Drug';
  String _severity = '';
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _loader.dispose();
    _name.dispose();
    _reaction.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
      await _loader.load();
    } catch (error) {
      if (!mounted) return;
      final t = context.l10n;
      setState(
        () =>
            _error = error is ApiException && error.hasFlag('allergy_on_record')
            ? t.allergyNoneBlocked
            : _failure(t, error),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _add() async {
    final t = context.l10n;
    if (_name.text.trim().isEmpty) {
      setState(() => _error = t.allergyNameRequired);
      return;
    }
    await _run(() async {
      await _repo.addAllergy(
        widget.patientId,
        name: _name.text.trim(),
        category: _category,
        reaction: _reaction.text.trim(),
        severity: _severity,
      );
      _name.clear();
      _reaction.clear();
    });
  }

  String _statusLabel(AppLocalizations t, String status) => switch (status) {
    AllergyStatus.none => t.allergyStatusNone,
    AllergyStatus.recorded => t.allergyStatusRecorded,
    _ => t.allergyStatusUnknown,
  };

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.allergiesTitle, icon: LucideIcons.shieldAlert),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: RecordSection<(String, List<AllergyRecord>)>(
              loader: _loader,
              skeletons: 1,
              builder: (context, data) {
                final (status, rows) = data;
                // An allergy on record rules out "no known allergies"; the
                // server refuses it too (allergy_on_record), and stays the
                // authority. Only loaded data reaches here, never a failed load.
                final hasAllergy =
                    rows.isNotEmpty || status == AllergyStatus.recorded;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    DetailRow(
                      label: t.allergiesTitle,
                      value: _statusLabel(t, status),
                    ),
                    for (final a in rows)
                      Padding(
                        padding: const EdgeInsets.only(top: AppSpacing.x2),
                        child: Text(
                          [
                            a.name,
                            ?a.category,
                            ?a.reaction,
                            ?a.severity,
                          ].join(' · '),
                          key: ValueKey('allergy-${a.id}'),
                          style: AppTypography.body(weight: FontWeight.w600),
                        ),
                      ),
                    if (_error != null) ...[
                      _gap(),
                      HmsAlert(tone: AlertTone.danger, title: _error!),
                    ],
                    if (widget.canWrite) ...[
                      _gap(),
                      Wrap(
                        spacing: AppSpacing.x2,
                        runSpacing: AppSpacing.x2,
                        children: [
                          HmsButton(
                            key: const Key('allergy-none'),
                            label: t.allergyMarkNone,
                            size: HmsButtonSize.small,
                            variant: HmsButtonVariant.secondary,
                            surface: HmsSurface.card,
                            onPressed:
                                _busy ||
                                    hasAllergy ||
                                    status == AllergyStatus.none
                                ? null
                                : () => _run(
                                    () => _repo.setAllergyStatus(
                                      widget.patientId,
                                      AllergyStatus.none,
                                    ),
                                  ),
                          ),
                          HmsButton(
                            key: const Key('allergy-unknown'),
                            label: t.allergyMarkUnknown,
                            size: HmsButtonSize.small,
                            variant: HmsButtonVariant.ghost,
                            surface: HmsSurface.card,
                            onPressed: _busy || status != AllergyStatus.none
                                ? null
                                : () => _run(
                                    () => _repo.setAllergyStatus(
                                      widget.patientId,
                                      AllergyStatus.unknown,
                                    ),
                                  ),
                          ),
                        ],
                      ),
                      if (hasAllergy) ...[
                        const SizedBox(height: AppSpacing.x1),
                        Text(
                          t.allergyNoneBlocked,
                          key: const Key('allergy-none-blocked'),
                          style: AppTypography.caption(
                            color: AppColors.onCardMuted,
                          ),
                        ),
                      ],
                      _gap(),
                      HmsTextField(
                        key: const Key('allergy-name'),
                        label: t.allergyName,
                        controller: _name,
                      ),
                      _gap(),
                      _label(t.allergyCategory),
                      DropdownButtonFormField<String>(
                        key: const Key('allergy-category'),
                        isExpanded: true,
                        initialValue: _category,
                        items: [
                          for (final (v, l) in [
                            ('Drug', t.allergyCategoryDrug),
                            ('Food', t.allergyCategoryFood),
                            ('Environmental', t.allergyCategoryEnvironmental),
                            ('Other', t.allergyCategoryOther),
                          ])
                            DropdownMenuItem(value: v, child: Text(l)),
                        ],
                        onChanged: (v) =>
                            setState(() => _category = v ?? _category),
                      ),
                      _gap(),
                      HmsTextField(
                        key: const Key('allergy-reaction'),
                        label: t.allergyReaction,
                        controller: _reaction,
                      ),
                      _gap(),
                      _label(t.allergySeverity),
                      DropdownButtonFormField<String>(
                        key: const Key('allergy-severity'),
                        isExpanded: true,
                        initialValue: _severity,
                        items: [
                          const DropdownMenuItem(value: '', child: Text('—')),
                          for (final v in ['Mild', 'Moderate', 'Severe'])
                            DropdownMenuItem(value: v, child: Text(v)),
                        ],
                        onChanged: (v) => setState(() => _severity = v ?? ''),
                      ),
                      _gap(),
                      HmsButton(
                        key: const Key('allergy-add'),
                        label: t.allergyAdd,
                        icon: LucideIcons.plus,
                        surface: HmsSurface.card,
                        loading: _busy,
                        onPressed: _add,
                      ),
                    ],
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Admit a patient (doctor)
// ---------------------------------------------------------------------------

/// `/ipd/admit/:patientId`: the doctor admits the patient under their own
/// name, optionally straight into a free bed. Occupied beds are never offered,
/// and the server refuses them anyway.
class AdmitPatientScreen extends StatefulWidget {
  const AdmitPatientScreen({super.key, required this.patientId, this.name});

  final int patientId;
  final String? name;

  @override
  State<AdmitPatientScreen> createState() => _AdmitPatientScreenState();
}

class _AdmitPatientScreenState extends State<AdmitPatientScreen> {
  late final _services = AppScope.read(context);
  late final RecordLoader<List<AvailableBed>> _beds = RecordLoader(
    () => _services.ipd.availableBeds(
      _services.session.state.activeHospitalId ?? 0,
    ),
  );
  final _reason = TextEditingController();
  String? _ward;
  int? _bedId;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _beds.load();
  }

  @override
  void dispose() {
    _beds.dispose();
    _reason.dispose();
    super.dispose();
  }

  Future<void> _admit() async {
    final t = context.l10n;
    final hospitalId = _services.session.state.activeHospitalId;
    if (_reason.text.trim().isEmpty || hospitalId == null) {
      setState(() => _error = t.admitReasonRequired);
      return;
    }
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final admission = await _services.clinicalWork.admit(
        widget.patientId,
        hospitalId,
        _reason.text.trim(),
      );
      final bed = _bedId;
      if (bed != null) await _services.ipd.allocateBed(admission.id, bed);
      if (mounted) context.go(IpdRoutes.admission(admission.id));
    } catch (error) {
      if (!mounted) return;
      setState(
        () => _error =
            error is ApiException && error.kind == ApiErrorKind.conflict
            ? t.admitAlreadyActive
            : _failure(t, error),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.admitPatient,
          description: [?widget.name, t.admitIntro].join(' · '),
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_error != null) ...[
                HmsAlert(tone: AlertTone.danger, title: _error!),
                _gap(),
              ],
              HmsTextField(
                key: const Key('admit-reason'),
                label: t.admitReason,
                controller: _reason,
                required: true,
              ),
              _gap(),
              RecordSection<List<AvailableBed>>(
                loader: _beds,
                skeletons: 1,
                builder: (context, beds) {
                  final wards = {
                    for (final b in beds)
                      if (b.place.ward != null) b.place.ward!,
                  }.toList()..sort();
                  final inWard = [
                    for (final b in beds)
                      if (b.place.ward == _ward) b,
                  ];
                  if (beds.isEmpty) {
                    return Text(
                      t.admitNoFreeBeds,
                      style: AppTypography.small(),
                    );
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _label(t.admitWard),
                      DropdownButtonFormField<String>(
                        key: const Key('admit-ward'),
                        isExpanded: true,
                        initialValue: _ward,
                        hint: Text(t.admitWard),
                        items: [
                          for (final w in wards)
                            DropdownMenuItem(value: w, child: Text(w)),
                        ],
                        onChanged: (w) => setState(() {
                          _ward = w;
                          _bedId = null;
                        }),
                      ),
                      _gap(),
                      _label(t.admitBed),
                      DropdownButtonFormField<int?>(
                        key: ValueKey('admit-bed-$_ward'),
                        isExpanded: true,
                        initialValue: _bedId,
                        hint: Text(t.admitNoBedNow),
                        items: [
                          DropdownMenuItem<int?>(
                            value: null,
                            child: Text(t.admitNoBedNow),
                          ),
                          for (final b in inWard)
                            DropdownMenuItem<int?>(
                              value: b.id,
                              child: Text(b.place.label),
                            ),
                        ],
                        onChanged: (id) => setState(() => _bedId = id),
                      ),
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.x4),
              HmsButton(
                key: const Key('admit-confirm'),
                label: t.admitConfirm,
                icon: LucideIcons.bedDouble,
                surface: HmsSurface.card,
                loading: _busy,
                onPressed: _admit,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Ward medication orders (doctor writes, nurses give)
// ---------------------------------------------------------------------------

class WardOrdersSection extends StatefulWidget {
  const WardOrdersSection({
    super.key,
    required this.admission,
    required this.canOrder,
  });

  final IpdAdmission admission;
  final bool canOrder;

  @override
  State<WardOrdersSection> createState() => _WardOrdersSectionState();
}

class _WardOrdersSectionState extends State<WardOrdersSection> {
  late final _services = AppScope.read(context);
  late final RecordLoader<List<MedicationOrder>> _orders = RecordLoader(
    () => _services.clinicalWork.medicationOrders(widget.admission.id),
  );
  late final RecordLoader<List<PrescribedMedicine>> _medicines = RecordLoader(
    () => _services.clinicalWork.prescribedMedicines(
      widget.admission.patientId ?? 0,
    ),
  );
  final _dose = TextEditingController();
  final _frequency = TextEditingController();
  final _instructions = TextEditingController();
  PrescribedMedicine? _medicine;
  String _route = 'Oral';
  DateTime? _endDate;
  // First dose: the next medication round unless the doctor chooses (the
  // server refuses a past time and asks for a choice when it cannot decide).
  FirstDose _firstDose = FirstDose.nextRound;
  DateTime? _firstDoseAt;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _orders.load();
    if (widget.canOrder) _medicines.load();
  }

  @override
  void dispose() {
    _orders.dispose();
    _medicines.dispose();
    for (final c in [_dose, _frequency, _instructions]) {
      c.dispose();
    }
    super.dispose();
  }

  /// A refused or undecidable first dose, in words the doctor can act on.
  String _scheduleFailure(AppLocalizations t, Object error) {
    if (error is ApiException && error.hasFlag('first_dose_required')) {
      return t.firstDoseChoose;
    }
    if (error is ApiException && error.fieldErrors.containsKey('first_dose')) {
      return t.firstDoseRefused;
    }
    return _failure(t, error);
  }

  /// The review the doctor confirms: first dose, the next ones and the count.
  String _reviewText(AppLocalizations t, SchedulePreview preview) {
    if (preview.prn) return t.firstDosePrn;
    final first = preview.firstDoseAt;
    final mode = switch (preview.mode) {
      FirstDose.nextRound => t.firstDoseNextRound,
      FirstDose.now => t.firstDoseNow,
      FirstDose.at => t.firstDoseAt,
      null => '',
    };
    final next = preview.doses.skip(1).take(3).map((d) => formatDateTime(t, d));
    return [
      t.firstDoseReviewFirst('${formatDateTime(t, first)} ($mode)'),
      if (next.isNotEmpty) t.firstDoseReviewNext(next.join(', ')),
      t.firstDoseReviewCount(preview.doseCount),
    ].join('\n');
  }

  Future<void> _order() async {
    final t = context.l10n;
    final medicine = _medicine;
    final hospitalId = _services.session.state.activeHospitalId;
    if (medicine == null ||
        _dose.text.trim().isEmpty ||
        _frequency.text.trim().isEmpty ||
        hospitalId == null) {
      setState(() => _error = t.wardOrderFieldsRequired);
      return;
    }
    if (_firstDose == FirstDose.at && _firstDoseAt == null) {
      setState(() => _error = t.firstDosePickTime);
      return;
    }
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    final draft = MedicationOrderDraft(
      medicine: medicine,
      dose: _dose.text.trim(),
      route: _route,
      frequency: _frequency.text.trim(),
      startDate: today(),
      endDate: _endDate,
      instructions: _instructions.text.trim(),
      firstDose: _firstDose,
      firstDoseAt: _firstDose == FirstDose.at ? _firstDoseAt : null,
    );
    try {
      // The doctor reviews the schedule before anything is saved.
      final preview = await _services.clinicalWork.previewSchedule(
        hospitalId,
        draft,
      );
      if (!mounted) return;
      // No spinner behind the review: the form waits for the doctor.
      setState(() => _busy = false);
      final ok = await showHmsConfirm(
        context,
        title: t.firstDoseReviewTitle,
        message: _reviewText(t, preview),
        confirmLabel: t.wardOrderAdd,
      );
      if (!ok || !mounted) return;
      setState(() => _busy = true);
      await _services.clinicalWork.orderMedication(
        widget.admission.id,
        widget.admission.patientId ?? 0,
        hospitalId,
        draft,
      );
      setState(() {
        _medicine = null;
        _endDate = null;
        _firstDose = FirstDose.nextRound;
        _firstDoseAt = null;
      });
      for (final c in [_dose, _frequency, _instructions]) {
        c.clear();
      }
      await _orders.load();
    } catch (error) {
      if (mounted) setState(() => _error = _scheduleFailure(t, error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickFirstDoseTime() async {
    final now = DateTime.now();
    final day = await showDatePicker(
      context: context,
      initialDate: _firstDoseAt ?? now,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 30)),
    );
    if (day == null || !mounted) return;
    final clock = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_firstDoseAt ?? now),
    );
    if (clock == null || !mounted) return;
    setState(() {
      _firstDoseAt = DateTime(
        day.year,
        day.month,
        day.day,
        clock.hour,
        clock.minute,
      );
      _firstDose = FirstDose.at;
    });
  }

  Future<void> _stop(MedicationOrder order) async {
    final t = context.l10n;
    final ok = await showHmsConfirm(
      context,
      title: '${t.wardOrderStop}: ${order.medicineName}?',
      message: t.wardOrdersIntro,
      confirmLabel: t.wardOrderStop,
      destructive: true,
    );
    if (!ok || !mounted) return;
    try {
      await _services.clinicalWork.stopMedication(order.id);
      await _orders.load();
    } catch (error) {
      if (mounted) setState(() => _error = _failure(t, error));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.wardOrdersTitle,
            description: t.wardOrdersIntro,
            icon: LucideIcons.pill,
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                RecordSection<List<MedicationOrder>>(
                  loader: _orders,
                  skeletons: 1,
                  builder: (context, orders) => orders.isEmpty
                      ? Text(t.wardOrderNone, style: AppTypography.small())
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            for (final o in orders)
                              Padding(
                                padding: const EdgeInsets.only(
                                  bottom: AppSpacing.x2,
                                ),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        [
                                          o.medicineName,
                                          o.dose,
                                          o.route,
                                          o.frequency,
                                          if (o.instructions?.isNotEmpty ??
                                              false)
                                            o.instructions!,
                                        ].join(' · '),
                                        style: AppTypography.small(),
                                      ),
                                    ),
                                    if (!o.isActive)
                                      StatusBadge(status: t.wardOrderStopped)
                                    else if (widget.canOrder)
                                      HmsButton(
                                        key: ValueKey('stop-order-${o.id}'),
                                        label: t.wardOrderStop,
                                        size: HmsButtonSize.small,
                                        variant: HmsButtonVariant.secondary,
                                        surface: HmsSurface.card,
                                        onPressed: () => _stop(o),
                                      ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                ),
                if (_error != null) ...[
                  _gap(),
                  HmsAlert(tone: AlertTone.danger, title: _error!),
                ],
                if (widget.canOrder) ...[
                  _gap(),
                  RecordSection<List<PrescribedMedicine>>(
                    loader: _medicines,
                    skeletons: 1,
                    builder: (context, medicines) => medicines.isEmpty
                        ? Text(
                            t.wardOrderNoMedicines,
                            style: AppTypography.small(),
                          )
                        : _orderForm(t, medicines),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _orderForm(AppLocalizations t, List<PrescribedMedicine> medicines) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _label(t.wardOrderMedicine),
          DropdownButtonFormField<int>(
            key: const Key('order-medicine'),
            isExpanded: true,
            initialValue: _medicine?.id,
            items: [
              for (final m in medicines)
                DropdownMenuItem(
                  value: m.id,
                  child: Text(
                    [m.name, ?m.dosage].join(' · '),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (id) => setState(() {
              _medicine = medicines.firstWhere((m) => m.id == id);
              _dose.text = _medicine?.dosage ?? '';
              _frequency.text = _medicine?.frequency ?? '';
            }),
          ),
          _gap(),
          HmsTextField(
            key: const Key('order-dose'),
            label: t.wardOrderDose,
            controller: _dose,
            required: true,
          ),
          _gap(),
          _label(t.route),
          DropdownButtonFormField<String>(
            key: const Key('order-route'),
            isExpanded: true,
            initialValue: _route,
            items: [
              for (final r in ['Oral', 'IV', 'IM', 'SC', 'Topical', 'Inhaled'])
                DropdownMenuItem(value: r, child: Text(r)),
            ],
            onChanged: (r) => setState(() => _route = r ?? _route),
          ),
          _gap(),
          HmsTextField(
            key: const Key('order-frequency'),
            label: t.frequency,
            controller: _frequency,
            required: true,
          ),
          _gap(),
          _label(t.firstDoseLabel),
          Wrap(
            spacing: AppSpacing.x2,
            runSpacing: AppSpacing.x2,
            children: [
              for (final (mode, label) in [
                (FirstDose.nextRound, t.firstDoseNextRound),
                (FirstDose.now, t.firstDoseNow),
                (FirstDose.at, t.firstDoseAt),
              ])
                ChoiceChip(
                  key: Key('first-dose-${mode.wire}'),
                  label: Text(label),
                  selected: _firstDose == mode,
                  onSelected: _busy
                      ? null
                      : (_) => mode == FirstDose.at
                            ? _pickFirstDoseTime()
                            : setState(() => _firstDose = mode),
                ),
            ],
          ),
          if (_firstDose == FirstDose.at) ...[
            _gap(),
            HmsButton(
              key: const Key('first-dose-time'),
              label: _firstDoseAt == null
                  ? t.firstDosePickTime
                  : formatDateTime(t, _firstDoseAt),
              icon: LucideIcons.clock,
              variant: HmsButtonVariant.secondary,
              surface: HmsSurface.card,
              onPressed: _pickFirstDoseTime,
            ),
          ],
          _gap(),
          _label(t.wardOrderEndDate),
          HmsButton(
            key: const Key('order-end-date'),
            label: _endDate == null ? '—' : formatDay(t, _endDate),
            icon: LucideIcons.calendarDays,
            variant: HmsButtonVariant.secondary,
            surface: HmsSurface.card,
            onPressed: () async {
              final picked = await showDatePicker(
                context: context,
                initialDate: _endDate ?? today().add(const Duration(days: 5)),
                firstDate: today(),
                lastDate: today().add(const Duration(days: 365)),
              );
              if (picked != null && mounted) setState(() => _endDate = picked);
            },
          ),
          _gap(),
          HmsTextField(
            key: const Key('order-instructions'),
            label: t.instructions,
            controller: _instructions,
          ),
          _gap(),
          HmsButton(
            key: const Key('order-add'),
            label: t.wardOrderAdd,
            icon: LucideIcons.plus,
            surface: HmsSurface.card,
            loading: _busy,
            onPressed: _order,
          ),
        ],
      );
}

// ---------------------------------------------------------------------------
// Discharge plan and summary (doctor)
// ---------------------------------------------------------------------------

/// The plan (checklist + follow-up) and the summary, which the doctor saves
/// as a draft and then finalises. [onSaved] reloads the readiness above, so
/// "Complete discharge" opens only when the server says it may.
class DischargeFormsSection extends StatefulWidget {
  const DischargeFormsSection({
    super.key,
    required this.admission,
    required this.summary,
    required this.onSaved,
  });

  final IpdAdmission admission;
  final DischargeSummaryRecord? summary;
  final Future<void> Function() onSaved;

  @override
  State<DischargeFormsSection> createState() => _DischargeFormsSectionState();
}

class _DischargeFormsSectionState extends State<DischargeFormsSection> {
  late final ClinicalWorkRepository _repo = AppScope.read(context).clinicalWork;
  late final RecordLoader<DischargePlanRecord?> _plan = RecordLoader(
    () => _repo.dischargePlan(widget.admission.id),
  );
  final _followUp = TextEditingController();
  final _diagnosis = TextEditingController();
  final _condition = TextEditingController();
  final _medications = TextEditingController();
  final _notes = TextEditingController();
  bool _reconciled = false;
  bool _counselled = false;
  bool _followUpArranged = false;
  bool _documents = false;
  bool _busy = false;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    _plan.load().then((_) {
      final plan = _plan.data;
      if (!mounted || plan == null) return;
      setState(() {
        _followUp.text = plan.instructions;
        _reconciled = plan.medicationsReconciled;
        _counselled = plan.patientCounselled;
        _followUpArranged = plan.followUpArranged;
        _documents = plan.documentsHandedOver;
      });
    });
  }

  @override
  void dispose() {
    _plan.dispose();
    for (final c in [_followUp, _diagnosis, _condition, _medications, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      await action();
      if (!mounted) return;
      setState(() => _notice = context.l10n.dischargeSaved);
      await widget.onSaved();
    } catch (error) {
      if (mounted) setState(() => _error = _failure(context.l10n, error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _savePlan() => _run(() async {
    await _repo.saveDischargePlan(
      widget.admission.id,
      DischargePlanRecord(
        id: _plan.data?.id ?? 0,
        instructions: _followUp.text.trim(),
        medicationsReconciled: _reconciled,
        patientCounselled: _counselled,
        followUpArranged: _followUpArranged,
        documentsHandedOver: _documents,
      ),
      existingId: _plan.data?.id,
    );
    await _plan.load();
  });

  /// The summary text the patient and the next doctor read, in sections.
  String _summaryText(AppLocalizations t) => [
    '${t.dischargeFinalDiagnosis}: ${_diagnosis.text.trim()}',
    '${t.dischargeCondition}: ${_condition.text.trim()}',
    if (_medications.text.trim().isNotEmpty)
      '${t.dischargeMedications}: ${_medications.text.trim()}',
    if (_followUp.text.trim().isNotEmpty)
      '${t.dischargeFollowUp}: ${_followUp.text.trim()}',
    if (_notes.text.trim().isNotEmpty) _notes.text.trim(),
  ].join('\n');

  Future<void> _saveSummary() async {
    final t = context.l10n;
    if (_diagnosis.text.trim().isEmpty || _condition.text.trim().isEmpty) {
      setState(() => _error = t.dischargeSummaryRequired);
      return;
    }
    await _run(
      () => _repo.saveDischargeSummary(
        widget.admission.id,
        _summaryText(t),
        existingId: widget.summary?.id,
      ),
    );
  }

  Future<void> _finalize() async {
    final t = context.l10n;
    final summary = widget.summary;
    if (summary == null) return;
    final ok = await showHmsConfirm(
      context,
      title: t.dischargeFinalizeTitle,
      message: t.dischargeFinalizeBody,
      confirmLabel: t.dischargeFinalize,
    );
    if (!ok || !mounted) return;
    await _run(() => _repo.finalizeDischargeSummary(summary.id));
  }

  Widget _check(String label, bool value, ValueChanged<bool> onChanged) =>
      CheckboxListTile(
        contentPadding: EdgeInsets.zero,
        dense: true,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(label, style: AppTypography.small()),
        value: value,
        // On the teal card the theme's dark box was barely visible: a light
        // outline when clear, a light fill with a teal tick when ticked,
        // and a dimmer version of both while saving (disabled).
        side: WidgetStateBorderSide.resolveWith(
          (states) => BorderSide(
            color: states.contains(WidgetState.disabled)
                ? AppColors.onCardMuted
                : AppColors.onCard,
            width: 1.5,
          ),
        ),
        fillColor: WidgetStateProperty.resolveWith(
          (states) => !states.contains(WidgetState.selected)
              ? Colors.transparent
              : states.contains(WidgetState.disabled)
              ? AppColors.onCardMuted
              : AppColors.onCard,
        ),
        checkColor: AppColors.card,
        onChanged: _busy ? null : (v) => onChanged(v ?? false),
      );

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final summary = widget.summary;
    final finalized = summary?.finalized ?? false;
    return HmsCard(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.x4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(t.dischargePlanTitle, style: AppTypography.cardTitle()),
            if (_notice != null) ...[
              _gap(),
              HmsAlert(tone: AlertTone.success, title: _notice!),
            ],
            if (_error != null) ...[
              _gap(),
              HmsAlert(tone: AlertTone.danger, title: _error!),
            ],
            _check(
              t.ipdCheckMedications,
              _reconciled,
              (v) => setState(() => _reconciled = v),
            ),
            _check(
              t.ipdCheckCounselled,
              _counselled,
              (v) => setState(() => _counselled = v),
            ),
            _check(
              t.ipdCheckFollowUp,
              _followUpArranged,
              (v) => setState(() => _followUpArranged = v),
            ),
            _check(
              t.ipdCheckDocuments,
              _documents,
              (v) => setState(() => _documents = v),
            ),
            HmsTextField(
              key: const Key('discharge-follow-up'),
              label: t.dischargeFollowUp,
              controller: _followUp,
            ),
            _gap(),
            HmsButton(
              key: const Key('discharge-save-plan'),
              label: t.dischargeSavePlan,
              surface: HmsSurface.card,
              loading: _busy,
              onPressed: _savePlan,
            ),
            const SizedBox(height: AppSpacing.x5),
            Text(t.dischargeSummaryTitle, style: AppTypography.cardTitle()),
            _gap(),
            if (finalized)
              HmsAlert(
                tone: AlertTone.success,
                title: t.dischargeSummaryFinalized,
              )
            else ...[
              HmsTextField(
                key: const Key('discharge-diagnosis'),
                label: t.dischargeFinalDiagnosis,
                controller: _diagnosis,
                required: true,
              ),
              _gap(),
              HmsTextField(
                key: const Key('discharge-condition'),
                label: t.dischargeCondition,
                controller: _condition,
                required: true,
              ),
              _gap(),
              HmsTextField(
                key: const Key('discharge-medications'),
                label: t.dischargeMedications,
                controller: _medications,
              ),
              _gap(),
              HmsTextField(
                key: const Key('discharge-notes'),
                label: t.dischargeNotes,
                controller: _notes,
              ),
              _gap(),
              HmsButton(
                key: const Key('discharge-save-summary'),
                label: t.dischargeSaveSummary,
                variant: HmsButtonVariant.secondary,
                surface: HmsSurface.card,
                loading: _busy,
                onPressed: _saveSummary,
              ),
              if (summary != null) ...[
                _gap(),
                HmsButton(
                  key: const Key('discharge-finalize'),
                  label: t.dischargeFinalize,
                  icon: LucideIcons.badgeCheck,
                  surface: HmsSurface.card,
                  loading: _busy,
                  onPressed: _finalize,
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Final bill of a stay (billing desk)
// ---------------------------------------------------------------------------

class FinalBillSection extends StatefulWidget {
  const FinalBillSection({super.key, this.onBilled});

  /// Called after a final bill is created, so a screen listing invoices
  /// reloads them (the new bill and the totals were stale until Refresh).
  final VoidCallback? onBilled;

  @override
  State<FinalBillSection> createState() => _FinalBillSectionState();
}

class _FinalBillSectionState extends State<FinalBillSection> {
  late final ClinicalWorkRepository _repo = AppScope.read(context).clinicalWork;
  late final RecordLoader<List<StayAwaitingBill>> _stays = RecordLoader(
    _repo.staysAwaitingFinalBill,
  );
  int? _busy;
  String? _error;
  String? _notice;

  @override
  void initState() {
    super.initState();
    _stays.load();
  }

  @override
  void dispose() {
    _stays.dispose();
    super.dispose();
  }

  Future<void> _bill(StayAwaitingBill stay) async {
    final t = context.l10n;
    if (_busy != null) return;
    // Like payments, dispensing and discharge: a final bill is confirmed
    // first. The server still refuses a second final bill for the stay.
    final total = stay.bedChargeTotal == null
        ? null
        : formatRupees(double.tryParse(stay.bedChargeTotal!));
    final ok = await showHmsConfirm(
      context,
      title: t.finalBillConfirmTitle(stay.patientName),
      message: [
        if (stay.days != null) t.finalBillDays('${stay.days}'),
        ...stay.bedChargeLines,
        if (total != null) t.finalBillBedCharges(total),
        t.finalBillConfirmBody,
      ].join('\n'),
      confirmLabel: t.finalBillCreate,
    );
    if (!ok || !mounted || _busy != null) return;
    setState(() {
      _busy = stay.admissionId;
      _error = null;
      _notice = null;
    });
    try {
      await _repo.createFinalBill(stay.admissionId);
      if (mounted) setState(() => _notice = t.finalBillDone);
      widget.onBilled?.call();
      await _stays.load();
    } catch (error) {
      if (mounted) setState(() => _error = _failure(t, error));
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.finalBillTitle, icon: LucideIcons.bedDouble),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.x4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_notice != null) ...[
                  HmsAlert(tone: AlertTone.success, title: _notice!),
                  _gap(),
                ],
                if (_error != null) ...[
                  HmsAlert(tone: AlertTone.danger, title: _error!),
                  _gap(),
                ],
                RecordSection<List<StayAwaitingBill>>(
                  loader: _stays,
                  skeletons: 1,
                  builder: (context, stays) {
                    final waiting = [
                      for (final s in stays)
                        if (s.finalInvoiceNumber == null) s,
                    ];
                    if (waiting.isEmpty) {
                      return Text(
                        t.finalBillNone,
                        style: AppTypography.small(),
                      );
                    }
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        for (final s in waiting) ...[
                          Text(
                            s.patientName,
                            style: AppTypography.body(weight: FontWeight.w600),
                          ),
                          if (s.days != null)
                            Text(
                              t.finalBillDays('${s.days}'),
                              style: AppTypography.small(),
                            ),
                          _gap(),
                          // BUG-07: bed days priced by the server from the price list.
                          for (final line in s.bedChargeLines)
                            Text(line, style: AppTypography.small()),
                          if (s.bedChargeTotal != null)
                            Text(
                              t.finalBillBedCharges(
                                formatRupees(
                                  double.tryParse(s.bedChargeTotal!),
                                ),
                              ),
                              key: ValueKey('final-beds-${s.admissionId}'),
                              style: AppTypography.body(
                                weight: FontWeight.w600,
                              ),
                            ),
                          if (s.bedChargeError != null)
                            HmsAlert(
                              tone: AlertTone.warning,
                              title: t.finalBillNoBedPrice,
                              message: s.bedChargeError,
                            ),
                          _gap(),
                          HmsButton(
                            key: ValueKey('final-bill-${s.admissionId}'),
                            label: t.finalBillCreate,
                            surface: HmsSurface.card,
                            loading: _busy == s.admissionId,
                            onPressed: _busy == null && s.bedChargeError == null
                                ? () => _bill(s)
                                : null,
                          ),
                          const SizedBox(height: AppSpacing.x4),
                        ],
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// The patient's own history
// ---------------------------------------------------------------------------

/// Visits, diagnoses, prescriptions, released reports, vitals, admissions and
/// discharges (with the finalised summary), newest first. The server returns
/// only this patient's records at their own hospitals.
class PatientHistorySection extends StatefulWidget {
  const PatientHistorySection({super.key, required this.patientId});

  final int patientId;

  @override
  State<PatientHistorySection> createState() => _PatientHistorySectionState();
}

class _PatientHistorySectionState extends State<PatientHistorySection> {
  late final RecordLoader<List<TimelineEvent>> _loader = RecordLoader(
    () => AppScope.read(context).clinicalWork.history(widget.patientId),
  );
  String? _kind;

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
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.historyTitle,
            description: t.historyIntro,
            icon: LucideIcons.history,
          ),
          RecordSection<List<TimelineEvent>>(
            loader: _loader,
            builder: (context, events) {
              if (events.isEmpty) {
                return HmsEmptyState(compact: true, title: t.historyEmpty);
              }
              final kinds = {for (final e in events) e.kind}.toList()..sort();
              final shown = [
                for (final e in events)
                  if (_kind == null || e.kind == _kind) e,
              ];
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.all(AppSpacing.x3),
                    child: Wrap(
                      spacing: AppSpacing.x2,
                      runSpacing: AppSpacing.x2,
                      children: [
                        for (final k in <String?>[null, ...kinds])
                          ChoiceChip(
                            key: ValueKey('history-kind-${k ?? 'all'}'),
                            label: Text(k ?? t.historyAll),
                            selected: _kind == k,
                            onSelected: (_) => setState(() => _kind = k),
                          ),
                      ],
                    ),
                  ),
                  HmsDividedColumn(
                    children: [
                      for (final e in shown)
                        Padding(
                          padding: AppSpacing.cardRow,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                [
                                  e.kind,
                                  formatDay(t, e.when),
                                  ?e.hospital,
                                ].join(' · '),
                                style: AppTypography.caption(),
                              ),
                              Text(
                                e.title,
                                style: AppTypography.body(
                                  weight: FontWeight.w600,
                                ),
                              ),
                              if (e.detail?.isNotEmpty ?? false)
                                Text(e.detail!, style: AppTypography.small()),
                            ],
                          ),
                        ),
                    ],
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
