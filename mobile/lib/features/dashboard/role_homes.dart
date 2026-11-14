import 'package:flutter/widgets.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../navigation/nav_config.dart';

/// Stat tiles a home page can show (keys of `tiles` in pages/Home.jsx).
enum DashboardTile {
  patients,
  appointments,
  queue,
  beds,
  admissions,
  labPending,
  labUrgent,
  labCompleted,
  billingPending,
  revenueToday,
}

@immutable
class QuickAction {
  const QuickAction({
    required this.path,
    required this.icon,
    required this.label,
    required this.module,
  });

  final String path;
  final IconData icon;
  final LocalizedText label;
  final String module;
}

/// What one staff role sees on its home page (src/config/roleHomes.js).
@immutable
class RoleHome {
  const RoleHome({
    required this.title,
    required this.tiles,
    required this.actions,
    this.showFlow = false,
    this.showRecentPatients = false,
  });

  final LocalizedText title;
  final List<DashboardTile> tiles;
  final List<QuickAction> actions;
  final bool showFlow;
  final bool showRecentPatients;
}

/// Admin and Hospital Manager keep the full hospital dashboard.
const fullDashboardRoles = {'Admin', 'Hospital Manager'};

const fullDashboardTiles = [
  DashboardTile.patients,
  DashboardTile.appointments,
  DashboardTile.queue,
  DashboardTile.beds,
];

final List<QuickAction> allQuickActions = [
  QuickAction(
    path: '/patients',
    icon: LucideIcons.userPlus,
    label: (t) => t.actionRegisterPatient,
    module: 'Patients',
  ),
  QuickAction(
    path: '/appointments',
    icon: LucideIcons.calendarPlus,
    label: (t) => t.actionNewAppointment,
    module: 'Appointments',
  ),
  QuickAction(
    path: '/queue',
    icon: LucideIcons.listOrdered,
    label: (t) => t.actionOpenQueue,
    module: 'Queue',
  ),
  QuickAction(
    path: '/consultation',
    icon: LucideIcons.stethoscope,
    label: (t) => t.actionStartConsultation,
    module: 'Doctors',
  ),
  QuickAction(
    path: '/pharmacy',
    icon: LucideIcons.pill,
    label: (t) => t.actionDispenseMedicines,
    module: 'Pharmacy',
  ),
  QuickAction(
    path: '/laboratory',
    icon: LucideIcons.flaskConical,
    label: (t) => t.actionLabWorklist,
    module: 'Laboratory',
  ),
  QuickAction(
    path: '/billing',
    icon: LucideIcons.receiptIndianRupee,
    label: (t) => t.actionCreateInvoice,
    module: 'Billing',
  ),
  QuickAction(
    path: '/patients',
    icon: LucideIcons.search,
    label: (t) => t.actionFindPatient,
    module: 'Patients',
  ),
];

QuickAction _a(
  String path,
  IconData icon,
  LocalizedText label,
  String module,
) => QuickAction(path: path, icon: icon, label: label, module: module);

