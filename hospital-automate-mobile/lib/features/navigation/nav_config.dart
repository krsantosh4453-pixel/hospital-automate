import 'package:flutter/widgets.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';

typedef LocalizedText = String Function(AppLocalizations l10n);

/// One sidebar entry. [module] is the permission module checked with
/// `canView` (`null`: every signed-in staff member sees it).
@immutable
class NavItem {
  const NavItem({
    required this.path,
    required this.label,
    required this.icon,
    required this.module,
    this.end = false,
  });

  final String path;
  final LocalizedText label;
  final IconData icon;
  final String? module;

  /// Matches only the exact path (React Router `end`), not its children.
  final bool end;

  bool matches(String location) => end
      ? location == path
      : location == path || location.startsWith('$path/');
}

@immutable
class NavGroup {
  const NavGroup({
    required this.id,
    required this.label,
    required this.items,
    this.adminOnly = false,
  });

  final String id;
  final LocalizedText label;
  final List<NavItem> items;
  final bool adminOnly;

  /// The Overview group is drawn without a heading, as on the web.
  bool get showsHeading => id != 'overview';
}

/// Staff navigation, item for item the web's `STAFF_NAV` (src/config/navigation.js).
final List<NavGroup> staffNav = [
  NavGroup(
    id: 'overview',
    label: (t) => t.groupOverview,
    items: [
      NavItem(
        path: '/',
        label: (t) => t.navHome,
        icon: LucideIcons.house,
        module: null,
        end: true,
      ),
    ],
  ),
  NavGroup(
    id: 'front-desk',
    label: (t) => t.groupFrontDesk,
    items: [
      NavItem(
        path: '/patients',
        label: (t) => t.navPatients,
        icon: LucideIcons.usersRound,
        module: 'Patients',
      ),
      NavItem(
        path: '/appointments',
        label: (t) => t.navAppointments,
        icon: LucideIcons.calendarDays,
        module: 'Appointments',
      ),
      NavItem(
        path: '/queue',
        label: (t) => t.navQueue,
        icon: LucideIcons.listOrdered,
        module: 'Queue',
      ),
    ],
  ),
  NavGroup(
    id: 'clinical',
    label: (t) => t.groupClinical,
    items: [
      // Consultation reuses the Doctors permission gate (no separate module exists).
      NavItem(
        path: '/consultation',
        label: (t) => t.navConsultation,
        icon: LucideIcons.stethoscope,
        module: 'Doctors',
      ),
      NavItem(
        path: '/prescription',
        label: (t) => t.navPrescription,
        icon: LucideIcons.fileText,
        module: 'Prescriptions',
      ),
      NavItem(
        path: '/nurses',
        label: (t) => t.navNurses,
        icon: LucideIcons.heartPulse,
        module: 'Nurses',
      ),
      NavItem(
        path: '/ipd',
        label: (t) => t.navIpd,
        icon: LucideIcons.bedDouble,
        module: 'IPD',
      ),
      NavItem(
        path: '/emergency',
        label: (t) => t.navEmergency,
        icon: LucideIcons.siren,
        module: 'Emergency',
      ),
      NavItem(
        path: '/ai-scribe',
        label: (t) => t.navAiScribe,
        icon: LucideIcons.sparkles,
        module: 'AIScribe',
      ),
    ],
  ),
  NavGroup(
    id: 'diagnostics',
    label: (t) => t.groupDiagnostics,
    items: [
      NavItem(
        path: '/laboratory',
        label: (t) => t.navLaboratory,
        icon: LucideIcons.flaskConical,
        module: 'Laboratory',
      ),
      NavItem(
        path: '/radiology',
        label: (t) => t.navRadiology,
        icon: LucideIcons.scanSearch,
        module: 'Laboratory',
      ),
      NavItem(
        path: '/pharmacy',
        label: (t) => t.navPharmacy,
        icon: LucideIcons.pill,
        module: 'Pharmacy',
      ),
      NavItem(
        path: '/compounter',
        label: (t) => t.navCompounder,
        icon: LucideIcons.syringe,
        module: 'Compounders',
      ),
      NavItem(
        path: '/blood-bank',
        label: (t) => t.navBloodBank,
        icon: LucideIcons.droplet,
        module: 'BloodBank',
      ),
    ],
  ),
  NavGroup(
    id: 'operations',
    label: (t) => t.groupOperations,
    items: [
      NavItem(
        path: '/billing',
        label: (t) => t.navBilling,
        icon: LucideIcons.receiptIndianRupee,
        module: 'Billing',
      ),
      NavItem(
        path: '/inventory',
        label: (t) => t.navInventory,
        icon: LucideIcons.package,
        module: 'Inventory',
      ),
      // Every staff member applies for leave here; other tabs follow the role.
      NavItem(
        path: '/services',
        label: (t) => t.navHospitalServices,
        icon: LucideIcons.ambulance,
        module: null,
      ),
      NavItem(
        path: '/reports',
        label: (t) => t.navReports,
        icon: LucideIcons.chartColumn,
        module: 'Reports',
      ),
    ],
  ),
  NavGroup(
    id: 'people',
    label: (t) => t.groupStaff,
    items: [
      NavItem(
        path: '/doctors',
        label: (t) => t.navDoctors,
        icon: LucideIcons.userRound,
        module: 'Doctors',
      ),
    ],
  ),
  NavGroup(
    id: 'admin',
    label: (t) => t.groupAdministration,
    adminOnly: true,
    items: [
      NavItem(
        path: '/admin',
        label: (t) => t.navAdminDashboard,
        icon: LucideIcons.layoutDashboard,
        module: null,
        end: true,
      ),
      NavItem(
        path: '/admin/users',
        label: (t) => t.navUsers,
        icon: LucideIcons.users,
        module: 'Users',
      ),
      NavItem(
        path: '/admin/roles',
        label: (t) => t.navRoles,
        icon: LucideIcons.shieldCheck,
        module: 'Roles',
      ),
      NavItem(
        path: '/admin/hospitals',
        label: (t) => t.navHospitals,
        icon: LucideIcons.hospital,
        module: 'Hospitals',
      ),
      NavItem(
        path: '/admin/departments',
        label: (t) => t.navDepartments,
        icon: LucideIcons.clipboardList,
        module: 'Departments',
      ),
      NavItem(
        path: '/admin/nurse-duty',
        label: (t) => t.navNurseDuty,
        icon: LucideIcons.calendarClock,
        module: 'Departments',
      ),
      NavItem(
        path: '/admin/permissions',
        label: (t) => t.navPermissions,
        icon: LucideIcons.keyRound,
        module: 'Permissions',
      ),
      NavItem(
        path: '/admin/audit',
        label: (t) => t.navAuditLog,
        icon: LucideIcons.history,
        module: 'Permissions',
      ),
      // Review queue for break-glass grants.
      NavItem(
        path: '/emergency-access',
        label: (t) => t.navEmergencyAccess,
        icon: LucideIcons.shieldAlert,
        module: null,
      ),
      NavItem(
        path: '/admin/security',
        label: (t) => t.navSecuritySettings,
        icon: LucideIcons.shieldCheck,
        module: 'Permissions',
      ),
    ],
  ),
  NavGroup(
    id: 'system',
    label: (t) => t.groupSystem,
    items: [
      NavItem(
        path: '/settings',
        label: (t) => t.settings,
        icon: LucideIcons.settings,
        module: null,
      ),
    ],
  ),
];

