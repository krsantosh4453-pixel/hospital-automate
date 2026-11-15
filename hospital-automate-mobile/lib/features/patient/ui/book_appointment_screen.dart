import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../data/appointment_models.dart';
import '../data/patient_repository.dart';
import 'patient_routes.dart';
import 'patient_ui.dart';

/// What the patient sees when the server refuses a booking. Known refusals
/// get their own sentence; the server's raw text is never shown.
String bookingErrorMessage(AppLocalizations t, Object error) {
  if (error is! ApiException) return t.errorUnknown;
  if (error.kind == ApiErrorKind.conflict) return t.bookingSlotTaken;
  if (error.kind != ApiErrorKind.validation) return apiErrorMessage(t, error);
  if (error.fieldErrors.containsKey('appointment_time')) {
    return t.bookingSlotUnavailable;
  }
  if (error.fieldErrors.containsKey('appointment_date')) {
    return t.bookingDateInvalid;
  }
  if (error.fieldErrors.containsKey('doctor')) {
    return t.bookingDoctorUnavailable;
  }
  if (error.serverMessage?.contains('upcoming appointments') ?? false) {
    return t.bookingLimitReached;
  }
  return t.bookingRejected;
}

/// Patient self-booking (web BookAppointmentModal): hospital → doctor →
/// date → free slot. The server re-checks every rule, so this screen only
/// guides; it never decides that a booking succeeded.
class BookAppointmentScreen extends StatefulWidget {
  const BookAppointmentScreen({super.key, this.today});

  /// For tests: the day the date picker treats as today.
  final DateTime Function()? today;

  @override
  State<BookAppointmentScreen> createState() => _BookAppointmentScreenState();
}

class _BookAppointmentScreenState extends State<BookAppointmentScreen> {
  late final PatientRepository _repository = AppScope.read(context).patient;
  final _reason = TextEditingController();

  BookingOptions _options = const BookingOptions();
  List<BookingDoctor> _doctors = const [];
  List<BookingSlot> _slots = const [];
  int? _hospitalId;
  int? _doctorId;
  late DateTime _date = _today().add(const Duration(days: 1));
  String? _time;

  bool _loadingOptions = true;
  bool _loadingSlots = false;
  bool _submitting = false;
  Object? _loadError;
  String? _bookingError;
  Appointment? _booked;

  // One key per exact request: a retry of the same request reuses it, so a
  // lost response cannot turn into a second booking.
  BookingRequest? _keyedRequest;
  String? _idempotencyKey;
  int _slotRequest = 0;

  DateTime _today() {
    final now = (widget.today ?? DateTime.now)();
    return DateTime(now.year, now.month, now.day);
  }

