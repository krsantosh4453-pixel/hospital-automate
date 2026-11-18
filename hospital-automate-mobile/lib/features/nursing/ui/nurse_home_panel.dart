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
import '../../doctor/ui/doctor_ui.dart' show today;
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/nursing_models.dart';
import '../data/nursing_repository.dart';
import 'nursing_ui.dart';

/// What the nurse's home shows, each part loaded on its own: a part that
/// fails is null and shows "not available", the others still show.
class NurseDay {
  const NurseDay({
    this.profile,
    this.wardDuties,
    this.patientDuties,
    this.admissions,
    this.dueDoses,
    this.tasks,
    this.recentNotes,
  });

  static Future<NurseDay> load(
    NursingRepository repository, {
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
        ? null
        : await settle(
            repository.myProfile(hospitalId: hospitalId, userId: userId),
          );
    final nurseId = profile?.id;
    final results = await Future.wait(<Future<Object?>>[
      if (nurseId != null) ...[
        settle(repository.wardDuties(nurseId: nurseId, day: day)),
        settle(repository.patientDuties(nurseId: nurseId, day: day)),
        settle(repository.careTasks(nurseId: nurseId)),
      ] else ...[
        Future.value(),
        Future.value(),
        Future.value(),
      ],
      settle(repository.admissions()),
      settle(repository.dueDoses(hospitalId)),
      settle(repository.notes()),
    ]);
    return NurseDay(
      profile: profile,
      wardDuties: results[0] as List<DutyAssignment>?,
      patientDuties: results[1] as List<DutyAssignment>?,
      tasks: results[2] as List<CareTask>?,
      admissions: results[3] as List<Admission>?,
      dueDoses: results[4] as List<Dose>?,
      recentNotes: results[5] as List<NursingNote>?,
    );
  }

  final NurseProfile? profile;
  final List<DutyAssignment>? wardDuties;
  final List<DutyAssignment>? patientDuties;
  final List<Admission>? admissions;
  final List<Dose>? dueDoses;
  final List<CareTask>? tasks;
  final List<NursingNote>? recentNotes;

  List<Admission>? get inWard => admissions?.where((a) => a.inWard).toList();

  /// Distinct patients in the ward or assigned to this nurse today.
  int? get patientCount {
    if (inWard == null && patientDuties == null) return null;
    return {
      for (final a in inWard ?? const <Admission>[]) ?a.patientId,
      for (final d in patientDuties ?? const <DutyAssignment>[]) ?d.patientId,
    }.length;
  }

  List<CareTask>? get openTasks => tasks?.where((t) => t.isOpen).toList();
  int? get overdueDoses => dueDoses?.where((d) => d.isDelayed).length;

  /// Shifts on duty today, e.g. "Morning · Ward A".
  List<String> dutyLines(AppLocalizations t) => [
    for (final d in wardDuties ?? const <DutyAssignment>[])
      [shiftLabel(t, d.shift), ?d.wardName].join(' · '),
  ];
}

/// The nurse's part of the staff home (below the role dashboard).
class NurseHomePanel extends StatefulWidget {
  const NurseHomePanel({
    super.key,
    required this.repository,
    required this.session,
    this.now,
  });

  final NursingRepository repository;
  final SessionState session;
  final DateTime Function()? now;

