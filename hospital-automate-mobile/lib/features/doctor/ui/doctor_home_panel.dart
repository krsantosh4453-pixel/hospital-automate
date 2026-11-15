import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/security/session_controller.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../patient/data/appointment_models.dart';
import '../../patient/data/record_models.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/doctor_models.dart';
import '../data/doctor_repository.dart';
import 'doctor_ui.dart';

/// What the doctor's home shows, each part loaded on its own: a part that
/// fails is null and shows "not available", the others still show.
class DoctorDay {
  const DoctorDay({this.profile, this.appointments, this.queue, this.visits});

  static Future<DoctorDay> load(
    DoctorRepository repository, {
    required int hospitalId,
    required int? userId,
    required DateTime day,
  }) async {
    Future<T?> settle<T>(Future<T> future) async {
      try {
        return await future;
      } on ApiException {
        return null;
      }
    }

    final profile = userId == null
        ? Future<DoctorProfile?>.value()
        : settle<DoctorProfile?>(
            repository.myProfile(hospitalId: hospitalId, userId: userId),
          );
    final results = await Future.wait(<Future<Object?>>[
      profile,
      settle(repository.appointments(date: day)),
      settle(repository.queue(date: day)),
      settle(repository.visits()),
    ]);
    return DoctorDay(
      profile: results[0] as DoctorProfile?,
      appointments: results[1] as List<Appointment>?,
      queue: results[2] as List<QueueToken>?,
      visits: results[3] as List<Visit>?,
    );
  }

  final DoctorProfile? profile;
  final List<Appointment>? appointments;
  final List<QueueToken>? queue;
  final List<Visit>? visits;

  int? _count(Iterable<QueueToken>? tokens, Set<String> statuses) =>
      tokens?.where((t) => statuses.contains(t.status)).length;

  QueueToken? get serving {
    for (final token in queue ?? const <QueueToken>[]) {
      if (token.status == 'In Consultation') return token;
    }
    return null;
  }

  int? get waiting =>
      _count(queue, {'Waiting', 'Called', 'Acknowledged', 'Ready'});
  int? get completedToday => _count(queue, {'Completed'});

  /// Completed consultations, newest first.
  List<Visit> recentConsultations(int count) =>
      ([
            for (final v in visits ?? const <Visit>[])
              if (v.status == Visit.completed) v,
          ]..sort(
            (a, b) => (b.visitDate ?? DateTime(0)).compareTo(
              a.visitDate ?? DateTime(0),
            ),
          ))
          .take(count)
          .toList();
}

/// The doctor's part of the staff home (below the role dashboard).
class DoctorHomePanel extends StatefulWidget {
  const DoctorHomePanel({
    super.key,
    required this.repository,
    required this.session,
    this.now,
  });

  final DoctorRepository repository;
  final SessionState session;
  final DateTime Function()? now;

  @override
  State<DoctorHomePanel> createState() => _DoctorHomePanelState();
}

class _DoctorHomePanelState extends State<DoctorHomePanel> {
  late final RecordLoader<DoctorDay> _loader = RecordLoader(
    () => DoctorDay.load(
      widget.repository,
      hospitalId: widget.session.activeHospitalId!,
      userId: widget.session.user?.id,
      day: today(widget.now),
    ),
  );

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
  Widget build(BuildContext context) => RecordSection<DoctorDay>(
    loader: _loader,
    skeletons: 2,
    builder: (context, day) =>
        _DayBody(day: day, hospital: widget.session.activeHospital?.name),
  );
}

class _DayBody extends StatelessWidget {
  const _DayBody({required this.day, required this.hospital});

  final DoctorDay day;
  final String? hospital;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final profile = day.profile;
    final serving = day.serving;
    final appointments = [...?day.appointments]
      ..sort((a, b) => a.sortKey.compareTo(b.sortKey));
    Widget unavailable() =>
        HmsEmptyState(compact: true, title: t.notAvailableNow);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.myDoctorProfile,
                icon: LucideIcons.stethoscope,
              ),
              if (profile == null)
                HmsEmptyState(compact: true, title: t.doctorProfileMissing)
              else
                HmsDividedColumn(
                  children: [
                    DetailRow(label: t.name, value: profile.name),
                    DetailRow(
                      label: t.specialization,
                      value: [
                        ?profile.specialization,
                        ?profile.department,
                      ].join(' · '),
                    ),
                    DetailRow(
                      label: t.registration,
                      value: [
                        ?profile.registrationNumber,
                        ?profile.registrationCouncil,
                        profile.registrationVerified
                            ? t.verified
                            : t.notVerified,
                      ].join(' · '),
                    ),
                    DetailRow(label: t.mobileNumber, value: profile.phone),
                    DetailRow(label: t.selectedHospital, value: hospital),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        StatTileGrid(
          children: [
            StatTile(
              label: t.nowServing,
              value: serving == null
                  ? (day.queue == null ? null : t.none)
                  : '#${serving.tokenNumber ?? '—'}',
              icon: LucideIcons.userRoundCheck,
            ),
            StatTile(
              label: t.waitingPatients,
              value: day.waiting?.toString(),
              icon: LucideIcons.listOrdered,
              tone: HmsTone.warning,
            ),
            StatTile(
              label: t.completedToday,
              value: day.completedToday?.toString(),
              icon: LucideIcons.circleCheck,
              tone: HmsTone.success,
            ),
            StatTile(
              label: t.todaysAppointments,
              value: day.appointments?.length.toString(),
              icon: LucideIcons.calendarDays,
              tone: HmsTone.accent,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.todaysAppointments,
                icon: LucideIcons.calendarDays,
                trailing: TextButton(
                  onPressed: () => context.go(DoctorRoutes.appointments),
                  child: Text(
                    t.viewAll,
                    style: AppTypography.small(color: AppColors.onCard),
                  ),
                ),
              ),
              if (day.appointments == null)
                unavailable()
              else if (appointments.isEmpty)
                HmsEmptyState(compact: true, title: t.noAppointmentsToday)
              else
                HmsDividedColumn(
                  children: [
                    for (final a in appointments.take(5))
                      DetailRow(
                        label: a.time ?? '—',
                        value:
                            '${a.patientName ?? t.patientLabel} · ${statusLabel(t, a.status)}',
                      ),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.recentConsultations,
                icon: LucideIcons.history,
                trailing: TextButton(
                  onPressed: () => context.go(DoctorRoutes.consultation),
                  child: Text(
                    t.viewAll,
                    style: AppTypography.small(color: AppColors.onCard),
                  ),
                ),
              ),
              if (day.visits == null)
                unavailable()
              else if (day.recentConsultations(3).isEmpty)
                HmsEmptyState(compact: true, title: t.noConsultationsYet)
              else
                HmsDividedColumn(
                  children: [
                    for (final v in day.recentConsultations(3))
                      InkWell(
                        onTap: () => context.go(DoctorRoutes.visit(v.id)),
                        child: DetailRow(
                          label: formatDateTime(t, v.visitDate),
                          value: v.patientName ?? t.patientLabel,
                        ),
                      ),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(tone: AlertTone.info, title: t.noDoctorInbox),
      ],
    );
  }
}
