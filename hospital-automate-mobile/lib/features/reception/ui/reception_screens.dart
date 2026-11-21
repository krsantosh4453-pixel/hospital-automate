import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/security/session_controller.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_text_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../doctor/data/doctor_models.dart';
import '../../doctor/ui/doctor_ui.dart' show today;
import '../../patient/data/appointment_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/reception_repository.dart';

/// The role these screens are for (front desk). The server checks every
/// request; these pages only offer what the desk may do.
const receptionistRole = 'Receptionist';

bool isReceptionist(SessionState session) =>
    session.isStaff && session.activeRole == receptionistRole;

const _minSearchLength = 2;
const _phoneDigits = 10;

/// `/patients` for the front desk: find a patient, register a new one, or
/// register an existing patient (for example a patient-app account) here.
class ReceptionPatientsScreen extends StatefulWidget {
  const ReceptionPatientsScreen({super.key});

  @override
  State<ReceptionPatientsScreen> createState() =>
      _ReceptionPatientsScreenState();
}

class _ReceptionPatientsScreenState extends State<ReceptionPatientsScreen> {
  final _query = TextEditingController();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _linkPhone = TextEditingController();

  List<PatientSummary>? _results;
  bool _searching = false;
  String? _searchError;

  DateTime? _dob;
  String _gender = 'Female';
  bool _registering = false;
  String? _registerError;
  String? _registered;
  bool _offerRegisterAnyway = false;

  DateTime? _linkDob;
  bool _linking = false;
  String? _linkError;
  String? _linked;

