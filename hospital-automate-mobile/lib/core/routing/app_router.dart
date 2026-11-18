import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/ui/patient_login_screen.dart';
import '../../features/auth/ui/register_screen.dart';
import '../../features/auth/ui/staff_login_screen.dart';
import '../../features/billing/ui/billing_screen.dart';
import '../../features/billing/ui/billing_ui.dart';
import '../../features/billing/ui/invoice_screen.dart';
import '../../features/billing/ui/money_entry_screen.dart';
import '../../features/billing/ui/new_invoice_screen.dart';
import '../../features/dashboard/dashboard_screen.dart';
import '../../features/laboratory/ui/lab_new_order_screen.dart';
import '../../features/laboratory/ui/lab_order_screen.dart';
import '../../features/laboratory/ui/lab_ui.dart';
import '../../features/laboratory/ui/laboratory_screen.dart';
import '../../features/doctor/ui/consultation_screen.dart';
import '../../features/doctor/ui/doctor_appointments_screen.dart';
import '../../features/doctor/ui/doctor_lists_screens.dart';
import '../../features/doctor/ui/doctor_ui.dart';
import '../../features/doctor/ui/patient_records_screens.dart';
import '../../features/doctor/ui/queue_board_screen.dart';
import '../../features/emergency/ui/emergency_screen.dart';
import '../../features/emergency/ui/emergency_ui.dart';
import '../../features/emergency/ui/emergency_visit_screen.dart';
import '../../features/hospital/ui/hospital_screens.dart';
import '../../features/ipd/ui/admission_screen.dart';
import '../../features/ipd/ui/ipd_screen.dart';
import '../../features/ipd/ui/ipd_ui.dart';
import '../../features/operations/ops_ui.dart';
import '../../features/navigation/app_shell.dart';
import '../../features/nursing/ui/nursing_ui.dart';
import '../../features/nursing/ui/ward_patient_screen.dart';
import '../../features/nursing/ui/ward_patients_screen.dart';
import '../../features/pharmacy/ui/dispense_screen.dart';
import '../../features/pharmacy/ui/medicine_screen.dart';
import '../../features/pharmacy/ui/pharmacy_screen.dart';
import '../../features/pharmacy/ui/pharmacy_ui.dart';
import '../../features/navigation/nav_config.dart';
import '../../features/patient/ui/account_screens.dart';
import '../../features/patient/ui/appointments_screen.dart';
import '../../features/patient/ui/bills_screen.dart';
import '../../features/patient/ui/book_appointment_screen.dart';
import '../../features/patient/ui/clinical_records_screens.dart';
import '../../features/patient/ui/patient_routes.dart';
import '../../features/patient/ui/patient_ui.dart';
import '../../features/patient/ui/queue_screen.dart';
import '../../features/system/placeholder_screens.dart';
import '../../features/system/settings_screen.dart';
import '../security/session_controller.dart';
import 'app_routes.dart';

