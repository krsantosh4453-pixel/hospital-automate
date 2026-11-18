import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/app.dart';
import 'package:hms_mobile/core/app_scope.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/localization/locale_controller.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/backend_health.dart';
import 'package:hms_mobile/core/security/session_controller.dart';
import 'package:hms_mobile/core/security/token_store.dart';
import 'package:hms_mobile/features/auth/auth_repository.dart';
import 'package:hms_mobile/features/auth/auth_service.dart';
import 'package:hms_mobile/features/auth/google_identity.dart';
import 'package:hms_mobile/features/dashboard/dashboard_repository.dart';
import 'package:hms_mobile/features/dashboard/dashboard_stats.dart';
import 'package:hms_mobile/features/doctor/data/doctor_repository.dart';
import 'package:hms_mobile/features/billing/data/billing_repository.dart';
import 'package:hms_mobile/features/laboratory/data/lab_repository.dart';
import 'package:hms_mobile/features/nursing/data/nursing_repository.dart';
import 'package:hms_mobile/features/pharmacy/data/pharmacy_repository.dart';
import 'package:hms_mobile/features/patient/data/patient_repository.dart';

import 'fake_auth_repository.dart';
import 'fake_doctor_repository.dart';
import 'fake_patient_repository.dart';
import 'fake_billing_repository.dart';
import 'fake_nursing_repository.dart';
import 'fake_pharmacy_repository.dart';
import 'fake_lab_repository.dart';

export 'fake_auth_repository.dart';
export 'fake_doctor_repository.dart';
export 'fake_patient_repository.dart';
export 'fake_billing_repository.dart';
export 'fake_nursing_repository.dart';
export 'fake_pharmacy_repository.dart';
export 'fake_lab_repository.dart';

/// Answers every request with [respond] instead of touching the network.
class FakeAdapter implements HttpClientAdapter {
  FakeAdapter(this.respond);

