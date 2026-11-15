import 'package:flutter/foundation.dart';

import 'app_environment.dart';

/// Where the app finds the Django backend.
///
/// Development defaults suit local work: the Android emulator reaches the
/// host machine at 10.0.2.2, the iOS simulator at localhost. For a real phone
/// on the same Wi-Fi, or a staging server, pass the origin at build time:
///
///     flutter run --dart-define=API_ORIGIN=http://192.168.1.20:8000
///
/// Staging and production builds must name an `https://` origin.
@immutable
class ApiConfig {
  const ApiConfig({
    required this.origin,
    this.environment = AppEnvironment.development,
  });

  /// Built from `--dart-define=APP_ENV=...`, `--dart-define=API_ORIGIN=...`
  /// and the running platform. Throws [ArgumentError] for an unsafe setup.
  factory ApiConfig.fromEnvironment() => resolve(
    override: _originOverride,
    platform: defaultTargetPlatform,
    environment: AppEnvironment.parse(_environmentName),
  );

  static const _originOverride = String.fromEnvironment('API_ORIGIN');
  static const _environmentName = String.fromEnvironment('APP_ENV');
  static const _androidEmulatorOrigin = 'http://10.0.2.2:8000';
  static const _localOrigin = 'http://localhost:8000';

  /// Scheme, host and port, with no trailing slash.
  final String origin;

  final AppEnvironment environment;

  /// Versioned DRF routes (`/api/v1/`), the contract for the mobile app.
  String get apiBaseUrl => '$origin/api/v1';

  /// Public health check, mounted outside /api/.
  String get healthUrl => '$origin/health/';

  /// The configuration for [environment], refusing plain HTTP outside development.
  static ApiConfig resolve({
    required String override,
    required TargetPlatform platform,
    required AppEnvironment environment,
  }) {
    if (environment.requiresHttps && override.isEmpty) {
      throw ArgumentError.value(
        override,
        'API_ORIGIN',
        'is required for a ${environment.name} build',
      );
    }
    final origin = resolveOrigin(override: override, platform: platform);
    if (environment.requiresHttps && !Uri.parse(origin).isScheme('https')) {
      throw ArgumentError.value(
        origin,
        'API_ORIGIN',
        'must use https:// in a ${environment.name} build',
      );
    }
    return ApiConfig(origin: origin, environment: environment);
  }

  @visibleForTesting
  static String resolveOrigin({
    required String override,
    required TargetPlatform platform,
  }) {
    if (override.isNotEmpty) {
      final uri = Uri.tryParse(override);
      if (uri == null ||
          !(uri.isScheme('http') || uri.isScheme('https')) ||
          uri.host.isEmpty) {
        throw ArgumentError.value(
          override,
          'API_ORIGIN',
          'must be an http(s) URL such as http://192.168.1.20:8000',
        );
      }
      return override.endsWith('/')
          ? override.substring(0, override.length - 1)
          : override;
    }
    return platform == TargetPlatform.android
        ? _androidEmulatorOrigin
        : _localOrigin;
  }
}