  @override
  void dispose() {
    for (final c in [_query, _name, _phone, _linkPhone]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _search() async {
    final query = _query.text.trim();
    if (query.length < _minSearchLength || _searching) return;
    setState(() {
      _searching = true;
      _searchError = null;
    });
    try {
      final rows = await AppScope.of(context).doctor.searchPatients(query);
      if (mounted) setState(() => _results = rows);
    } catch (error) {
      if (mounted) {
        setState(() => _searchError = apiErrorMessage(context.l10n, error));
      }
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  Future<DateTime?> _pickDob(DateTime? current) {
    final now = today();
    return showDatePicker(
      context: context,
      initialDate: current ?? DateTime(now.year - 30, now.month, now.day),
      firstDate: DateTime(now.year - 120),
      lastDate: now,
      initialEntryMode: DatePickerEntryMode.input,
      helpText: context.l10n.dateOfBirth,
    );
  }

  Future<void> _register({bool confirmNew = false}) async {
    if (_registering) return;
    final t = context.l10n;
    final services = AppScope.read(context);
    final hospitalId = services.session.state.activeHospitalId;
    final name = _name.text.trim();
    final phone = _phone.text.trim();
    final dob = _dob;
    final problem = name.isEmpty
        ? t.authNameRequired
        : phone.length != _phoneDigits
        ? t.receptionPhoneInvalid
        : dob == null
        ? t.authDobRequired
        : null;
    if (problem != null || hospitalId == null) {
      setState(() => _registerError = problem ?? t.selectHospital);
      return;
    }
    setState(() {
      _registering = true;
      _registerError = null;
      _registered = null;
      _offerRegisterAnyway = false;
    });
    try {
      final patient = await services.reception.registerPatient(
        NewPatientDraft(
          name: name,
          dateOfBirth: dob!,
          gender: _gender,
          phone: phone,
        ),
        hospitalId,
        confirmNew: confirmNew,
      );
      if (!mounted) return;
      setState(() {
        _registered = t.receptionRegistered(patient.name, patient.uhid ?? '—');
        _name.clear();
        _phone.clear();
        _dob = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        if (error is ApiException && error.hasFlag('portal_account')) {
          // Same person, already known: register that record here instead.
          _registerError = t.receptionPortalAccount;
          _linkPhone.text = phone;
          _linkDob = dob;
        } else if (error is ApiException &&
            error.kind == ApiErrorKind.conflict) {
          _registerError = t.receptionPossibleDuplicate;
          _offerRegisterAnyway = true;
        } else {
          _registerError = apiErrorMessage(t, error);
        }
      });
    } finally {
      if (mounted) setState(() => _registering = false);
    }
  }

  Future<void> _link() async {
    if (_linking) return;
    final t = context.l10n;
    final phone = _linkPhone.text.trim();
    final dob = _linkDob;
    if (phone.length != _phoneDigits || dob == null) {
      setState(
        () => _linkError = phone.length != _phoneDigits
            ? t.receptionPhoneInvalid
            : t.authDobRequired,
      );
      return;
    }
    setState(() {
      _linking = true;
      _linkError = null;
      _linked = null;
    });
    try {
      final patient = await AppScope.read(context).reception
          .linkPatient(phone, dob);
      if (!mounted) return;
      setState(() {
        _linked = t.receptionLinked(patient.name, patient.uhid ?? '—');
        _linkPhone.clear();
        _linkDob = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(
        () => _linkError = error is ApiException && error.hasFlag('multiple')
            ? t.receptionMultipleMatch
            : error is ApiException && error.kind == ApiErrorKind.notFound
            ? t.receptionNoMatch
            : apiErrorMessage(t, error),
      );
    } finally {
      if (mounted) setState(() => _linking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.navPatients, description: t.receptionPatientsIntro),
        const SizedBox(height: AppSpacing.x4),
        _searchCard(t),
        const SizedBox(height: AppSpacing.x4),
        _registerCard(t),
        const SizedBox(height: AppSpacing.x4),
        _linkCard(t),
      ],
    );
  }

  Widget _searchCard(AppLocalizations t) => HmsCard(
    padding: const EdgeInsets.all(AppSpacing.x4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsTextField(
          key: const Key('reception-search'),
          label: t.receptionSearchHint,
          controller: _query,
          textInputAction: TextInputAction.search,
          onSubmitted: (_) => _search(),
        ),
        const SizedBox(height: AppSpacing.x3),
        HmsButton(
          key: const Key('reception-search-submit'),
          label: t.receptionSearch,
          icon: LucideIcons.search,
          surface: HmsSurface.card,
          loading: _searching,
          onPressed: _search,
        ),
        if (_searchError != null) ...[
          const SizedBox(height: AppSpacing.x3),
          HmsAlert(tone: AlertTone.danger, title: _searchError!),
        ],
        if (_results != null) ...[
          const SizedBox(height: AppSpacing.x3),
          if (_results!.isEmpty)
            HmsEmptyState(compact: true, title: t.receptionNoResults)
          else
            HmsDividedColumn(
              children: [
                for (final p in _results!)
                  Padding(
                    padding: AppSpacing.cardRow,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          p.name,
                          style: AppTypography.body(weight: FontWeight.w600),
                        ),
                        Text(
                          [
                            if (p.uhid != null) '${t.patientId}: ${p.uhid}',
                            if (p.age != null) t.ageYears('${p.age}'),
                            ?p.gender,
                            ?p.phone,
                          ].join(' · '),
                          style: AppTypography.small(),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
        ],
      ],
    ),
  );

  Widget _registerCard(AppLocalizations t) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(title: t.receptionRegisterTitle),
        Padding(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_registered != null) ...[
                HmsAlert(tone: AlertTone.success, title: _registered!),
                const SizedBox(height: AppSpacing.x3),
              ],
              if (_registerError != null) ...[
                HmsAlert(tone: AlertTone.warning, title: _registerError!),
                const SizedBox(height: AppSpacing.x3),
              ],
              HmsTextField(
                key: const Key('reception-name'),
                label: t.fullName,
                controller: _name,
                required: true,
              ),
              const SizedBox(height: AppSpacing.x3),
              HmsTextField(
                key: const Key('reception-phone'),
                label: t.mobileNumber,
                controller: _phone,
                required: true,
                prefixText: '+91 ',
                keyboardType: TextInputType.phone,
                maxLength: _phoneDigits,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              ),
              const SizedBox(height: AppSpacing.x3),
              Text(
                t.gender,
                style: AppTypography.small(weight: FontWeight.w500),
              ),
              const SizedBox(height: AppSpacing.x1_5),
              DropdownButtonFormField<String>(
                key: const Key('reception-gender'),
                initialValue: _gender,

                items: [
                  DropdownMenuItem(
                    value: 'Female',
                    child: Text(t.genderFemale),
                  ),
                  DropdownMenuItem(value: 'Male', child: Text(t.genderMale)),
                  DropdownMenuItem(value: 'Other', child: Text(t.genderOther)),
                ],
                onChanged: (value) =>
                    setState(() => _gender = value ?? _gender),
              ),
              const SizedBox(height: AppSpacing.x3),
              _DobButton(
                key: const Key('reception-dob'),
                value: _dob,
                onPick: () async {
                  final picked = await _pickDob(_dob);
                  if (picked != null && mounted) setState(() => _dob = picked);
                },
              ),
              const SizedBox(height: AppSpacing.x4),
              HmsButton(
                key: const Key('reception-register'),
                label: t.receptionRegister,
                icon: LucideIcons.userPlus,
                surface: HmsSurface.card,
                loading: _registering,
                onPressed: _register,
              ),
              if (_offerRegisterAnyway) ...[
                const SizedBox(height: AppSpacing.x2),
                HmsButton(
                  key: const Key('reception-register-anyway'),
                  label: t.receptionRegisterAnyway,
                  variant: HmsButtonVariant.secondary,
                  surface: HmsSurface.card,
                  onPressed: _registering
                      ? null
                      : () => _register(confirmNew: true),
                ),
              ],
            ],
          ),
        ),
      ],
    ),
  );

  Widget _linkCard(AppLocalizations t) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(
          title: t.receptionLinkTitle,
          description: t.receptionLinkIntro,
        ),
        Padding(
          padding: const EdgeInsets.all(AppSpacing.x4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_linked != null) ...[
                HmsAlert(tone: AlertTone.success, title: _linked!),
                const SizedBox(height: AppSpacing.x3),
              ],
              if (_linkError != null) ...[
                HmsAlert(tone: AlertTone.warning, title: _linkError!),
                const SizedBox(height: AppSpacing.x3),
              ],
              HmsTextField(
                key: const Key('reception-link-phone'),
                label: t.mobileNumber,
                controller: _linkPhone,
                required: true,
                prefixText: '+91 ',
                keyboardType: TextInputType.phone,
                maxLength: _phoneDigits,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              ),
              const SizedBox(height: AppSpacing.x3),
              _DobButton(
                key: const Key('reception-link-dob'),
                value: _linkDob,
                onPick: () async {
                  final picked = await _pickDob(_linkDob);
                  if (picked != null && mounted) {
                    setState(() => _linkDob = picked);
                  }
                },
              ),
              const SizedBox(height: AppSpacing.x4),
              HmsButton(
                key: const Key('reception-link'),
                label: t.receptionLink,
                icon: LucideIcons.link,
                surface: HmsSurface.card,
                loading: _linking,
                onPressed: _link,
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _DobButton extends StatelessWidget {
  const _DobButton({super.key, required this.value, required this.onPick});

  final DateTime? value;
  final VoidCallback onPick;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '${t.dateOfBirth} *',
          style: AppTypography.small(weight: FontWeight.w500),
        ),
        const SizedBox(height: AppSpacing.x1_5),
        HmsButton(
          label: value == null ? t.chooseDateOfBirth : formatDay(t, value),
          icon: LucideIcons.calendarDays,
          variant: HmsButtonVariant.secondary,
          surface: HmsSurface.card,
          onPressed: onPick,
        ),
      ],
    );
  }
}

