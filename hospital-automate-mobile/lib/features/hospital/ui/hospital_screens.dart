import 'dart:async';

import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/app_scope.dart';
import '../../../core/localization/l10n.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/security/session_controller.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/hms_button.dart';
import '../../../shared/widgets/hms_card.dart';
import '../../../shared/widgets/hms_search_field.dart';
import '../../../shared/widgets/page_header.dart';
import '../../../shared/widgets/stat_tile.dart';
import '../../../shared/widgets/states.dart';
import '../../../shared/widgets/tone.dart';
import '../../operations/ops_ui.dart';
import '../../patient/record_loader.dart';
import '../../patient/ui/patient_ui.dart' show DetailRow, RecordSection;
import '../data/hospital_models.dart';

/// Admin paths of these pages (nav_config.dart, as on the web).
abstract final class HospitalRoutes {
  static const hospitals = '/admin/hospitals';
  static const departments = '/admin/departments';
  static const staff = '/admin/users';
}

const _searchDelay = Duration(milliseconds: 350);

/// `/admin/hospitals`: the acting hospital's record, wards and the
/// hospitals this login may switch between. Switching re-scopes every
/// request (`X-Hospital-ID`); the server re-checks membership each time.
class HospitalOverviewScreen extends StatefulWidget {
  const HospitalOverviewScreen({super.key});

  @override
  State<HospitalOverviewScreen> createState() => _HospitalOverviewScreenState();
}

