import 'package:flutter/widgets.dart';

import '../features/auth/auth_service.dart';
import '../features/billing/data/billing_repository.dart';
import '../features/laboratory/data/lab_repository.dart';
import '../features/dashboard/dashboard_repository.dart';
import '../features/doctor/data/doctor_repository.dart';
import '../features/patient/data/patient_repository.dart';
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
