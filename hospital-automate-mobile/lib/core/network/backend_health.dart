import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Outcome of one call to the backend's public /health/ endpoint.
@immutable
class HealthResult {
  const HealthResult({required this.reachable, required this.message});

  final bool reachable;
  final String message;
}

/// Runs one health check against the configured backend.
typedef HealthCheck = Future<HealthResult> Function();

/// Checks that the app can talk to the Django backend.
class BackendHealth {
  BackendHealth(this._dio);

  final Dio _dio;

  Future<HealthResult> check(String healthUrl) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(healthUrl);
      final body = response.data ?? const {};
      final status = body['status'];
      if (status == 'healthy') {
        return HealthResult(
          reachable: true,
          message: '${body['service'] ?? 'Backend'} is healthy',
        );
      }
      return HealthResult(
        reachable: false,
        message: 'Backend answered with status "$status"',
      );
    } on DioException catch (error) {
      return HealthResult(reachable: false, message: _explain(error));
    }
  }

  String _explain(DioException error) {
    final code = error.response?.statusCode;
    if (code == 400) {
      return 'Backend refused this host (HTTP 400). Add it to ALLOWED_HOSTS in the development settings.';
    }
    if (code != null) {
      return 'Backend answered HTTP $code';
    }
    return switch (error.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.receiveTimeout ||
      DioExceptionType.sendTimeout =>
        'Backend did not answer in time. Is runserver still starting?',
      _ => 'Cannot reach the backend. Is runserver running, and is the address right?',
    };
  }
}
