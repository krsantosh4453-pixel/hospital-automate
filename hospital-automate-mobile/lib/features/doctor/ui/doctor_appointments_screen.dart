import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../patient/data/appointment_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import 'doctor_ui.dart';

/// Which days the list shows.
enum AppointmentRange { today, upcoming, past, day }

/// `Appointment.Status` values (backend/appointments/models.py), for the filter.
const appointmentStatuses = [
  AppointmentStatus.scheduled,
  AppointmentStatus.checkedIn,
  AppointmentStatus.inConsultation,
  AppointmentStatus.completed,
  AppointmentStatus.cancelled,
  AppointmentStatus.noShow,
];

/// Keeps the rows of [range] (relative to [day0]); [picked] for a chosen day.
List<Appointment> appointmentsIn(
  List<Appointment> rows,
  AppointmentRange range,
  DateTime day0, {
  DateTime? picked,
}) {
  bool keep(Appointment a) {
    final date = a.date;
    if (date == null) return range == AppointmentRange.upcoming;
    return switch (range) {
      AppointmentRange.today => date == day0,
      AppointmentRange.upcoming => date.isAfter(day0),
      AppointmentRange.past => date.isBefore(day0),
      AppointmentRange.day => date == picked,
    };
  }

  final kept = [
    for (final a in rows)
      if (keep(a)) a,
  ];
  kept.sort(
    (a, b) => range == AppointmentRange.past
        ? b.sortKey.compareTo(a.sortKey)
        : a.sortKey.compareTo(b.sortKey),
  );
  return kept;
}

/// `/appointments` for a doctor: the bookings under their own profile (the
/// server returns only those). Read-only: the doctor's web pages do not
/// change bookings, so the app offers no change either.
class DoctorAppointmentsScreen extends StatefulWidget {
  const DoctorAppointmentsScreen({super.key, this.now});

  final DateTime Function()? now;

  @override
  State<DoctorAppointmentsScreen> createState() =>
      _DoctorAppointmentsScreenState();
}

class _DoctorAppointmentsScreenState extends State<DoctorAppointmentsScreen> {
  late final _repository = AppScope.read(context).doctor;
  late final RecordLoader<List<Appointment>> _loader = RecordLoader(
    () => _repository.appointments(status: _status),
  );
  AppointmentRange _range = AppointmentRange.today;
  DateTime? _picked;
  String? _status;
  final _search = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loader.load();
  }

  @override
  void dispose() {
    _search.dispose();
    _loader.dispose();
    super.dispose();
  }

  Future<void> _pickDay() async {
    final day0 = today(widget.now);
    final picked = await showDatePicker(
      context: context,
      initialDate: _picked ?? day0,
      firstDate: day0.subtract(const Duration(days: 365)),
      lastDate: day0.add(const Duration(days: 365)),
    );
    if (picked == null) return;
    setState(() {
      _picked = picked;
      _range = AppointmentRange.day;
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final ranges = {
      AppointmentRange.today: t.filterToday,
      AppointmentRange.upcoming: t.filterUpcoming,
      AppointmentRange.past: t.filterPast,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.navAppointments,
          description: t.doctorAppointmentsIntro,
        ),
        const SizedBox(height: AppSpacing.x4),
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final entry in ranges.entries)
              ChoiceChip(
                label: Text(entry.value),
                selected: _range == entry.key,
                onSelected: (_) => setState(() => _range = entry.key),
              ),
            ChoiceChip(
              avatar: const Icon(LucideIcons.calendarDays, size: 16),
              label: Text(
                _range == AppointmentRange.day && _picked != null
                    ? formatDay(t, _picked)
                    : t.pickDate,
              ),
              selected: _range == AppointmentRange.day,
              onSelected: (_) => _pickDay(),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x3),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String?>(
                key: const Key('appointment-status-filter'),
                initialValue: _status,
                isExpanded: true,
                decoration: InputDecoration(labelText: t.status),
                items: [
                  DropdownMenuItem(value: null, child: Text(t.filterAll)),
                  for (final status in appointmentStatuses)
                    DropdownMenuItem(
                      value: status,
                      child: Text(statusLabel(t, status)),
                    ),
                ],
                onChanged: (status) {
                  setState(() => _status = status);
                  _loader.load();
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x3),
        TextField(
          controller: _search,
          decoration: InputDecoration(
            prefixIcon: const Icon(LucideIcons.search, size: 18),
            hintText: t.searchPatientName,
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<Appointment>>(
          loader: _loader,
          builder: (context, rows) {
            final query = _search.text.trim().toLowerCase();
            final shown = [
              for (final a in appointmentsIn(
                rows,
                _range,
                today(widget.now),
                picked: _picked,
              ))
                if (query.isEmpty ||
                    (a.patientName ?? '').toLowerCase().contains(query))
                  a,
            ];
            if (shown.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.calendarDays,
                  title: t.noAppointmentsMatch,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final a in shown) _AppointmentRow(appointment: a),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _AppointmentRow extends StatelessWidget {
  const _AppointmentRow({required this.appointment});

  final Appointment appointment;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final a = appointment;
    return InkWell(
      onTap: () => _showDetails(context, a),
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            DayTile(day: a.date),
            const SizedBox(width: AppSpacing.x3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    a.patientName ?? t.patientLabel,
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  Text(
                    [formatDay(t, a.date), ?a.time].join(' · '),
                    style: AppTypography.small(),
                  ),
                  const SizedBox(height: AppSpacing.x1),
                  StatusBadge(status: a.status),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> _showDetails(BuildContext context, Appointment a) {
  final t = context.l10n;
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (sheet) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.x4),
        child: HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: a.patientName ?? t.patientLabel,
                icon: LucideIcons.calendarDays,
                trailing: StatusBadge(status: a.status),
              ),
              HmsDividedColumn(
                children: [
                  DetailRow(label: t.appointmentId, value: '#${a.id}'),
                  DetailRow(label: t.date, value: formatDay(t, a.date)),
                  DetailRow(label: t.timeLabel, value: a.time),
                  DetailRow(label: t.hospital, value: a.hospitalName),
                  DetailRow(label: t.reasonForVisit, value: a.reason),
                ],
              ),
              Padding(
                padding: const EdgeInsets.all(AppSpacing.x4),
                child: Wrap(
                  spacing: AppSpacing.x2,
                  runSpacing: AppSpacing.x2,
                  children: [
                    if (a.patientId != null)
                      HmsButton(
                        label: t.openPatientRecord,
                        surface: HmsSurface.card,
                        onPressed: () {
                          Navigator.of(sheet).pop();
                          context.go(DoctorRoutes.patient(a.patientId!));
                        },
                      ),
                    HmsButton(
                      label: t.navQueue,
                      surface: HmsSurface.card,
                      variant: HmsButtonVariant.secondary,
                      onPressed: () {
                        Navigator.of(sheet).pop();
                        context.go(DoctorRoutes.queue);
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