/// Every page sits inside the shell (sidebar + header), at the same paths
/// the web app uses. Sidebar pages not built yet open [ModuleScreen].
/// Routes follow the session (see [redirectFor]); the server still checks
/// every request, so this only keeps people off pages it would refuse.
GoRouter buildAppRouter({
  required SessionController session,
  String initialLocation = AppRoutes.home,
}) {
  const ownScreens = {AppRoutes.home, AppRoutes.settings};
  // Patient portal pages built so far; consent still opens ModuleScreen.
  final patientScreens = <String, Widget Function()>{
    PatientRoutes.appointments: AppointmentsScreen.new,
    PatientRoutes.queue: QueueScreen.new,
    PatientRoutes.prescriptions: PrescriptionsScreen.new,
    PatientRoutes.labResults: LabResultsScreen.new,
    PatientRoutes.bills: BillsScreen.new,
    PatientRoutes.documents: DocumentsScreen.new,
    PatientRoutes.notifications: NotificationsScreen.new,
    PatientRoutes.profile: ProfileScreen.new,
  };
  GoRoute patientPage(String path, Widget Function() build) => GoRoute(
    path: path,
    pageBuilder: (_, state) =>
        _page(state, PatientPage(location: state.uri.path, child: build())),
  );
  GoRoute page(String path, Widget Function(String location) build) => GoRoute(
    path: path,
    pageBuilder: (_, state) => _page(state, build(state.uri.path)),
  );
  // Doctor pages at the staff paths. Other roles keep ModuleScreen there
  // until their own module is built (the server checks every request).
  final doctorScreens = <String, Widget Function(GoRouterState)>{
    DoctorRoutes.appointments: (_) => const DoctorAppointmentsScreen(),
    DoctorRoutes.queue: (_) => const QueueBoardScreen(),
    DoctorRoutes.patients: (_) => const PatientSearchScreen(),
    '${DoctorRoutes.patients}/:id': (state) =>
        PatientRecordScreen(patientId: _idOf(state)),
    DoctorRoutes.consultation: (_) => const ConsultationListScreen(),
    '${DoctorRoutes.consultation}/:visitId': (state) =>
        ConsultationScreen(visitId: _idOf(state, 'visitId')),
    DoctorRoutes.prescriptions: (_) => const DoctorPrescriptionsScreen(),
  };
  // Laboratory and billing desks, for every role the sidebar lets in (the
  // module check in redirectFor). Each page offers only the actions the
  // server allows that role; /laboratory shows doctors their ordered tests.
  final deskScreens = <String, Widget Function(GoRouterState)>{
    LabRoutes.worklist: (_) => const LabHomeScreen(),
    LabRoutes.newOrder: (_) => const LabNewOrderScreen(),
    '${LabRoutes.worklist}/:id': (state) =>
        LabOrderScreen(orderId: _idOf(state)),
    BillingRoutes.desk: (_) => const BillingScreen(),
    BillingRoutes.newInvoice: (_) => const NewInvoiceScreen(),
    '${BillingRoutes.desk}/invoices/:id': (state) =>
        InvoiceScreen(invoiceId: _idOf(state)),
    '${BillingRoutes.desk}/invoices/:id/pay': (state) => MoneyEntryScreen(
      invoiceId: _idOf(state),
      kind: MoneyEntryKind.payment,
    ),
    '${BillingRoutes.desk}/invoices/:id/refund': (state) => MoneyEntryScreen(
      invoiceId: _idOf(state),
      kind: MoneyEntryKind.refund,
    ),
  };
  // Nursing pages for the Nurse role, pharmacy pages for Pharmacist and
  // Compounder. Other roles keep ModuleScreen there.
  final nurseScreens = <String, Widget Function(GoRouterState)>{
    NursingRoutes.ward: (_) => const WardPatientsScreen(),
    '${NursingRoutes.ward}/patients/:id': (state) =>
        WardPatientScreen(patientId: _idOf(state)),
  };
  final pharmacyScreens = <String, Widget Function(GoRouterState)>{
    PharmacyRoutes.home: (_) => const PharmacyScreen(),
    '${PharmacyRoutes.home}/prescriptions/:id': (state) =>
        DispenseScreen(prescriptionId: _idOf(state)),
    '${PharmacyRoutes.home}/medicines/:id': (state) =>
        MedicineScreen(medicineId: _idOf(state)),
  };
  // Emergency, IPD and hospital pages, for every role whose permissions open
  // the module (redirectFor). Each page offers only what the role may do;
  // the server checks every request.
  final opsScreens = <String, Widget Function(GoRouterState)>{
    EmergencyRoutes.list: (_) => const EmergencyScreen(),
    '${EmergencyRoutes.list}/:id': (state) =>
        EmergencyVisitScreen(visitId: _idOf(state)),
    IpdRoutes.list: (_) => const IpdScreen(),
    '${IpdRoutes.list}/:id': (state) =>
        AdmissionScreen(admissionId: _idOf(state)),
    HospitalRoutes.hospitals: (_) => const HospitalOverviewScreen(),
    HospitalRoutes.departments: (_) => const DepartmentsScreen(),
    HospitalRoutes.staff: (_) => const StaffScreen(),
  };
  GoRoute rolePage(
    String path,
    bool Function(SessionState) allowed,
    Widget Function(GoRouterState) build,
  ) => GoRoute(
    path: path,
    pageBuilder: (_, state) {
      final location = state.uri.path;
      final item = findNavMatch(location)?.item;
      final Widget child = allowed(session.state) || item == null
          ? PatientPage(location: location, child: build(state))
          : ModuleScreen(item: item, location: location);
      return _page(state, child);
    },
  );
  GoRoute doctorPage(String path, Widget Function(GoRouterState) build) =>
      GoRoute(
        path: path,
        pageBuilder: (_, state) {
          final location = state.uri.path;
          final item = findNavMatch(location)?.item;
          final Widget child = isDoctor(session.state) || item == null
              ? PatientPage(location: location, child: build(state))
              : ModuleScreen(item: item, location: location);
          return _page(state, child);
        },
      );
  return GoRouter(
    initialLocation: initialLocation,
    refreshListenable: session,
    redirect: (_, state) => redirectFor(session.state, state.uri.path),
    // An unknown path (old link, typo) falls back to Home instead of a blank page.
    onException: (_, _, router) => router.go(AppRoutes.home),
    routes: [
      ShellRoute(
        builder: (context, state, child) =>
            AppShell(location: state.uri.path, child: child),
        routes: [
          GoRoute(
            path: AppRoutes.home,
            pageBuilder: (_, state) => _page(state, const DashboardScreen()),
          ),
          page(
            AppRoutes.settings,
            (location) => SettingsScreen(location: location),
          ),
          page(
            AppRoutes.staffLogin,
            (location) => StaffLoginScreen(location: location),
          ),
          page(
            AppRoutes.patientLogin,
            (location) => PatientLoginScreen(location: location),
          ),
          page(
            AppRoutes.register,
            (location) => RegisterScreen(location: location),
          ),
          patientPage(PatientRoutes.book, BookAppointmentScreen.new),
          for (final entry in patientScreens.entries)
            patientPage(entry.key, entry.value),
          for (final entry in doctorScreens.entries)
            doctorPage(entry.key, entry.value),
          for (final entry in nurseScreens.entries)
            rolePage(entry.key, isNurse, entry.value),
          for (final entry in pharmacyScreens.entries)
            rolePage(entry.key, isPharmacyStaff, entry.value),
          for (final entry in deskScreens.entries)
            GoRoute(
              path: entry.key,
              pageBuilder: (_, state) => _page(
                state,
                PatientPage(
                  location: state.uri.path,
                  child: entry.value(state),
                ),
              ),
            ),
          for (final entry in opsScreens.entries)
            GoRoute(
              path: entry.key,
              pageBuilder: (_, state) => _page(
                state,
                StaffModulePage(
                  location: state.uri.path,
                  child: entry.value(state),
                ),
              ),
            ),
          for (final group in [...staffNav, ...patientNav])
            for (final item in group.items)
              if (!ownScreens.contains(item.path) &&
                  !patientScreens.containsKey(item.path) &&
                  !doctorScreens.containsKey(item.path) &&
                  !nurseScreens.containsKey(item.path) &&
                  !pharmacyScreens.containsKey(item.path) &&
                  !deskScreens.containsKey(item.path) &&
                  !opsScreens.containsKey(item.path))
                page(
                  item.path,
                  (location) => ModuleScreen(item: item, location: location),
                ),
        ],
      ),
    ],
  );
}