  @override
  void initState() {
    super.initState();
    _loadHospitals();
  }

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _loadHospitals() async {
    setState(() {
      _loadingOptions = true;
      _loadError = null;
    });
    try {
      final options = await _repository.bookingOptions();
      if (!mounted) return;
      final ids = options.hospitals.map((h) => h.id).toList();
      final active = AppScope.read(context).session.activeHospitalId;
      setState(() {
        _options = options;
        _loadingOptions = false;
      });
      final preferred = ids.contains(active)
          ? active
          : (ids.length == 1 ? ids.single : null);
      if (preferred != null) await _selectHospital(preferred);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loadError = error;
        _loadingOptions = false;
      });
    }
  }

  Future<void> _selectHospital(int id) async {
    setState(() {
      _hospitalId = id;
      _doctorId = null;
      _doctors = const [];
      _slots = const [];
      _time = null;
      _bookingError = null;
    });
    try {
      final options = await _repository.bookingOptions(hospitalId: id);
      if (!mounted || _hospitalId != id) return;
      setState(() => _doctors = options.doctors);
    } catch (error) {
      if (!mounted) return;
      setState(() => _bookingError = bookingErrorMessage(context.l10n, error));
    }
  }

  Future<void> _loadSlots() async {
    final hospital = _hospitalId;
    final doctor = _doctorId;
    if (hospital == null || doctor == null) return;
    final request = ++_slotRequest;
    setState(() {
      _loadingSlots = true;
      _time = null;
    });
    try {
      final options = await _repository.bookingOptions(
        hospitalId: hospital,
        doctorId: doctor,
        date: _date,
      );
      if (!mounted || request != _slotRequest) return;
      setState(() {
        _slots = options.slots;
        _loadingSlots = false;
      });
    } catch (error) {
      if (!mounted || request != _slotRequest) return;
      setState(() {
        _slots = const [];
        _loadingSlots = false;
        _bookingError = bookingErrorMessage(context.l10n, error);
      });
    }
  }

  Future<void> _pickDate() async {
    final today = _today();
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: today,
      lastDate: today.add(Duration(days: _options.windowDays)),
    );
    if (picked == null || picked == _date) return;
    setState(() {
      _date = picked;
      _bookingError = null;
    });
    await _loadSlots();
  }

  BookingRequest? get _request {
    final doctor = _doctorId;
    final time = _time;
    if (doctor == null || time == null) return null;
    return BookingRequest(
      doctorId: doctor,
      date: _date,
      time: time,
      reason: _reason.text,
    );
  }

  Future<void> _submit() async {
    final request = _request;
    if (request == null || _submitting) return;
    if (request != _keyedRequest) {
      _keyedRequest = request;
      _idempotencyKey = ApiClient.newIdempotencyKey();
    }
    setState(() {
      _submitting = true;
      _bookingError = null;
    });
    try {
      final booked = await _repository.book(request, _idempotencyKey!);
      if (!mounted) return;
      setState(() {
        _booked = booked;
        _submitting = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _bookingError = bookingErrorMessage(context.l10n, error);
      });
      // The slot may have just been taken: show the free times again.
      if (error is ApiException && error.kind == ApiErrorKind.conflict) {
        await _loadSlots();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final booked = _booked;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.bookAppointment,
          description: t.bookAppointmentIntro,
        ),
        const SizedBox(height: AppSpacing.x6),
        if (booked != null)
          _Confirmation(appointment: booked)
        else if (_loadingOptions)
          const HmsLoading()
        else if (_loadError != null)
          HmsCard(
            child: HmsErrorState(error: _loadError!, onRetry: _loadHospitals),
          )
        else
          _form(t),
      ],
    );
  }

  Widget _form(AppLocalizations t) {
    final freeSlots = [
      for (final slot in _slots)
        if (slot.available) slot,
    ];
    return HmsCard(
      padding: const EdgeInsets.all(AppSpacing.x4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_options.hospitals.isEmpty) ...[
            HmsAlert(tone: AlertTone.warning, title: t.bookingNoHospital),
            const SizedBox(height: AppSpacing.x4),
          ],
          if (_bookingError != null) ...[
            HmsAlert(tone: AlertTone.danger, title: _bookingError!),
            const SizedBox(height: AppSpacing.x4),
          ],
          _Label(t.hospital),
          DropdownButtonFormField<int>(
            // initialValue is read once, so a new key shows an automatic choice.
            key: ValueKey('booking-hospital-$_hospitalId'),
            initialValue: _hospitalId,
            isExpanded: true,
            hint: Text(t.selectHospital),
            items: [
              for (final h in _options.hospitals)
                DropdownMenuItem(value: h.id, child: Text(h.name)),
            ],
            onChanged: _submitting
                ? null
                : (id) => id == null ? null : _selectHospital(id),
          ),
          const SizedBox(height: AppSpacing.x4),
          _Label(t.doctor),
          DropdownButtonFormField<int>(
            key: ValueKey('booking-doctor-$_hospitalId'),
            initialValue: _doctorId,
            isExpanded: true,
            hint: Text(t.selectDoctor),
            items: [
              for (final d in _doctors)
                DropdownMenuItem(
                  value: d.id,
                  child: Text(
                    [d.name, ?d.specialization].join(' — '),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: _hospitalId == null || _submitting
                ? null
                : (id) {
                    setState(() {
                      _doctorId = id;
                      _bookingError = null;
                    });
                    _loadSlots();
                  },
          ),
          const SizedBox(height: AppSpacing.x4),
          _Label(t.date),
          HmsButton(
            label: formatDay(t, _date),
            icon: LucideIcons.calendarDays,
            variant: HmsButtonVariant.secondary,
            surface: HmsSurface.card,
            onPressed: _submitting ? null : _pickDate,
          ),
          const SizedBox(height: AppSpacing.x4),
          _Label(t.timeLabel),
          if (_doctorId == null)
            Text(t.chooseDoctorFirst, style: AppTypography.small())
          else if (_loadingSlots)
            const HmsLoading()
          else if (freeSlots.isEmpty)
            Text(t.noFreeSlots, style: AppTypography.small())
          else
            Wrap(
              spacing: AppSpacing.x2,
              runSpacing: AppSpacing.x2,
              children: [
                for (final slot in freeSlots)
                  ChoiceChip(
                    label: Text(slot.time),
                    selected: _time == slot.time,
                    onSelected: _submitting
                        ? null
                        : (_) => setState(() {
                            _time = slot.time;
                            _bookingError = null;
                          }),
                  ),
              ],
            ),
          const SizedBox(height: AppSpacing.x4),
          _Label(t.reasonForVisit),
          TextField(
            controller: _reason,
            maxLength: BookingRequest.maxReasonLength,
            maxLines: 3,
            enabled: !_submitting,
          ),
          const SizedBox(height: AppSpacing.x4),
          HmsButton(
            key: const Key('booking-submit'),
            label: t.confirmBooking,
            loading: _submitting,
            expand: true,
            surface: HmsSurface.card,
            onPressed: _request == null || _submitting ? null : _submit,
          ),
        ],
      ),
    );
  }
}

class _Label extends StatelessWidget {
  const _Label(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.x1_5),
    child: Text(text, style: AppTypography.small(weight: FontWeight.w600)),
  );
}

/// Shown only after the server answered 200/201 with the booking.
class _Confirmation extends StatelessWidget {
  const _Confirmation({required this.appointment});

  final Appointment appointment;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsAlert(
          tone: AlertTone.success,
          title: t.bookingConfirmed,
          message: t.bookingConfirmedBody,
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          child: HmsDividedColumn(
            children: [
              DetailRow(label: t.appointmentId, value: '#${appointment.id}'),
              DetailRow(label: t.doctor, value: appointment.doctorName),
              DetailRow(label: t.hospital, value: appointment.hospitalName),
              DetailRow(label: t.date, value: formatDay(t, appointment.date)),
              DetailRow(label: t.timeLabel, value: appointment.time),
              DetailRow(
                label: t.status,
                value: statusLabel(t, appointment.status),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsButton(
          label: t.viewMyAppointments,
          expand: true,
          onPressed: () => context.go(PatientRoutes.appointments),
        ),
      ],
    );
  }
}
