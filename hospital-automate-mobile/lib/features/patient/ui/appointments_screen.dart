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
import '../data/appointment_models.dart';
import '../record_loader.dart';
import 'patient_routes.dart';
import 'patient_ui.dart';

enum AppointmentFilter { all, upcoming, past, cancelled }

/// The web portal's filter rules (PatientAppointments.jsx).
bool matchesFilter(Appointment a, AppointmentFilter filter) => switch (filter) {
  AppointmentFilter.all => true,
  AppointmentFilter.upcoming => a.isUpcoming,
  AppointmentFilter.past =>
    a.status == AppointmentStatus.completed ||
        a.status == AppointmentStatus.noShow,
  AppointmentFilter.cancelled => a.status == AppointmentStatus.cancelled,
};

/// `/patient/appointments`: the patient's bookings at the selected hospital.
class AppointmentsScreen extends StatefulWidget {
  const AppointmentsScreen({super.key});

  @override
  State<AppointmentsScreen> createState() => _AppointmentsScreenState();
}

class _AppointmentsScreenState extends State<AppointmentsScreen> {
  late final RecordLoader<List<Appointment>> _loader = RecordLoader(
    AppScope.read(context).patient.appointments,
  );
  AppointmentFilter _filter = AppointmentFilter.all;

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
    final labels = {
      AppointmentFilter.all: t.filterAll,
      AppointmentFilter.upcoming: t.filterUpcoming,
      AppointmentFilter.past: t.filterPast,
      AppointmentFilter.cancelled: t.filterCancelled,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: t.patientNavAppointments,
          description: t.appointmentsIntro,
          actions: [
            HmsButton(
              label: t.bookAppointment,
              icon: LucideIcons.calendarPlus,
              onPressed: () => context.go(PatientRoutes.book),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(title: t.appointmentChangesAtHospital),
        const SizedBox(height: AppSpacing.x4),
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final filter in AppointmentFilter.values)
              ChoiceChip(
                label: Text(labels[filter]!),
                selected: _filter == filter,
                onSelected: (_) => setState(() => _filter = filter),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<Appointment>>(
          loader: _loader,
          builder: (context, appointments) {
            final shown = [
              for (final a in appointments)
                if (matchesFilter(a, _filter)) a,
            ]..sort((a, b) => b.sortKey.compareTo(a.sortKey));
            if (shown.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.calendarDays,
                  title: appointments.isEmpty
                      ? t.noAppointmentsYet
                      : t.noAppointmentsMatch,
                  description: appointments.isEmpty
                      ? t.noAppointmentsYetHint
                      : null,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [
                  for (final a in shown) AppointmentRow(appointment: a),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

/// One appointment; tapping opens its details.
class AppointmentRow extends StatelessWidget {
  const AppointmentRow({super.key, required this.appointment});

  final Appointment appointment;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final a = appointment;
    return InkWell(
      onTap: () => showAppointmentDetails(context, a),
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
                    a.doctorName ?? t.doctor,
                    style: AppTypography.body(weight: FontWeight.w600),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    [formatDay(t, a.date), ?a.time].join(' · '),
                    style: AppTypography.small(),
                  ),
                  if (a.hospitalName != null)
                    Text(a.hospitalName!, style: AppTypography.caption()),
                  // Under the text, not beside it, so a long Hindi status never squeezes the name.
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

Future<void> showAppointmentDetails(BuildContext context, Appointment a) {
  final t = context.l10n;
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.x4),
        child: HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.appointmentDetails,
                icon: LucideIcons.calendarDays,
                trailing: StatusBadge(status: a.status),
              ),
              HmsDividedColumn(
                children: [
                  DetailRow(label: t.appointmentId, value: '#${a.id}'),
                  DetailRow(label: t.doctor, value: a.doctorName),
                  DetailRow(label: t.hospital, value: a.hospitalName),
                  DetailRow(label: t.date, value: formatDay(t, a.date)),
                  DetailRow(label: t.timeLabel, value: a.time),
                  DetailRow(label: t.reasonForVisit, value: a.reason),
                ],
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
