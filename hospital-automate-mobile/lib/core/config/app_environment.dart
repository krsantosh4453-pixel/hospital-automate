/// Which deployment this build talks to, set at build time:
///
///     flutter build apk --dart-define=APP_ENV=production --dart-define=API_ORIGIN=https://hms.example.org
enum AppEnvironment {
  development,
  staging,
  production;

  /// Staging and production carry real hospital data, so they must use HTTPS.
  bool get requiresHttps => this != AppEnvironment.development;

  static AppEnvironment parse(String value) {
    return switch (value.trim().toLowerCase()) {
      '' || 'dev' || 'development' => AppEnvironment.development,
      'staging' => AppEnvironment.staging,
      'prod' || 'production' => AppEnvironment.production,
      _ => throw ArgumentError.value(
        value,
        'APP_ENV',
        'must be development, staging or production',
      ),
    };
  }
}