final Map<String, RoleHome> roleHomes = {
  'Doctor': RoleHome(
    title: (t) => t.roleHomeDoctor,
    tiles: const [
      DashboardTile.appointments,
      DashboardTile.queue,
      DashboardTile.labPending,
    ],
    showFlow: true,
    actions: [
      _a('/queue', LucideIcons.listOrdered, (t) => t.actionOpenQueue, 'Queue'),
      _a(
        '/consultation',
        LucideIcons.stethoscope,
        (t) => t.actionStartConsultation,
        'Doctors',
      ),
      _a(
        '/prescription',
        LucideIcons.fileText,
        (t) => t.actionPrescriptions,
        'Prescriptions',
      ),
      _a(
        '/ai-scribe',
        LucideIcons.sparkles,
        (t) => t.actionAiScribe,
        'AIScribe',
      ),
      _a(
        '/emergency-access',
        LucideIcons.shieldAlert,
        (t) => t.navEmergencyAccess,
        'Dashboard',
      ),
      _a(
        '/laboratory',
        LucideIcons.flaskConical,
        (t) => t.actionLabResults,
        'Laboratory',
      ),
    ],
  ),
  'Nurse': RoleHome(
    title: (t) => t.roleHomeNurse,
    tiles: const [
      DashboardTile.admissions,
      DashboardTile.beds,
      DashboardTile.queue,
    ],
    actions: [
      _a(
        '/nurses',
        LucideIcons.heartPulse,
        (t) => t.actionVitalsNursing,
        'Nurses',
      ),
      _a('/ipd', LucideIcons.bedDouble, (t) => t.actionWardBeds, 'IPD'),
      _a('/queue', LucideIcons.listOrdered, (t) => t.actionOpenQueue, 'Queue'),
      _a('/emergency', LucideIcons.siren, (t) => t.navEmergency, 'Emergency'),
      _a(
        '/emergency-access',
        LucideIcons.shieldAlert,
        (t) => t.navEmergencyAccess,
        'Dashboard',
      ),
    ],
  ),
  'Receptionist': RoleHome(
    title: (t) => t.roleHomeReceptionist,
    tiles: const [
      DashboardTile.patients,
      DashboardTile.appointments,
      DashboardTile.queue,
    ],
    showFlow: true,
    showRecentPatients: true,
    actions: [
      _a(
        '/patients',
        LucideIcons.userPlus,
        (t) => t.actionRegisterPatient,
        'Patients',
      ),
      _a(
        '/appointments',
        LucideIcons.calendarPlus,
        (t) => t.actionNewAppointment,
        'Appointments',
      ),
      _a('/queue', LucideIcons.listOrdered, (t) => t.actionOpenQueue, 'Queue'),
      _a(
        '/billing',
        LucideIcons.receiptIndianRupee,
        (t) => t.actionCreateInvoice,
        'Billing',
      ),
      _a(
        '/patients',
        LucideIcons.search,
        (t) => t.actionFindPatient,
        'Patients',
      ),
    ],
  ),
  'Compounder': RoleHome(
    title: (t) => t.roleHomePharmacy,
    tiles: const [],
    actions: [
      _a(
        '/pharmacy',
        LucideIcons.pill,
        (t) => t.actionDispenseMedicines,
        'Pharmacy',
      ),
      _a(
        '/compounter',
        LucideIcons.syringe,
        (t) => t.actionCompounding,
        'Compounders',
      ),
      _a(
        '/prescription',
        LucideIcons.fileText,
        (t) => t.actionPrescriptions,
        'Prescriptions',
      ),
      _a(
        '/inventory',
        LucideIcons.package,
        (t) => t.actionMedicineStock,
        'Inventory',
      ),
    ],
  ),
  'Pharmacist': RoleHome(
    title: (t) => t.roleHomePharmacy,
    tiles: const [],
    actions: [
      _a(
        '/pharmacy',
        LucideIcons.pill,
        (t) => t.actionDispenseMedicines,
        'Pharmacy',
      ),
      _a(
        '/prescription',
        LucideIcons.fileText,
        (t) => t.actionPrescriptions,
        'Prescriptions',
      ),
      _a(
        '/inventory',
        LucideIcons.package,
        (t) => t.actionMedicineStock,
        'Inventory',
      ),
      _a(
        '/compounter',
        LucideIcons.syringe,
        (t) => t.actionCompounding,
        'Compounders',
      ),
    ],
  ),
  'Lab Staff': RoleHome(
    title: (t) => t.roleHomeLaboratory,
    tiles: const [
      DashboardTile.labPending,
      DashboardTile.labUrgent,
      DashboardTile.labCompleted,
    ],
    actions: [
      _a(
        '/laboratory',
        LucideIcons.flaskConical,
        (t) => t.actionLabWorklist,
        'Laboratory',
      ),
    ],
  ),
  'Billing Staff': RoleHome(
    title: (t) => t.roleHomeBilling,
    tiles: const [DashboardTile.billingPending, DashboardTile.revenueToday],
    actions: [
      _a(
        '/billing',
        LucideIcons.receiptIndianRupee,
        (t) => t.actionCreateInvoice,
        'Billing',
      ),
      _a('/reports', LucideIcons.chartColumn, (t) => t.navReports, 'Reports'),
    ],
  ),
  'Blood Bank Staff': RoleHome(
    title: (t) => t.roleHomeBloodBank,
    tiles: const [],
    actions: [
      _a(
        '/blood-bank',
        LucideIcons.droplet,
        (t) => t.actionBloodStock,
        'BloodBank',
      ),
    ],
  ),
  'Inventory Staff': RoleHome(
    title: (t) => t.roleHomeStore,
    tiles: const [],
    actions: [
      _a('/inventory', LucideIcons.package, (t) => t.navInventory, 'Inventory'),
    ],
  ),
};

/// Home configuration for [role], or null for the full dashboard.
RoleHome? roleHomeFor(String? role) {
  if (role == null || fullDashboardRoles.contains(role)) return null;
  return roleHomes[role];
}

/// Translated name of a staff role the server sends; unknown roles stay as sent.
String roleLabel(AppLocalizations t, String role) => switch (role) {
  'Admin' => t.roleAdmin,
  'Doctor' => t.roleDoctor,
  'Nurse' => t.roleNurse,
  'Compounder' => t.roleCompounder,
  'Receptionist' => t.roleReceptionist,
  'Pharmacist' => t.rolePharmacist,
  'Lab Staff' => t.roleLabStaff,
  'Blood Bank Staff' => t.roleBloodBankStaff,
  'Billing Staff' => t.roleBillingStaff,
  'Inventory Staff' => t.roleInventoryStaff,
  'Hospital Manager' => t.roleHospitalManager,
  _ => role,
};
