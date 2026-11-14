import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// What went wrong with an API call, as the UI needs to know it.
enum ApiErrorKind {
  network,
  timeout,
  unauthorized,
  forbidden,
  notFound,
  validation,
  conflict,
  rateLimited,
  server,
  unavailable,
  unknown,
}

/// A failed API call. The backend answers in one of two shapes:
///
/// * sign-in views: `{"error": "Invalid credentials.", "otp_unavailable": true}`
/// * everything else (DRF handler): `{"error": true, "status_code": 400,
///   "message": "...", "details": {...}}`
///
/// Screens choose what to show from [kind] (see `apiErrorMessage`), or, on
/// sign-in screens, from [serverMessage] matched against known texts (see
/// `authErrorMessage`); the raw text is never logged. [flags] keeps boolean
/// markers such as `otp_unavailable`, and [fieldErrors] the validation detail
/// for the form that sent the data.
@immutable
class ApiException implements Exception {
  const ApiException({
    required this.kind,
    this.statusCode,
    this.fieldErrors = const {},
    this.serverMessage,
    this.flags = const {},
  });

  factory ApiException.fromDio(DioException error) {
    final status = error.response?.statusCode;
    if (status != null) {
      final body = error.response?.data;
      return ApiException(
        kind: kindForStatus(status),
        statusCode: status,
        fieldErrors: _fieldErrors(body),
        serverMessage: _serverMessage(body),
        flags: _flags(body),
      );
    }
    return ApiException(
      kind: switch (error.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.sendTimeout ||
        DioExceptionType.receiveTimeout => ApiErrorKind.timeout,
        DioExceptionType.connectionError ||
        DioExceptionType.badCertificate => ApiErrorKind.network,
        _ => ApiErrorKind.unknown,
      },
    );
  }

  final ApiErrorKind kind;
  final int? statusCode;

  /// Field name to the reasons the server gave, for a 400 response.
  final Map<String, List<String>> fieldErrors;

  /// The server's own sentence (`error` text or envelope `message`), if any.
  /// For matching known sign-in failures only: never log it or show it raw.
  final String? serverMessage;

  /// Names of `true` boolean fields in the body, e.g. `otp_unavailable`.
  final Set<String> flags;

  bool hasFlag(String name) => flags.contains(name);

  static ApiErrorKind kindForStatus(int status) {
    return switch (status) {
      400 || 422 => ApiErrorKind.validation,
      401 => ApiErrorKind.unauthorized,
      403 => ApiErrorKind.forbidden,
      404 => ApiErrorKind.notFound,
      409 => ApiErrorKind.conflict,
      429 => ApiErrorKind.rateLimited,
      503 => ApiErrorKind.unavailable,
      >= 500 => ApiErrorKind.server,
      _ => ApiErrorKind.unknown,
    };
  }

  static Map<String, List<String>> _fieldErrors(Object? body) {
    if (body is! Map || body['details'] is! Map) return const {};
    final details = body['details'] as Map;
    return {
      for (final entry in details.entries)
        if (entry.value is List)
          '${entry.key}': [for (final reason in entry.value as List) '$reason'],
    };
  }

  static String? _serverMessage(Object? body) {
    if (body is! Map) return null;
    final error = body['error'];
    if (error is String && error.isNotEmpty) return error;
    final message = body['message'];
    return message is String && message.isNotEmpty ? message : null;
  }

  static Set<String> _flags(Object? body) {
    if (body is! Map) return const {};
    return {
      for (final entry in body.entries)
        if (entry.value == true && entry.key != 'error') '${entry.key}',
    };
  }

  @override
  String toString() =>
      'ApiException(${kind.name}${statusCode == null ? '' : ', HTTP $statusCode'})';
}