class _HospitalOverviewScreenState extends State<HospitalOverviewScreen>
    with PullToRefresh<HospitalOverviewScreen> {
  late final _services = AppScope.read(context);
  late final RecordLoader<HospitalInfo> _info = RecordLoader(
    () => _services.hospital.hospital(_services.session.activeHospitalId ?? 0),
  );
  late final RecordLoader<List<Ward>> _wards = RecordLoader(
    _services.hospital.wards,
  );

  @override
  void initState() {
    super.initState();
    reload();
  }

  @override
  void dispose() {
    _info.dispose();
    _wards.dispose();
    super.dispose();
  }

  @override
  Future<void> reload() => Future.wait([_info.load(), _wards.load()]);

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final session = AppScope.of(context).session;
    String count(int? n) => n == null ? '—' : '$n';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.navHospitals, description: t.hospIntro),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<HospitalInfo>(
          loader: _info,
          builder: (context, h) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              StatTileGrid(
                children: [
                  StatTile(
                    label: t.hospDepartments,
                    value: count(h.departments),
                    icon: LucideIcons.clipboardList,
                  ),
                  StatTile(
                    label: t.hospDoctors,
                    value: count(h.doctors),
                    icon: LucideIcons.stethoscope,
                    tone: HmsTone.accent,
                  ),
                  StatTile(
                    label: t.hospNurses,
                    value: count(h.nurses),
                    icon: LucideIcons.heartPulse,
                    tone: HmsTone.success,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.x4),
              HmsCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    HmsCardHeader(
                      title: h.name,
                      icon: LucideIcons.hospital,
                      trailing: ToneBadge(
                        label: h.isActive ? t.hospActive : t.hospInactive,
                        tone: h.isActive ? AlertTone.success : AlertTone.danger,
                      ),
                    ),
                    DetailRow(label: t.hospCode, value: h.code),
                    DetailRow(label: t.hospType, value: h.type),
                    DetailRow(label: t.hospAddress, value: h.fullAddress),
                    DetailRow(label: t.hospPhone, value: h.phone),
                    DetailRow(label: t.hospEmail, value: h.email),
                    DetailRow(
                      label: t.hospGrievanceOfficer,
                      value: [
                        ?h.grievanceOfficerName,
                        ?h.grievanceOfficerPhone,
                        ?h.grievanceOfficerEmail,
                      ].join(' · '),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        SectionHeading(title: t.hospWards),
        const SizedBox(height: AppSpacing.x2),
        RecordSection<List<Ward>>(
          loader: _wards,
          skeletons: 1,
          builder: (context, wards) => HmsCard(
            child: wards.isEmpty
                ? HmsEmptyState(
                    icon: LucideIcons.bedDouble,
                    title: t.hospNoWards,
                  )
                : HmsDividedColumn(
                    children: [
                      for (final ward in wards)
                        DetailRow(label: ward.name, value: ward.wardType),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: AppSpacing.x4),
        SectionHeading(title: t.hospYourHospitals),
        const SizedBox(height: AppSpacing.x2),
        HmsCard(
          child: HmsDividedColumn(
            children: [
              for (final hospital in session.state.hospitals)
                _HospitalChoice(
                  hospital: hospital,
                  current: hospital.id == session.activeHospitalId,
                  onSwitch: () => session.selectHospital(hospital.id),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _HospitalChoice extends StatelessWidget {
  const _HospitalChoice({
    required this.hospital,
    required this.current,
    required this.onSwitch,
  });

  final HospitalContext hospital;
  final bool current;
  final VoidCallback onSwitch;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Padding(
      key: ValueKey('hospital-choice-${hospital.id}'),
      padding: AppSpacing.cardRow,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  hospital.name,
                  style: AppTypography.body(weight: FontWeight.w600),
                ),
                if (hospital.role != null)
                  Text(
                    t.actingAs(hospital.role!),
                    style: AppTypography.small(),
                  ),
              ],
            ),
          ),
          if (current)
            ToneBadge(label: t.hospCurrent, tone: AlertTone.success)
          else
            HmsButton(
              label: t.hospSwitch,
              surface: HmsSurface.card,
              variant: HmsButtonVariant.secondary,
              size: HmsButtonSize.small,
              onPressed: onSwitch,
            ),
        ],
      ),
    );
  }
}

/// `/admin/departments`: departments of the acting hospital (read-only here).
class DepartmentsScreen extends StatefulWidget {
  const DepartmentsScreen({super.key});

  @override
  State<DepartmentsScreen> createState() => _DepartmentsScreenState();
}

class _DepartmentsScreenState extends State<DepartmentsScreen>
    with PullToRefresh<DepartmentsScreen> {
  late final RecordLoader<List<Department>> _loader = RecordLoader(
    AppScope.read(context).hospital.departments,
  );

  @override
  void initState() {
    super.initState();
    reload();
  }

  @override
  void dispose() {
    _loader.dispose();
    super.dispose();
  }

  @override
  Future<void> reload() => _loader.load();

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.navDepartments, description: t.deptIntro),
        const SizedBox(height: AppSpacing.x4),
        RecordSection<List<Department>>(
          loader: _loader,
          builder: (context, rows) {
            if (rows.isEmpty) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.clipboardList,
                  title: t.deptNone,
                ),
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final dept in rows) ...[
                  HmsCard(
                    key: ValueKey('dept-${dept.id}'),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        HmsCardHeader(
                          title: dept.name,
                          description: dept.code,
                          trailing: ToneBadge(
                            label: dept.isActive
                                ? t.hospActive
                                : t.hospInactive,
                            tone: dept.isActive
                                ? AlertTone.success
                                : AlertTone.danger,
                          ),
                        ),
                        DetailRow(label: t.deptHead, value: dept.headName),
                        DetailRow(
                          label: t.hospDoctors,
                          value: dept.doctors?.toString(),
                        ),
                        if (dept.description != null)
                          DetailRow(
                            label: t.deptDescription,
                            value: dept.description,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.x3),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

/// `/admin/users`: staff of the acting hospital, for its Admin or Manager.
/// Other roles get the server's 403, shown as a plain explanation.
class StaffScreen extends StatefulWidget {
  const StaffScreen({super.key});

  @override
  State<StaffScreen> createState() => _StaffScreenState();
}

class _StaffScreenState extends State<StaffScreen>
    with PullToRefresh<StaffScreen> {
  late final _repository = AppScope.read(context).hospital;
  late final RecordLoader<List<StaffMember>> _staff = RecordLoader(
    () => _repository.staff(search: _search),
  );
  late final RecordLoader<List<Department>> _departments = RecordLoader(
    _repository.departments,
  );
  String _search = '';
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    reload();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _staff.dispose();
    _departments.dispose();
    super.dispose();
  }

  @override
  Future<void> reload() => Future.wait([_staff.load(), _departments.load()]);

  void _onSearch(String text) {
    _debounce?.cancel();
    _debounce = Timer(_searchDelay, () {
      _search = text;
      _staff.load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(title: t.navUsers, description: t.staffIntro),
        const SizedBox(height: AppSpacing.x4),
        HmsSearchField(hint: t.staffSearch, onChanged: _onSearch),
        const SizedBox(height: AppSpacing.x4),
        ListenableBuilder(
          listenable: Listenable.merge([_staff, _departments]),
          builder: (context, _) {
            final error = _staff.error;
            if (error is ApiException && error.kind == ApiErrorKind.forbidden) {
              return HmsCard(
                child: HmsEmptyState(
                  icon: LucideIcons.lock,
                  title: t.staffManagersOnly,
                ),
              );
            }
            final names = {
              for (final d in _departments.data ?? const <Department>[])
                d.id: d.name,
            };
            return RecordSection<List<StaffMember>>(
              loader: _staff,
              builder: (context, rows) {
                if (rows.isEmpty) {
                  return HmsCard(
                    child: HmsEmptyState(
                      icon: LucideIcons.users,
                      title: t.staffNone,
                    ),
                  );
                }
                return HmsCard(
                  child: HmsDividedColumn(
                    children: [
                      for (final member in rows)
                        _StaffRow(
                          member: member,
                          department: names[member.departmentId],
                        ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ],
    );
  }
}

class _StaffRow extends StatelessWidget {
  const _StaffRow({required this.member, this.department});

  final StaffMember member;
  final String? department;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final (label, tone) = member.invitePending
        ? (t.staffInvitePending, AlertTone.warning)
        : member.membershipActive
        ? (t.hospActive, AlertTone.success)
        : (t.staffAccessEnded, AlertTone.danger);
    return Padding(
      key: ValueKey('staff-${member.userId}'),
      padding: AppSpacing.cardRow,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  member.name,
                  style: AppTypography.body(weight: FontWeight.w600),
                ),
                Text(
                  [?member.role, ?department, ?member.employeeId].join(' · '),
                  style: AppTypography.small(),
                ),
              ],
            ),
          ),
          ToneBadge(label: label, tone: tone),
        ],
      ),
    );
  }
}
