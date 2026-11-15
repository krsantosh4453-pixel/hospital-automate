import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/security/session_controller.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import '../../shared/widgets/avatar.dart';
import '../../shared/widgets/hms_card.dart';
import '../../shared/widgets/page_header.dart';
import '../../shared/widgets/states.dart';
import '../patient/data/patient_repository.dart';
import '../patient/ui/patient_overview_panel.dart';

/// Home for a signed-in patient (or family member): greeting, the live
/// overview of their records at the selected hospital (PatientDashboard.jsx),
/// quick actions, the profile from `auth/patient/me/` and the hospitals
/// from `auth/me/contexts/`.
class PatientHome extends StatelessWidget {
  const PatientHome({
    super.key,
    required this.session,
    required this.repository,
    this.now,
  });

  final SessionState session;
  final PatientRepository repository;
  final DateTime Function()? now;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final user = session.user!;
    final profile = user.patient;
    final hour = (now ?? DateTime.now)().hour;
    final greeting = hour < 12
        ? t.goodMorning
        : hour < 17
        ? t.goodAfternoon
        : t.goodEvening;
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.lg;
    final cards = [
      if (profile != null)
        _ProfileCard(
          profile: profile,
          family: user.accountType == AccountType.proxy,
        ),
      _HospitalsCard(
        hospitals: session.hospitals,
        activeId: session.activeHospitalId,
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          title: user.firstName == null
              ? greeting
              : t.greetingWithName(greeting, user.firstName!),
          description: t.patientHomeIntro,
        ),
        if (session.activeHospital != null) ...[
          const SizedBox(height: AppSpacing.x2),
          Text(
            t.viewingHospital(session.activeHospital!.name),
            style: AppTypography.small(color: AppColors.ink500),
          ),
        ],
        const SizedBox(height: AppSpacing.x6),
        PatientOverviewPanel(
          key: ValueKey('overview-${session.activeHospitalId}'),
          repository: repository,
        ),
        const SizedBox(height: AppSpacing.x6),
        if (wide)
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                if (i > 0) const SizedBox(width: AppSpacing.x6),
                Expanded(child: cards[i]),
              ],
            ],
          )
        else
          for (var i = 0; i < cards.length; i++) ...[
            if (i > 0) const SizedBox(height: AppSpacing.x6),
            cards[i],
          ],
      ],
    );
  }
}

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({required this.profile, required this.family});

  final PatientProfile profile;
  final bool family;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    Widget row(IconData icon, String label, String? value, {bool? verified}) =>
        Padding(
          padding: AppSpacing.cardRow,
          child: Row(
            children: [
              Icon(icon, size: 16, color: AppColors.onCard),
              const SizedBox(width: AppSpacing.x3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, style: AppTypography.caption()),
                    Text(
                      value == null || value.isEmpty ? '—' : value,
                      style: AppTypography.body(weight: FontWeight.w500),
                    ),
                  ],
                ),
              ),
              if (verified != null)
                Text(
                  verified ? t.verified : t.notVerified,
                  style: AppTypography.caption(weight: FontWeight.w600),
                ),
            ],
          ),
        );
    final facts = [
      if (profile.gender != null && profile.gender!.isNotEmpty) profile.gender!,
      if (profile.age != null) t.ageYears('${profile.age}'),
    ].join(' · ');
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(
            title: t.myProfile,
            description: family ? t.accountFamily : null,
            icon: LucideIcons.userRound,
          ),
          Padding(
            padding: AppSpacing.cardHeader,
            child: Row(
              children: [
                HmsAvatar(name: profile.name, size: AvatarSize.large),
                const SizedBox(width: AppSpacing.x3),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(profile.name, style: AppTypography.cardTitle()),
                      if (facts.isNotEmpty)
                        Text(facts, style: AppTypography.small()),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppColors.onCardLine),
          HmsDividedColumn(
            children: [
              row(
                LucideIcons.phone,
                t.mobileNumber,
                profile.phone,
                verified: profile.phoneVerified,
              ),
              row(
                LucideIcons.mail,
                t.email,
                profile.email,
                verified: profile.emailVerified,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HospitalsCard extends StatelessWidget {
  const _HospitalsCard({required this.hospitals, required this.activeId});

  final List<HospitalContext> hospitals;
  final int? activeId;

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    return HmsCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          HmsCardHeader(title: t.myHospitals, icon: LucideIcons.hospital),
          if (hospitals.isEmpty)
            HmsEmptyState(
              compact: true,
              icon: LucideIcons.hospital,
              title: t.notMemberOfAnyHospital,
            )
          else
            HmsDividedColumn(
              children: [
                for (final hospital in hospitals)
                  Padding(
                    padding: AppSpacing.cardRow,
                    child: Row(
                      children: [
                        Icon(
                          hospital.id == activeId
                              ? LucideIcons.circleCheck
                              : LucideIcons.hospital,
                          size: 16,
                          color: AppColors.onCard,
                        ),
                        const SizedBox(width: AppSpacing.x3),
                        Expanded(
                          child: Text(
                            hospital.name,
                            style: AppTypography.body(weight: FontWeight.w500),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
