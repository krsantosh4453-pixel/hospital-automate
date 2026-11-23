import 'package:flutter/widgets.dart';

import '../features/ai/data/ai_repository.dart';
import '../features/ai/data/scribe_recorder.dart';
import '../features/auth/auth_service.dart';
import '../features/billing/data/billing_repository.dart';
import '../features/laboratory/data/lab_repository.dart';
import '../features/dashboard/dashboard_repository.dart';
import '../features/doctor/data/doctor_repository.dart';
import '../features/emergency/data/emergency_repository.dart';
import '../features/hospital/data/hospital_repository.dart';
import '../features/ipd/data/clinical_work_repository.dart';
import '../features/ipd/data/ipd_repository.dart';
import '../features/nursing/data/nursing_repository.dart';
import '../features/patient/data/patient_repository.dart';
import '../features/pharmacy/data/pharmacy_repository.dart';
import '../features/reception/data/reception_repository.dart';
import 'config/api_config.dart';
import 'localization/locale_controller.dart';
import 'network/api_client.dart';
import 'network/backend_health.dart';
import 'security/session_controller.dart';

/// The app's long-lived services, built once in `main.dart` (or by a test)
/// and handed down the widget tree. Screens read them with [AppScope.of].
@immutable
class AppServices {
  const AppServices({
    required this.config,
    required this.api,
    required this.session,
    required this.auth,
    required this.locale,
    required this.checkHealth,
    required this.dashboard,
    required this.patient,
    required this.doctor,
    required this.laboratory,
    required this.billing,
    required this.nursing,
    required this.pharmacy,
    required this.emergency,
    required this.ipd,
    required this.hospital,
    this.aiOverride,
    this.receptionOverride,
    this.clinicalWorkOverride,
    this.scribeRecorderFactory,
  });

  final ApiConfig config;
  final ApiClient api;
  final SessionController session;

  /// Sign-in, sign-out, token refresh and session restore.
  final AuthService auth;
  final LocaleController locale;
  final HealthCheck checkHealth;
  final DashboardRepository dashboard;

  /// The signed-in patient's own records (patient portal pages).
  final PatientRepository patient;

  /// Clinical work of the signed-in doctor (doctor pages).
  final DoctorRepository doctor;

  /// Laboratory orders and their workflow (lab desk pages).
  final LabRepository laboratory;

  /// Invoices, payments and refunds (billing desk pages).
  final BillingRepository billing;

  /// Ward work of the signed-in nurse (nursing pages).
  final NursingRepository nursing;

  /// Stock, prescriptions and dispensing (pharmacy pages).
  final PharmacyRepository pharmacy;

  /// Emergency department visits of the acting hospital (Emergency pages).
  final EmergencyRepository emergency;

  /// Admissions, beds and discharges (IPD pages).
  final IpdRepository ipd;

  /// The acting hospital's record, departments, wards and staff.
  final HospitalRepository hospital;

  /// Tests pass a fake here; the app uses the API (see [ai]).
  final AiRepository? aiOverride;

  /// AI scribe and AI status pages. Optional so existing wiring in
  /// `main.dart` and tests keeps compiling; the repository holds no state.
  AiRepository get ai => aiOverride ?? ApiAiRepository(api);

  /// Tests pass a fake here; the app uses the API (see [reception]).
  final ReceptionRepository? receptionOverride;

  /// Front desk writes: register, link and check in (BUG-01). Optional for
  /// the same reason as [ai]; the repository holds no state.
  ReceptionRepository get reception =>
      receptionOverride ?? ApiReceptionRepository(api);

  /// Tests pass a fake here; the app uses the API (see [clinicalWork]).
  final ClinicalWorkRepository? clinicalWorkOverride;

  /// Allergies, admitting, ward orders, discharge forms, the stay's final
  /// bill and the patient's history (Prompt 3). Holds no state.
  ClinicalWorkRepository get clinicalWork =>
      clinicalWorkOverride ?? ApiClinicalWorkRepository(api);

  /// Tests pass a fake microphone here.
  final ScribeRecorder Function()? scribeRecorderFactory;

  /// A new recorder for one scribe screen (disposed with it).
  ScribeRecorder newScribeRecorder() =>
      (scribeRecorderFactory ?? DeviceScribeRecorder.new)();
}

class AppScope extends InheritedWidget {
  const AppScope({super.key, required this.services, required super.child});

  final AppServices services;

  static AppServices of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope is missing above this widget');
    return scope!.services;
  }

  /// Like [of] without subscribing to changes, so it may be called from
  /// `initState` (the services are built once and never replaced).
  static AppServices read(BuildContext context) {
    final scope = context.getInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope is missing above this widget');
    return scope!.services;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) =>
      !identical(services, oldWidget.services);
}