  @override
  State<NurseHomePanel> createState() => _NurseHomePanelState();
}

class _NurseHomePanelState extends State<NurseHomePanel> {
  late final RecordLoader<NurseDay> _loader = RecordLoader(
    () => NurseDay.load(
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
  Widget build(BuildContext context) => RecordSection<NurseDay>(
    loader: _loader,
    skeletons: 2,
    builder: (context, day) =>
        _DayBody(day: day, hospital: widget.session.activeHospital?.name),
  );
}

class _DayBody extends StatelessWidget {
  const _DayBody({required this.day, required this.hospital});

  final NurseDay day;
  final String? hospital;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    Widget unavailable() =>
        HmsEmptyState(compact: true, title: t.notAvailableNow);
    final duties = day.dutyLines(t);
    final attention = _attention(t);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              HmsCardHeader(
                title: t.myNurseProfile,
                icon: LucideIcons.heartPulse,
              ),
              if (day.profile == null)
                HmsEmptyState(compact: true, title: t.nurseProfileMissing)
              else
                HmsDividedColumn(
                  children: [
                    DetailRow(label: t.name, value: day.profile!.name),
                    DetailRow(
                      label: t.department,
                      value: day.profile!.department,
                    ),
                    DetailRow(
                      label: t.qualification,
                      value: day.profile!.qualification,
                    ),
                    DetailRow(label: t.selectedHospital, value: hospital),
                    DetailRow(
                      label: t.todaysShift,
                      value: day.wardDuties == null
                          ? t.notAvailableNow
                          : (duties.isEmpty
                                ? t.noDutyToday
                                : duties.join('\n')),
                    ),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        StatTileGrid(
          children: [
            StatTile(
              label: t.patientsInCare,
              value: day.patientCount?.toString(),
              icon: LucideIcons.bedDouble,
            ),
            StatTile(
              label: t.dosesDue,
              value: day.dueDoses?.length.toString(),
              icon: LucideIcons.pill,
              tone: HmsTone.accent,
            ),
            StatTile(
              label: t.dosesOverdue,
              value: day.overdueDoses?.toString(),
              icon: LucideIcons.alarmClock,
              tone: HmsTone.warning,
            ),
            StatTile(
              label: t.openTasks,
              value: day.openTasks?.length.toString(),
              icon: LucideIcons.clipboardList,
              tone: HmsTone.success,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        _ListCard(
          title: t.wardAttention,
          icon: LucideIcons.triangleAlert,
          onViewAll: () => context.go(NursingRoutes.ward),
          child: day.dueDoses == null && day.tasks == null
              ? unavailable()
              : attention.isEmpty
              ? HmsEmptyState(compact: true, title: t.nothingNeedsAttention)
              : HmsDividedColumn(children: attention),
        ),
        const SizedBox(height: AppSpacing.x4),
        _ListCard(
          title: t.pendingTasks,
          icon: LucideIcons.clipboardList,
          child: day.openTasks == null
              ? unavailable()
              : day.openTasks!.isEmpty
              ? HmsEmptyState(compact: true, title: t.noOpenTasks)
              : HmsDividedColumn(
                  children: [
                    for (final task in day.openTasks!.take(5))
                      _PatientLink(
                        patientId: task.patientId,
                        child: DetailRow(
                          label: formatClock(t, task.scheduledAt),
                          value:
                              '${task.patientName ?? t.patientLabel} · ${task.description}',
                        ),
                      ),
                  ],
                ),
        ),
        const SizedBox(height: AppSpacing.x4),
        _ListCard(
          title: t.recentNursingActivity,
          icon: LucideIcons.history,
          child: day.recentNotes == null
              ? unavailable()
              : day.recentNotes!.isEmpty
              ? HmsEmptyState(compact: true, title: t.noNotesYet)
              : HmsDividedColumn(
                  children: [
                    for (final note in day.recentNotes!.take(5))
                      _PatientLink(
                        patientId: note.patientId,
                        child: DetailRow(
                          label: formatDateTime(t, note.createdAt),
                          value: [
                            noteTypeLabel(t, note.type),
                            ?note.nurseName,
                          ].join(' · '),
                        ),
                      ),
                  ],
                ),
        ),
        const SizedBox(height: AppSpacing.x4),
        HmsAlert(tone: AlertTone.info, title: t.noStaffInbox),
      ],
    );
  }

  /// Overdue doses, urgent open tasks and patients still waiting for a bed.
  List<Widget> _attention(AppLocalizations t) => [
    for (final dose in day.dueDoses ?? const <Dose>[])
      if (dose.isDelayed)
        _PatientLink(
          patientId: dose.patientId,
          child: DetailRow(
            label: t.doseOverdueAt(formatClock(t, dose.scheduledAt)),
            value:
                '${dose.patientName ?? t.patientLabel} · ${dose.medicineName}',
          ),
        ),
    for (final task in day.openTasks ?? const <CareTask>[])
      if (task.isUrgent)
        _PatientLink(
          patientId: task.patientId,
          child: DetailRow(
            label: taskPriorityLabel(t, task.priority),
            value:
                '${task.patientName ?? t.patientLabel} · ${task.description}',
          ),
        ),
    for (final admission in day.inWard ?? const <Admission>[])
      if (admission.awaitingBed && admission.status == 'Admitted')
        _PatientLink(
          patientId: admission.patientId,
          child: DetailRow(
            label: t.awaitingBed,
            value: admission.patientName ?? t.patientLabel,
          ),
        ),
  ];
}

class _ListCard extends StatelessWidget {
  const _ListCard({
    required this.title,
    required this.icon,
    required this.child,
    this.onViewAll,
  });

  final String title;
  final IconData icon;
  final Widget child;
  final VoidCallback? onViewAll;

  @override
  Widget build(BuildContext context) => HmsCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsCardHeader(
          title: title,
          icon: icon,
          trailing: onViewAll == null
              ? null
              : TextButton(
                  onPressed: onViewAll,
                  child: Text(
                    context.l10n.viewAll,
                    style: AppTypography.small(color: AppColors.onCard),
                  ),
                ),
        ),
        child,
      ],
    ),
  );
}

/// A row that opens the patient's ward record when the patient is known.
class _PatientLink extends StatelessWidget {
  const _PatientLink({required this.patientId, required this.child});

  final int? patientId;
  final Widget child;

  @override
  Widget build(BuildContext context) => patientId == null
      ? child
      : InkWell(
          onTap: () => context.go(NursingRoutes.patient(patientId!)),
          child: child,
        );
}
