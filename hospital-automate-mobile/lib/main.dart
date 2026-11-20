import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import 'app.dart';
import 'core/app_scope.dart';
import 'core/config/api_config.dart';
import 'core/config/app_info.dart';
import 'core/localization/locale_controller.dart';
import 'core/network/api_client.dart';
import 'core/network/backend_health.dart';
import 'core/security/session_controller.dart';
import 'core/security/token_store.dart';
import 'features/auth/auth_repository.dart';
import 'features/auth/auth_service.dart';
import 'features/auth/google_identity.dart';
import 'features/ai/data/scribe_recorder.dart';
import 'features/billing/data/billing_repository.dart';
import 'features/dashboard/dashboard_repository.dart';
import 'features/laboratory/data/lab_repository.dart';
import 'features/doctor/data/doctor_repository.dart';
import 'features/emergency/data/emergency_repository.dart';
import 'features/hospital/data/hospital_repository.dart';
import 'features/ipd/data/ipd_repository.dart';
import 'features/nursing/data/nursing_repository.dart';
import 'features/patient/data/patient_repository.dart';
import 'features/pharmacy/data/pharmacy_repository.dart';

const _healthTimeout = Duration(seconds: 10);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Fails fast on an unsafe build (e.g. production without https://).
  final config = ApiConfig.fromEnvironment();

  final languagePreference = SharedPreferencesLanguagePreference();
  final locale = LocaleController(
    preference: languagePreference,
    initial: await _savedLanguage(languagePreference),
  );
  final store = SecureTokenStore();
  // Before anything reads the Keychain: a reinstall starts signed out.
  await forgetSessionFromPreviousInstall(
    store,
    SharedPreferencesInstallMarker(),
  );
  final session = SessionController(tokenStore: store);
  // Consultation audio never outlives an upload, a crash or a sign-out.
  unawaited(_sweepRecordings());
  session.onSignOut(_sweepRecordings);
  final api = ApiClient(
    config: config,
    accessToken: session.accessToken,
    hospitalId: () => session.activeHospitalId,
    blockAuthenticated: () => session.isClosing,
  );
  final auth = AuthService(
    repository: ApiAuthRepository(api),
    session: session,
    store: store,
    appVersion: AppInfo.version,
    google: PluginGoogleIdentity(serverClientId: GoogleConfig.serverClientId),
  );
  // Expired access tokens are renewed through the same client.
  api.attachRefreshHandler(auth);
  // Resume a stored session; the app shows a loading cover until it settles.
  unawaited(auth.restore());

  // /health/ is outside /api/v1/, so it uses its own small client.
  final health = BackendHealth(
    Dio(
      BaseOptions(
        connectTimeout: _healthTimeout,
        receiveTimeout: _healthTimeout,
      ),
    ),
  );

  final doctor = ApiDoctorRepository(api);
  runApp(
    HmsApp(
      services: AppServices(
        config: config,
        api: api,
        session: session,
        auth: auth,
        locale: locale,
        checkHealth: () => health.check(config.healthUrl),
        dashboard: ApiDashboardRepository(api),
        patient: ApiPatientRepository(api),
        doctor: doctor,
        laboratory: ApiLabRepository(api),
        billing: ApiBillingRepository(api),
        nursing: ApiNursingRepository(api, doctor),
        pharmacy: ApiPharmacyRepository(api),
        emergency: ApiEmergencyRepository(api),
        ipd: ApiIpdRepository(api),
        hospital: ApiHospitalRepository(api),
      ),
    ),
  );
}

Future<AppLanguage> _savedLanguage(LanguagePreference preference) async {
  try {
    return await preference.read();
  } on Exception {
    return AppLanguage.en;
  }
}

Future<void> _sweepRecordings() async {
  try {
    await deleteLeftoverRecordingsInTemp();
  } on Exception catch (_) {
    // Best effort: a file that cannot be listed or deleted now is retried at
    // the next start-up or sign-out.
  }
}
