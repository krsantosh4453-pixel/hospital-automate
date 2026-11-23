import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/config/api_config.dart';
import 'package:hms_mobile/core/config/app_environment.dart';

void main() {
  group('ApiConfig.resolveOrigin', () {
    test(
      'uses 10.0.2.2 on Android so the emulator reaches the host machine',
      () {
        final origin = ApiConfig.resolveOrigin(
          override: '',
          platform: TargetPlatform.android,
        );

        expect(origin, 'http://10.0.2.2:8000');
      },
    );

    test(
      'uses localhost on iOS, where the simulator shares the host network',
      () {
        final origin = ApiConfig.resolveOrigin(
          override: '',
          platform: TargetPlatform.iOS,
        );

        expect(origin, 'http://localhost:8000');
      },
    );

    test(
      'prefers the API_ORIGIN override, e.g. a LAN address for a real phone',
      () {
        final origin = ApiConfig.resolveOrigin(
          override: 'http://192.168.1.20:8000',
          platform: TargetPlatform.android,
        );

        expect(origin, 'http://192.168.1.20:8000');
      },
    );

    test('drops a trailing slash from the override', () {
      final origin = ApiConfig.resolveOrigin(
        override: 'https://staging.example.com/',
        platform: TargetPlatform.iOS,
      );

      expect(origin, 'https://staging.example.com');
    });

    test('rejects an override that is not an http(s) URL', () {
      expect(
        () => ApiConfig.resolveOrigin(
          override: '192.168.1.20:8000',
          platform: TargetPlatform.android,
        ),
        throwsArgumentError,
      );
    });
  });

  test('apiBaseUrl and healthUrl are built from the origin', () {
    const config = ApiConfig(origin: 'http://10.0.2.2:8000');

    expect(config.apiBaseUrl, 'http://10.0.2.2:8000/api/v1');
    expect(config.healthUrl, 'http://10.0.2.2:8000/health/');
  });

  group('ApiConfig.resolve per environment', () {
    test('development allows plain http and the emulator default', () {
      final config = ApiConfig.resolve(
        override: '',
        platform: TargetPlatform.android,
        environment: AppEnvironment.development,
      );

      expect(config.origin, 'http://10.0.2.2:8000');
      expect(config.environment, AppEnvironment.development);
    });

    test('production refuses a plain http origin', () {
      expect(
        () => ApiConfig.resolve(
          override: 'http://hms.example.org',
          platform: TargetPlatform.android,
          environment: AppEnvironment.production,
        ),
        throwsArgumentError,
      );
    });

    test('staging and production require an explicit origin', () {
      for (final environment in [
        AppEnvironment.staging,
        AppEnvironment.production,
      ]) {
        expect(
          () => ApiConfig.resolve(
            override: '',
            platform: TargetPlatform.android,
            environment: environment,
          ),
          throwsArgumentError,
        );
      }
    });

    test('a release build refuses the development environment', () {
      expect(
        () => ApiConfig.resolve(
          override: '',
          platform: TargetPlatform.android,
          environment: AppEnvironment.development,
          releaseBuild: true,
        ),
        throwsArgumentError,
      );
      final config = ApiConfig.resolve(
        override: 'https://hms.example.org',
        platform: TargetPlatform.android,
        environment: AppEnvironment.production,
        releaseBuild: true,
      );
      expect(config.origin, 'https://hms.example.org');
    });

    test('production accepts an https origin', () {
      final config = ApiConfig.resolve(
        override: 'https://hms.example.org',
        platform: TargetPlatform.iOS,
        environment: AppEnvironment.production,
      );

      expect(config.apiBaseUrl, 'https://hms.example.org/api/v1');
    });
  });

  group('AppEnvironment.parse', () {
    test('defaults to development and accepts short names', () {
      expect(AppEnvironment.parse(''), AppEnvironment.development);
      expect(AppEnvironment.parse('prod'), AppEnvironment.production);
      expect(AppEnvironment.parse('Staging'), AppEnvironment.staging);
    });

    test('rejects an unknown name instead of guessing', () {
      expect(() => AppEnvironment.parse('live'), throwsArgumentError);
    });
  });
}
