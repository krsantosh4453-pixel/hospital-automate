/// Route paths outside the sidebar. Sidebar paths live in `nav_config.dart`
/// and match the web app's URLs.
abstract final class AppRoutes {
  static const home = '/';
  static const settings = '/settings';
  static const staffLogin = '/staff-login';
  static const patientLogin = '/patient-login';
  static const register = '/register';

  /// Pages only signed-out visitors need; signed-in people are sent Home.
  static const signedOutOnly = {staffLogin, patientLogin, register};
}
