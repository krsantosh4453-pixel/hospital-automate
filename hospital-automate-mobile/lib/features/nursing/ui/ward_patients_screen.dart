import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_search_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/states.dart';
import '../../doctor/ui/doctor_ui.dart' show today;
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart';
import '../data/nursing_models.dart';
import '../data/nursing_repository.dart';
import 'nursing_ui.dart';

/// One patient on the ward list: their stay (if admitted) and whether they
/// are assigned to this nurse for today's shift.
@immutable
class WardPatient {
  const WardPatient({
    required this.patientId,
    required this.name,
    this.admission,
    this.assignedShift,
  });

  final int patientId;
  final String name;
  final Admission? admission;

  /// The shift this nurse is assigned to the patient today, if any.
  final String? assignedShift;
}

/// Filters the list offers; each matches what the server sent.
enum WardFilter { all, admitted, dischargeInitiated, awaitingBed, assigned }

/// Merges admissions still in the ward with today's assignments, one row
/// per patient, sorted by name. Both lists are already narrowed by the
/// server to this nurse's care.
List<WardPatient> wardPatients(
  List<Admission> admissions,
  List<DutyAssignment> assignments,
) {
  final byPatient = <int, WardPatient>{};
  for (final a in admissions) {
    final id = a.patientId;
    if (id == null || !a.inWard) continue;
    byPatient[id] = WardPatient(
      patientId: id,
      name: a.patientName ?? '',
      admission: a,
    );
  }
  for (final d in assignments) {
    final id = d.patientId;
    if (id == null) continue;
    final known = byPatient[id];
    byPatient[id] = WardPatient(
      patientId: id,
      name: known?.name ?? d.patientName ?? '',
      admission: known?.admission,
      assignedShift: d.shift,
    );
  }
  return byPatient.values.toList()
    ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
}

bool matchesWardFilter(WardPatient p, WardFilter filter) => switch (filter) {
  WardFilter.all => true,
  WardFilter.admitted => p.admission?.status == 'Admitted',
  WardFilter.dischargeInitiated =>
    p.admission?.status == 'Discharge Initiated',
  WardFilter.awaitingBed => p.admission?.awaitingBed ?? false,
  WardFilter.assigned => p.assignedShift != null,
};

bool matchesWardSearch(WardPatient p, String query) {
  final q = query.trim().toLowerCase();
  if (q.isEmpty) return true;
  final a = p.admission;
  return [
    p.name,
    ?a?.wardName,
    ?a?.bedNumber,
  ].any((field) => field.toLowerCase().contains(q));
}

/// `/nurses` for a nurse: the patients of today's duty.
class WardPatientsScreen extends StatefulWidget {
  const WardPatientsScreen({super.key, this.now});

  final DateTime Function()? now;

  @override
  State<WardPatientsScreen> createState() => _WardPatientsScreenState();
}

class _WardPatientsScreenState extends State<WardPatientsScreen> {
  late final NursingRepository _repo = AppScope.read(context).nursing;
  late final RecordLoader<List<WardPatient>> _loader = RecordLoader(_fetch);
  String _query = '';
  WardFilter _filter = WardFilter.all;

  Future<List<WardPatient>> _fetch() async {
    final session = AppScope.read(context).session.state;
    final hospitalId = session.activeHospitalId;
    final userId = session.user?.id;
    final profile = hospitalId == null || userId == null
        ? null
        : await _repo.myProfile(hospitalId: hospitalId, userId: userId);
    final results = await Future.wait<Object>([
      _repo.admissions(),
      if (profile != null)
        _repo.patientDuties(nurseId: profile.id, day: today(widget.now))
      else
        Future.value(const <DutyAssignment>[]),
    ]);
    return wardPatients(
      results[0] as List<Admission>,
      results[1] as List<DutyAssignment>,
    );
  }

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

  String _filterLabel(AppLocalizations t, WardFilter f) => switch (f) {
    WardFilter.all => t.filterAll,
    WardFilter.admitted => t.statusAdmitted,
    WardFilter.dischargeInitiated => t.statusDischargeInitiated,
    WardFilter.awaitingBed => t.awaitingBed,
    WardFilter.assigned => t.assignedToMe,
  };

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.wardPatients, description: t.wardPatientsIntro),
        const SizedBox(height: AppSpacing.x4),
        HmsSearchField(
          hint: t.searchWardPatients,
          onChanged: (value) => setState(() => _query = value),
        ),
        const SizedBox(height: AppSpacing.x3),
        Wrap(
          spacing: AppSpacing.x2,
          runSpacing: AppSpacing.x2,
          children: [
            for (final f in WardFilter.values)
              ChoiceChip(
                label: Text(_filterLabel(t, f)),
                selected: _filter == f,
                onSelected: (_) => setState(() => _filter = f),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<WardPatient>>(
          loader: _loader,
          builder: (context, patients) {
            final shown = [
              for (final p in patients)
                if (matchesWardFilter(p, _filter) &&
                    matchesWardSearch(p, _query))
                  p,
            ];
            if (shown.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.bedDouble,
                  title: patients.isEmpty
                      ? t.noWardPatients
                      : t.noPatientsFound,
                  description: patients.isEmpty ? t.noWardPatientsHint : null,
                ),
              );
            }
            return HmsCard(
              child: HmsDividedColumn(
                children: [for (final p in shown) _WardPatientRow(patient: p)],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _WardPatientRow extends StatelessWidget {
  const _WardPatientRow({required this.patient});

  final WardPatient patient;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final a = patient.admission;
    final place = a == null
        ? null
        : a.awaitingBed
        ? t.awaitingBed
        : [?a.wardName, if (a.bedNumber != null) t.bedNumber(a.bedNumber!)]
              .join(' · ');
    return InkWell(
      onTap: () => context.go(NursingRoutes.patient(patient.patientId)),
      child: Padding(
        padding: AppSpacing.cardRow,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    patient.name.isEmpty ? t.patientLabel : patient.name,
                    style: AppTypography.body(weight: FontWeight.w600),
                  ),
                  Text(
                    [
                      ?place,
                      if (patient.assignedShift != null)
                        t.assignedForShift(
                          shiftLabel(t, patient.assignedShift!),
                        ),
                    ].join(' · '),
                    style: AppTypography.caption(),
                  ),
                ],
              ),
            ),
            if (a != null)
              StatusBadge(
                status: a.status,
                label: wardStatusLabel(t, a.status),
              ),
            const SizedBox(width: AppSpacing.x2),
            const Icon(
              LucideIcons.chevronRight,
              size: 16,
              color: AppColors.onCardMuted,
            ),
          ],
        ),
      ),
    );
  }
}