  final Future<ResponseBody> Function(RequestOptions options) respond;
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) {
    requests.add(options);
    return respond(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody jsonBody(String body, int status) => ResponseBody.fromString(
  body,
  status,
  headers: {
    Headers.contentTypeHeader: [Headers.jsonContentType],
  },
);

/// Returns fixed dashboard figures (or throws [error]) and counts calls.
class FakeDashboardRepository implements DashboardRepository {
  FakeDashboardRepository({this.stats, this.error});

  DashboardStats? stats;
  Object? error;
  final List<int> requestedHospitals = [];

  @override
  Future<DashboardStats> fetch(int hospitalId) async {
    requestedHospitals.add(hospitalId);
    if (error != null) throw error!;
    return stats!;
  }
}

const testConfig = ApiConfig(origin: 'http://10.0.2.2:8000');

/// Services wired to fakes: no network, no keystore, no preferences.
AppServices testServices({
  SessionState session = SessionState.signedOut,
  DashboardRepository? dashboard,
  HealthCheck? checkHealth,
  AppLanguage language = AppLanguage.en,
  AuthRepository? authRepository,
  TokenStore? tokenStore,
  PatientRepository? patient,
  DoctorRepository? doctor,
  LabRepository? laboratory,
  BillingRepository? billing,
  NursingRepository? nursing,
  PharmacyRepository? pharmacy,
  GoogleIdentity? google,
}) {
  final store = tokenStore ?? InMemoryTokenStore();
  final controller = SessionController(tokenStore: store, initial: session);
  return AppServices(
    config: testConfig,
    api: ApiClient(
      config: testConfig,
      accessToken: controller.accessToken,
      hospitalId: () => controller.activeHospitalId,
      adapter: FakeAdapter((_) async => jsonBody('{}', 200)),
      log: (_) {},
    ),
    session: controller,
    auth: AuthService(
      repository: authRepository ?? FakeAuthRepository(),
      session: controller,
      store: store,
      appVersion: 'test',
      google: google,
      platform: TargetPlatform.android,
    ),
    locale: LocaleController(
      preference: InMemoryLanguagePreference(language),
      initial: language,
    ),
    checkHealth:
        checkHealth ??
        () async => const HealthResult(
          reachable: true,
          message: 'hms-backend is healthy',
        ),
    dashboard: dashboard ?? FakeDashboardRepository(),
    patient: patient ?? FakePatientRepository(),
    doctor: doctor ?? FakeDoctorRepository(),
    laboratory: laboratory ?? FakeLabRepository(),
    billing: billing ?? FakeBillingRepository(),
    nursing: nursing ?? FakeNursingRepository(),
    pharmacy: pharmacy ?? FakePharmacyRepository(),
  );
}

/// A signed-in patient at hospital 7. Names and numbers are synthetic.
SessionState patientSession({
  AccountType accountType = AccountType.patient,
  List<HospitalContext> hospitals = const [
    HospitalContext(id: 7, name: 'Test General Hospital', role: 'Patient'),
  ],
}) => SessionState(
  user: SessionUser(
    displayName: 'Test Patient',
    firstName: 'Test',
    accountType: accountType,
    patient: const PatientProfile(
      id: 41,
      name: 'Test Patient',
      age: 30,
      gender: 'Female',
      phone: '9000000001',
      email: 'patient@example.test',
      phoneVerified: true,
    ),
  ),
  hospitals: hospitals,
  activeHospitalId: hospitals.first.id,
);

/// Phone (412×915, Pixel 7 class), tablet and desktop logical sizes.
const phoneSize = Size(412, 915);
const smallPhoneSize = Size(320, 640);
const tabletSize = Size(820, 1180);
const desktopSize = Size(1440, 900);

Future<void> pumpApp(
  WidgetTester tester,
  AppServices services, {
  Size size = phoneSize,
  String location = '/',
}) async {
  tester.view.physicalSize = size * 3;
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  // A new key every call: HmsApp builds its router once, so re-pumping the
  // same app would keep the first location instead of opening [location].
  await tester.pumpWidget(
    HmsApp(key: UniqueKey(), services: services, initialLocation: location),
  );
  await tester.pumpAndSettle();
}

/// A signed-in staff session for widget tests. Names and figures are synthetic.
SessionState staffSession({
  String role = 'Admin',
  Set<String> permissions = allViewPermissions,
  String? firstName = 'Asha',
}) => SessionState(
  user: SessionUser(displayName: 'asha.test', firstName: firstName),
  hospitals: [
    HospitalContext(
      id: 7,
      name: 'Test General Hospital',
      role: role,
      permissions: permissions,
    ),
  ],
  activeHospitalId: 7,
);

const allViewPermissions = {
  'Dashboard.View',
  'Patients.View',
  'Appointments.View',
  'Queue.View',
  'Doctors.View',
  'Nurses.View',
  'Compounders.View',
  'Pharmacy.View',
  'Laboratory.View',
  'Billing.View',
  'Inventory.View',
  'Prescriptions.View',
  'Reports.View',
  'Emergency.View',
  'BloodBank.View',
  'IPD.View',
  'AIScribe.View',
  'Users.View',
  'Roles.View',
  'Hospitals.View',
  'Departments.View',
  'Permissions.View',
};

/// The shape `/home/stats/detail/` returns, with synthetic values.
const statsJson = {
  'statistics': {
    'patients': {'total': 1250, 'today': 12},
    'doctors': {'total': 8, 'active': 5},
    'appointments': {'total': 300, 'today': 18, 'pending': 6, 'completed': 10},
    'queue': {
      'total': 40,
      'waiting': 4,
      'in_consultation': 2,
      'completed': 20,
      'current_token': 17,
    },
    'beds': {'total': 50, 'available': 9, 'occupied': 41},
    'emergency': {'total': 30, 'today': 3, 'active': 1},
    'admissions': {'total': 200, 'current': 41},
    'laboratory': {'total': 90, 'pending': 5, 'completed': 60, 'urgent': 2},
    'billing': {
      'total_invoices': 120,
      'paid': 100,
      'pending': 7,
      'partial': 3,
      'total_revenue': 250000.0,
      'today_revenue': 18500.0,
    },
  },
  'recent_patients': [
    {
      'id': 101,
      'name': 'Test Patient One',
      'patient_id': 'P101',
      'age': 34,
      'gender': 'Female',
      'created_at': '2026-11-10T09:30:00Z',
    },
    {
      'id': 102,
      'name': 'Test Patient Two',
      'patient_id': 'P102',
      'age': 61,
      'gender': 'Male',
      'created_at': '2026-11-10T08:05:00Z',
    },
  ],
};
