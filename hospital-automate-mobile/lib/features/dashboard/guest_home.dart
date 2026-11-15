import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/routing/app_routes.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/hms_button.dart';
import '../../shared/widgets/hms_card.dart';
import '../../shared/widgets/hms_dialog.dart';
import '../../shared/widgets/page_header.dart';
import '../../shared/widgets/stat_tile.dart';
import '../../shared/widgets/tone.dart';
import '../navigation/nav_config.dart';
import 'role_homes.dart';

/// GuestHome.jsx: the home page before sign-in. It mirrors the staff home
/// so the hospital's services are visible, but shows no figures.
class GuestHome extends StatelessWidget {
  const GuestHome({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const _Hero(),
        const SizedBox(height: AppSpacing.x8),
        Semantics(
          label: l10n.todayAtAGlance,
          container: true,
          child: StatTileGrid(
            children: [
              StatTile(
                icon: LucideIcons.usersRound,
                label: l10n.tilePatientsToday,
                hint: l10n.signInToSee,
              ),
              StatTile(
                icon: LucideIcons.calendarDays,
                tone: HmsTone.accent,
                label: l10n.tileAppointmentsToday,
                hint: l10n.signInToSee,
              ),
              StatTile(
                icon: LucideIcons.listOrdered,
                tone: HmsTone.warning,
                label: l10n.tileWaitingInQueue,
                hint: l10n.signInToSee,
              ),
              StatTile(
                icon: LucideIcons.bedDouble,
                tone: HmsTone.success,
                label: l10n.tileBedsAvailable,
                hint: l10n.signInToSee,
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.x8),
        SectionHeading(
          title: l10n.departments,
          description: l10n.departmentsIntro,
        ),
        const SizedBox(height: AppSpacing.x4),
        const _DepartmentGrid(),
        const SizedBox(height: AppSpacing.x8),
        const _BookingSteps(),
      ],
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.sm;
    const outline = BorderSide(color: AppColors.heroOutline);
    return Container(
      padding: wide
          ? const EdgeInsets.symmetric(horizontal: AppSpacing.x10, vertical: 56)
          : const EdgeInsets.symmetric(
              horizontal: AppSpacing.x6,
              vertical: AppSpacing.x10,
            ),
      decoration: const BoxDecoration(
        color: AppColors.hero,
        borderRadius: BorderRadius.all(Radius.circular(AppRadii.xxxl)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.guestEyebrow.toUpperCase(),
            style: AppTypography.caption(
              weight: FontWeight.w600,
              color: AppColors.heroEyebrow,
            ).copyWith(letterSpacing: 1.44),
          ),
          const SizedBox(height: AppSpacing.x3),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 672),
            child: Semantics(
              header: true,
              child: Text(
                l10n.guestTitle,
                style: AppTypography.style(
                  wide ? 36 : 30,
                  weight: FontWeight.w600,
                  height: wide ? 45 : 37.5,
                  color: Colors.white,
                  letterSpacing: wide ? -0.9 : -0.75,
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.x4),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 576),
            child: Text(
              l10n.guestBody,
              style: AppTypography.style(
                15,
                height: 28,
                color: AppColors.heroBody,
              ),
            ),
          ),
          const SizedBox(height: 28),
          Wrap(
            spacing: AppSpacing.x3,
            runSpacing: AppSpacing.x3,
            children: [
              _HeroButton(
                label: l10n.bookAppointment,
                icon: LucideIcons.calendarPlus,
                fill: Colors.white,
                foreground: AppColors.brand800,
                onTap: () => context.go(AppRoutes.patientLogin),
              ),
              _HeroButton(
                label: l10n.patientSignIn,
                icon: LucideIcons.logIn,
                border: outline,
                onTap: () => context.go(AppRoutes.patientLogin),
              ),
              _HeroButton(
                label: l10n.staffSignIn,
                icon: LucideIcons.logIn,
                border: outline,
                onTap: () => context.go(AppRoutes.staffLogin),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroButton extends StatelessWidget {
  const _HeroButton({
    required this.label,
    required this.icon,
    required this.onTap,
    this.fill = Colors.transparent,
    this.foreground = Colors.white,
    this.border = BorderSide.none,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final Color fill;
  final Color foreground;
  final BorderSide border;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      child: Material(
        color: fill,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadii.button,
          side: border,
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: AppRadii.button,
          child: SizedBox(
            height: AppDimensions.controlLarge,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.x5),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(icon, size: 17, color: foreground),
                  const SizedBox(width: AppSpacing.x2),
                  Flexible(
                    child: Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.body(
                        weight: FontWeight.w600,
                        color: foreground,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

@immutable
class _Department {
  const _Department(this.module, this.icon, this.title, this.text, this.roles);

  final String module;
  final IconData icon;
  final LocalizedText title;
  final LocalizedText text;

  /// Staff roles that may open this module, for the "only for …" message.
  /// Mirrors `eligibleRolesFor` on the web; the server enforces the real rule.
  final List<String> roles;
}

const _clinicalDesk = [
  'Admin',
  'Doctor',
  'Nurse',
  'Receptionist',
  'Hospital Manager',
];

final _departments = [
  _Department(
    'Patients',
    LucideIcons.usersRound,
    (t) => t.navPatients,
    (t) => t.deptPatientsText,
    _clinicalDesk,
  ),
  _Department(
    'Appointments',
    LucideIcons.calendarDays,
    (t) => t.navAppointments,
    (t) => t.deptAppointmentsText,
    _clinicalDesk,
  ),
  _Department(
    'Queue',
    LucideIcons.listOrdered,
    (t) => t.deptQueue,
    (t) => t.deptQueueText,
    _clinicalDesk,
  ),
  _Department(
    'Doctors',
    LucideIcons.stethoscope,
    (t) => t.navConsultation,
    (t) => t.deptConsultationText,
    const ['Admin', 'Doctor', 'Receptionist', 'Hospital Manager'],
  ),
  _Department(
    'Nurses',
    LucideIcons.userRound,
    (t) => t.deptNursing,
    (t) => t.deptNursingText,
    const ['Admin', 'Nurse', 'Hospital Manager'],
  ),
  _Department(
    'IPD',
    LucideIcons.bedDouble,
    (t) => t.deptWards,
    (t) => t.deptWardsText,
    const ['Admin', 'Doctor', 'Nurse', 'Hospital Manager'],
  ),
  _Department(
    'Emergency',
    LucideIcons.siren,
    (t) => t.navEmergency,
    (t) => t.deptEmergencyText,
    const ['Admin', 'Doctor', 'Nurse', 'Hospital Manager'],
  ),
  _Department(
    'Laboratory',
    LucideIcons.flaskConical,
    (t) => t.navLaboratory,
    (t) => t.deptLaboratoryText,
    const ['Admin', 'Doctor', 'Nurse', 'Lab Staff', 'Hospital Manager'],
  ),
  _Department(
    'Pharmacy',
    LucideIcons.pill,
    (t) => t.navPharmacy,
    (t) => t.deptPharmacyText,
    const ['Admin', 'Compounder', 'Pharmacist', 'Hospital Manager'],
  ),
  _Department(
    'BloodBank',
    LucideIcons.droplet,
    (t) => t.deptBloodBank,
    (t) => t.deptBloodBankText,
    const ['Admin', 'Doctor', 'Nurse', 'Blood Bank Staff', 'Hospital Manager'],
  ),
  _Department(
    'Billing',
    LucideIcons.receiptIndianRupee,
    (t) => t.navBilling,
    (t) => t.deptBillingText,
    const ['Admin', 'Receptionist', 'Billing Staff', 'Hospital Manager'],
  ),
  _Department(
    'Inventory',
    LucideIcons.package,
    (t) => t.navInventory,
    (t) => t.deptInventoryText,
    const [
      'Admin',
      'Compounder',
      'Pharmacist',
      'Inventory Staff',
      'Hospital Manager',
    ],
  ),
  _Department(
    'Reports',
    LucideIcons.chartColumn,
    (t) => t.navReports,
    (t) => t.deptReportsText,
    const [
      'Admin',
      'Doctor',
      'Nurse',
      'Compounder',
      'Receptionist',
      'Pharmacist',
      'Lab Staff',
      'Blood Bank Staff',
      'Billing Staff',
      'Inventory Staff',
      'Hospital Manager',
    ],
  ),
];

class _DepartmentGrid extends StatelessWidget {
  const _DepartmentGrid();

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final columns = width >= AppBreakpoints.xl
        ? 4
        : width >= AppBreakpoints.lg
        ? 3
        : width >= AppBreakpoints.sm
        ? 2
        : 1;
    return ResponsiveGrid(
      columns: columns,
      gap: AppSpacing.x4,
      children: [for (final dept in _departments) _DepartmentCard(dept: dept)],
    );
  }
}

class _DepartmentCard extends StatelessWidget {
  const _DepartmentCard({required this.dept});

  final _Department dept;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final title = dept.title(l10n);
    return HmsCard(
      onTap: () => _showLocked(context),
      semanticLabel: '$title, ${l10n.signInRequired}',
      padding: const EdgeInsets.all(AppSpacing.x5),
      child: ExcludeSemantics(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            HmsIconTile(icon: dept.icon, fill: AppColors.cardTintBrand),
            const SizedBox(width: AppSpacing.x3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          title,
                          style: AppTypography.style(
                            16,
                            weight: FontWeight.w600,
                            height: 24,
                            color: AppColors.onCard,
                          ),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.x1_5),
                      const Icon(
                        LucideIcons.lock,
                        size: 13,
                        color: AppColors.onCard,
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.x1),
                  Text(dept.text(l10n), style: AppTypography.body()),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showLocked(BuildContext context) {
    final l10n = context.l10n;
    final title = dept.title(l10n);
    showHmsModal<void>(
      context,
      title: l10n.notEligibleTitle,
      description: title,
      body: Text(
        l10n.notEligibleBody(
          title,
          dept.roles.map((r) => roleLabel(l10n, r)).join(', '),
        ),
        style: AppTypography.body().copyWith(height: 24 / 14),
      ),
      actions: (dialogContext) => [
        HmsButton(
          label: l10n.close,
          variant: HmsButtonVariant.secondary,
          surface: HmsSurface.card,
          onPressed: () => Navigator.of(dialogContext).pop(),
        ),
        HmsButton(
          label: l10n.staffSignIn,
          icon: LucideIcons.logIn,
          surface: HmsSurface.card,
          onPressed: () {
            Navigator.of(dialogContext).pop();
            context.go(AppRoutes.staffLogin);
          },
        ),
      ],
    );
  }
}

class _BookingSteps extends StatelessWidget {
  const _BookingSteps();

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final width = MediaQuery.sizeOf(context).width;
    final columns = width >= AppBreakpoints.lg
        ? 4
        : width >= AppBreakpoints.sm
        ? 2
        : 1;
    final steps = [
      (LucideIcons.hospital, l10n.selectHospital, l10n.stepSelectHospitalText),
      (
        LucideIcons.stethoscope,
        l10n.stepSelectDoctor,
        l10n.stepSelectDoctorText,
      ),
      (LucideIcons.calendarCheck, l10n.stepChooseSlot, l10n.stepChooseSlotText),
      (LucideIcons.shieldCheck, l10n.stepConfirm, l10n.stepConfirmText),
    ];
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: l10n.howBookingWorks,
            description: l10n.howBookingWorksIntro,
          ),
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.x5,
              vertical: AppSpacing.x6,
            ),
            child: ResponsiveGrid(
              columns: columns,
              gap: AppSpacing.x6,
              children: [
                for (var i = 0; i < steps.length; i++)
                  _Step(
                    number: i + 1,
                    icon: steps[i].$1,
                    title: steps[i].$2,
                    text: steps[i].$3,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({
    required this.number,
    required this.icon,
    required this.title,
    required this.text,
  });

  final int number;
  final IconData icon;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 32,
          height: 32,
          alignment: Alignment.center,
          decoration: const BoxDecoration(
            color: AppColors.cardButton,
            shape: BoxShape.circle,
          ),
          child: Text(
            '$number',
            style: AppTypography.body(weight: FontWeight.w600),
          ),
        ),
        const SizedBox(width: AppSpacing.x3),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 15, color: AppColors.onCard),
                  const SizedBox(width: AppSpacing.x1_5),
                  Flexible(
                    child: Text(
                      title,
                      style: AppTypography.style(
                        16,
                        weight: FontWeight.w500,
                        height: 24,
                        color: AppColors.onCard,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 2),
              Text(text, style: AppTypography.body()),
            ],
          ),
        ),
      ],
    );
  }
}