/// Modules whose view permission opens the Administration group.
const adminModules = [
  'Users',
  'Roles',
  'Hospitals',
  'Departments',
  'Permissions',
];

/// Navigation filtered to what the current role may view.
List<NavGroup> visibleStaffNav(bool Function(String? module) canView) {
  final hasAdminAccess = adminModules.any(canView);
  return [
    for (final group in staffNav)
      if (!group.adminOnly || hasAdminAccess)
        NavGroup(
          id: group.id,
          label: group.label,
          adminOnly: group.adminOnly,
          items: [
            for (final item in group.items)
              if (item.module == null || canView(item.module)) item,
          ],
        ),
  ].where((group) => group.items.isNotEmpty).toList();
}

/// Navigation for visitors: the same menu staff see, without Administration.
List<NavGroup> guestStaffNav() => [
  for (final group in staffNav)
    if (!group.adminOnly) group,
];

/// Patient portal navigation, item for item the web's `PatientLayout.jsx`.
/// Home is `/` in the app (the web uses `/patient`); the rest keep the web paths.
final List<NavGroup> patientNav = [
  NavGroup(
    id: 'patient-overview',
    label: (t) => t.groupOverview,
    items: [
      NavItem(
        path: '/',
        label: (t) => t.patientNavHome,
        icon: LucideIcons.house,
        module: null,
        end: true,
      ),
    ],
  ),
  NavGroup(
    id: 'patient-portal',
    label: (t) => t.groupPatientPortal,
    items: [
      NavItem(
        path: '/patient/appointments',
        label: (t) => t.patientNavAppointments,
        icon: LucideIcons.calendarDays,
        module: null,
      ),
      NavItem(
        path: '/patient/queue',
        label: (t) => t.patientNavQueue,
        icon: LucideIcons.ticket,
        module: null,
      ),
      NavItem(
        path: '/patient/documents',
        label: (t) => t.patientNavRecords,
        icon: LucideIcons.fileText,
        module: null,
      ),
      NavItem(
        path: '/patient/prescriptions',
        label: (t) => t.patientNavPrescriptions,
        icon: LucideIcons.pill,
        module: null,
      ),
      NavItem(
        path: '/patient/lab-results',
        label: (t) => t.patientNavLab,
        icon: LucideIcons.flaskConical,
        module: null,
      ),
      NavItem(
        path: '/patient/bills',
        label: (t) => t.patientNavBills,
        icon: LucideIcons.receiptIndianRupee,
        module: null,
      ),
      NavItem(
        path: '/patient/consent',
        label: (t) => t.patientNavConsent,
        icon: LucideIcons.bell,
        module: null,
      ),
      // App pages (not in the web sidebar): the in-app inbox and the profile.
      NavItem(
        path: '/patient/notifications',
        label: (t) => t.patientNavNotifications,
        icon: LucideIcons.bellRing,
        module: null,
      ),
      NavItem(
        path: '/patient/profile',
        label: (t) => t.myProfile,
        icon: LucideIcons.userRound,
        module: null,
      ),
    ],
  ),
  NavGroup(
    id: 'patient-system',
    label: (t) => t.groupSystem,
    items: [
      NavItem(
        path: '/settings',
        label: (t) => t.settings,
        icon: LucideIcons.settings,
        module: null,
      ),
    ],
  ),
];

/// The group and entry for [location], for breadcrumbs and titles. Null when none matches.
({NavGroup group, NavItem item})? findNavMatch(String location) {
  for (final group in [...staffNav, ...patientNav.skip(1)]) {
    for (final item in group.items) {
      if (item.matches(location)) return (group: group, item: item);
    }
  }
  return null;
}