/// Where [location] should go for [session], or null to stay.
///
/// * Visitors: staff pages show "sign in required" (as on the web); patient
///   pages send them to patient sign-in.
/// * Signed in: sign-in pages go Home. Patients see Home, Settings and the
///   patient pages only. Staff are sent Home with `?denied=` when their role
///   may not view a module, as the web's ProtectedRoute does.
String? redirectFor(SessionState session, String location) {
  final patientPage = location.startsWith('/patient/');
  if (!session.isSignedIn) return patientPage ? AppRoutes.patientLogin : null;
  if (AppRoutes.signedOutOnly.contains(location)) return AppRoutes.home;
  if (session.isPatient) {
    final allowed =
        location == AppRoutes.home ||
        location == AppRoutes.settings ||
        patientPage;
    return allowed ? null : AppRoutes.home;
  }
  if (patientPage) return AppRoutes.home;
  final match = findNavMatch(location);
  if (match == null) return null;
  final adminBlocked =
      match.group.adminOnly && !adminModules.any(session.canView);
  final moduleBlocked =
      match.item.module != null && !session.canView(match.item.module);
  if (adminBlocked || moduleBlocked) {
    return Uri(
      path: AppRoutes.home,
      queryParameters: {'denied': match.item.path},
    ).toString();
  }
  return null;
}

/// The numeric path parameter [name]; 0 (never a real id: the server answers
/// 404) when it is not a number.
int _idOf(GoRouterState state, [String name = 'id']) =>
    int.tryParse(state.pathParameters[name] ?? '') ?? 0;

/// Pages swap without a slide inside the shell, as on the web.
Page<void> _page(GoRouterState state, Widget child) =>
    NoTransitionPage<void>(key: state.pageKey, child: child);
