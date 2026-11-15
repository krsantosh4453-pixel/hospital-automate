import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_scope.dart';
import '../../core/localization/l10n.dart';
import '../../core/routing/app_routes.dart';
import '../../core/theme/app_spacing.dart';
import '../../shared/widgets/page_body.dart';
import '../../shared/widgets/states.dart';
import '../../shared/widgets/tone.dart';
import '../doctor/ui/doctor_home_panel.dart';
import '../doctor/ui/doctor_ui.dart';
import '../navigation/nav_config.dart';
import 'guest_home.dart';
import 'patient_home.dart';
import 'staff_dashboard.dart';

/// Home (`/`): the guest landing page before sign-in; after it, the staff
/// dashboard or the patient home. `?denied=<path>` (set by the router when a
/// role opened another department's page) shows why the person landed here.
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final services = AppScope.of(context);
    final denied = GoRouterState.of(context).uri.queryParameters['denied'];
    return ListenableBuilder(
      listenable: services.session,
      builder: (context, _) {
        final t = context.l10n;
        final session = services.session.state;
        final deniedItem = denied == null ? null : findNavMatch(denied)?.item;
        return PageBody(
          location: AppRoutes.home,
          children: [
            if (session.isStaff && deniedItem != null) ...[
              HmsAlert(
                tone: AlertTone.warning,
                title: t.notEligibleForPage,
                message: t.notEligibleForPageBody(deniedItem.label(t)),
              ),
              const SizedBox(height: AppSpacing.x6),
            ],
            if (session.isStaff) ...[
              StaffDashboard(session: session, repository: services.dashboard),
              if (isDoctor(session) && session.activeHospitalId != null) ...[
                const SizedBox(height: AppSpacing.x6),
                DoctorHomePanel(
                  key: ValueKey('doctor-day-${session.activeHospitalId}'),
                  repository: services.doctor,
                  session: session,
                ),
              ],
            ] else if (session.isPatient)
              PatientHome(session: session, repository: services.patient)
            else
              const GuestHome(),
          ],
        );
      },
    );
  }
}