/// `/appointments` for the front desk: the day's bookings, each with its
/// status; a booking for today is checked in here, which issues its queue
/// token (the server returns the same token if it was already issued).
class ReceptionAppointmentsScreen extends StatefulWidget {
  const ReceptionAppointmentsScreen({super.key, this.now});

  final DateTime Function()? now;

  @override
  State<ReceptionAppointmentsScreen> createState() =>
      _ReceptionAppointmentsScreenState();
}

class _ReceptionAppointmentsScreenState
    extends State<ReceptionAppointmentsScreen> {
  late DateTime _day = today(widget.now);
  late final RecordLoader<List<Appointment>> _loader = RecordLoader(
    () => AppScope.read(context).doctor.appointments(date: _day),
  );
  final Set<int> _busy = {};
  String? _notice;
  String? _error;

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

  Future<void> _pickDay() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _day,
      firstDate: _day.subtract(const Duration(days: 365)),
      lastDate: _day.add(const Duration(days: 365)),
    );
    if (picked == null || picked == _day) return;
    setState(() {
      _day = picked;
      _notice = null;
      _error = null;
    });
    await _loader.load();
  }

  Future<void> _checkIn(Appointment appointment) async {
    if (_busy.contains(appointment.id)) return;
    final t = context.l10n;
    setState(() {
      _busy.add(appointment.id);
      _notice = null;
      _error = null;
    });
    try {
      final token = await AppScope.read(context).reception
          .checkIn(appointment.id);
      if (mounted) {
        setState(
          () => _notice = t.receptionCheckedIn(
            appointment.patientName ?? '',
            '${token.tokenNumber ?? '—'}',
          ),
        );
      }
    } catch (error) {
      if (mounted) setState(() => _error = apiErrorMessage(t, error));
    } finally {
      if (mounted) setState(() => _busy.remove(appointment.id));
    }
    await _loader.load();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final isToday = _day == today(widget.now);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.navAppointments,
          description: t.receptionAppointmentsIntro,
          actions: [
            HmsButton(
              label: formatDay(t, _day),
              icon: LucideIcons.calendarDays,
              variant: HmsButtonVariant.secondary,
              onPressed: _pickDay,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        if (_notice != null) ...[
          HmsAlert(tone: AlertTone.success, title: _notice!),
          const SizedBox(height: AppSpacing.x4),
        ],
        if (_error != null) ...[
          HmsAlert(tone: AlertTone.danger, title: _error!),
          const SizedBox(height: AppSpacing.x4),
        ],
        RecordSection<List<Appointment>>(
          loader: _loader,
          builder: (context, rows) {
            if (rows.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(title: t.receptionNoAppointments),
              );
            }
            final sorted = [...rows]
              ..sort((a, b) => (a.time ?? '').compareTo(b.time ?? ''));
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final a in sorted)
                    Padding(
                      padding: AppSpacing.cardRow,
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  a.patientName ?? '—',
                                  style: AppTypography.body(
                                    weight: FontWeight.w600,
                                  ),
                                ),
                                Text(
                                  [?a.time, ?a.doctorName].join(' · '),
                                  style: AppTypography.small(),
                                ),
                              ],
                            ),
                          ),
                          StatusBadge(status: a.status),
                          if (isToday &&
                              a.status == AppointmentStatus.scheduled) ...[
                            const SizedBox(width: AppSpacing.x2),
                            HmsButton(
                              key: ValueKey('check-in-${a.id}'),
                              label: t.receptionCheckIn,
                              size: HmsButtonSize.small,
                              surface: HmsSurface.card,
                              loading: _busy.contains(a.id),
                              onPressed: _busy.contains(a.id)
                                  ? null
                                  : () => _checkIn(a),
                            ),
                          ],
                        ],
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}
