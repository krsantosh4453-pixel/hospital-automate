import 'dart:developer' as developer;
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../config/api_config.dart';
import 'api_exception.dart';

/// Reads the current access token, or null when signed out.
typedef AccessTokenReader = Future<String?> Function();

/// Reads the hospital the user acts in, sent as `X-Hospital-ID`.
typedef HospitalIdReader = int? Function();

/// Turns a decoded JSON body into a typed result.
typedef JsonDecoder<T> = T Function(Object? json);

/// Writes one line of request log. Receives no bodies, query strings or headers.
typedef ApiLogSink = void Function(String line);

/// What happened when the client tried to renew an expired access token.
enum RefreshOutcome {
  /// A new access token is stored; retry the request.
  refreshed,

  /// The server refused the refresh token: the session is over.
  rejected,

  /// The refresh call itself failed (network, server): keep the session.
  failed,
}

/// Renews the access token. [usedAccessToken] is the token the failed
/// request carried, so a refresh already done by another request is reused.
abstract interface class TokenRefreshHandler {
  Future<RefreshOutcome> refresh(String usedAccessToken);

  /// The session ended (refresh rejected): clear it locally.
  Future<void> onSessionExpired();
}

const _defaultTimeout = Duration(seconds: 15);
const _idempotencyKeyLength = 32;

/// `extra` keys on [RequestOptions].
const _anonymousKey = 'hms.anonymous';
const _usedTokenKey = 'hms.usedToken';
const _retriedKey = 'hms.retried';

void _developerLog(String line) => developer.log(line, name: 'hms.api');

/// The one HTTP client for the Django `/api/v1/` API.
///
/// Every request gets JSON headers, a request id, the bearer token when
/// signed in and the acting hospital. An expired access token is renewed
/// once (see [TokenRefreshHandler]) and the request retried. Failures
/// surface as [ApiException].
class ApiClient {
  ApiClient({
    required ApiConfig config,
    required AccessTokenReader accessToken,
    required HospitalIdReader hospitalId,
    HttpClientAdapter? adapter,
    ApiLogSink? log,
    Duration timeout = _defaultTimeout,
    bool Function()? blockAuthenticated,
  }) : dio = Dio(
         BaseOptions(
           baseUrl: '${config.apiBaseUrl}/',
           connectTimeout: timeout,
           receiveTimeout: timeout,
           sendTimeout: timeout,
           responseType: ResponseType.json,
           headers: const {'Accept': 'application/json'},
         ),
       ) {
    if (adapter != null) dio.httpClientAdapter = adapter;
    dio.interceptors.addAll([
      RequestContextInterceptor(
        accessToken: accessToken,
        hospitalId: hospitalId,
        blockAuthenticated: blockAuthenticated,
      ),
      _RefreshInterceptor(this),
      SafeLogInterceptor(log ?? (kDebugMode ? _developerLog : null)),
    ]);
  }

  final Dio dio;
  TokenRefreshHandler? _refreshHandler;

  /// Connects token renewal. Done after construction because the handler
  /// itself calls this client (`auth/token/refresh/`).
  void attachRefreshHandler(TokenRefreshHandler handler) =>
      _refreshHandler = handler;

  /// GET [path]. [anonymous] requests carry no token and never trigger a
  /// refresh (sign-in endpoints).
  Future<T> get<T>(
    String path, {
    Map<String, Object?>? query,
    bool anonymous = false,
    required JsonDecoder<T> decode,
  }) => _send(
    () => dio.get<Object?>(
      _relative(path),
      queryParameters: query,
      options: _options(anonymous: anonymous),
    ),
    decode,
  );

  /// POST [body]. Pass an [idempotencyKey] (see [newIdempotencyKey]) for
  /// writes the backend de-duplicates, and reuse it when retrying.
  Future<T> post<T>(
    String path, {
    Object? body,
    String? idempotencyKey,
    bool anonymous = false,
    required JsonDecoder<T> decode,
  }) => _send(
    () => dio.post<Object?>(
      _relative(path),
      data: body,
      options: _options(anonymous: anonymous, idempotencyKey: idempotencyKey),
    ),
    decode,
  );

  Future<T> patch<T>(
    String path, {
    Object? body,
    required JsonDecoder<T> decode,
  }) => _send(() => dio.patch<Object?>(_relative(path), data: body), decode);

  Future<void> delete(String path) =>
      _send(() => dio.delete<Object?>(_relative(path)), (_) {});

  /// A fresh key for `Idempotency-Key` (32 hex characters; the backend accepts up to 80).
  static String newIdempotencyKey([Random? random]) =>
      _randomHex(random ?? Random.secure(), _idempotencyKeyLength);

  Future<T> _send<T>(
    Future<Response<Object?>> Function() request,
    JsonDecoder<T> decode,
  ) async {
    try {
      final response = await request();
      return decode(response.data);
    } on DioException catch (error) {
      throw ApiException.fromDio(error);
    }
  }

  static Options _options({required bool anonymous, String? idempotencyKey}) =>
      Options(
        extra: {_anonymousKey: anonymous},
        headers: {'Idempotency-Key': ?idempotencyKey},
      );

  /// Paths are relative to `/api/v1/`; a leading slash would drop the prefix.
  static String _relative(String path) =>
      path.startsWith('/') ? path.substring(1) : path;
}

String _randomHex(Random random, int length) =>
    List.generate(length, (_) => random.nextInt(16).toRadixString(16)).join();

/// Adds the bearer token, `X-Hospital-ID` and `X-Request-ID` to each request.
/// The app never sends `X-Auth-Mode: cookie`, so tokens come back in the body.
class RequestContextInterceptor extends Interceptor {
  RequestContextInterceptor({
    required this.accessToken,
    required this.hospitalId,
    this.blockAuthenticated,
    Random? random,
  }) : _random = random ?? Random.secure();

  final AccessTokenReader accessToken;
  final HospitalIdReader hospitalId;

  /// True while a sign-out is in progress (and until the next sign-in):
  /// signed-in requests are then not sent at all. Final E2E finding 6: the
  /// open page reloaded during sign-out and sent 1-3 requests that could
  /// only come back 401.
  final bool Function()? blockAuthenticated;
  final Random _random;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    options.headers.remove('Authorization');
    if (options.extra[_anonymousKey] != true &&
        (blockAuthenticated?.call() ?? false)) {
      handler.reject(
        DioException(
          requestOptions: options,
          type: DioExceptionType.cancel,
          error: const SignedOutRequest(),
        ),
      );
      return;
    }
    if (options.extra[_anonymousKey] != true) {
      final token = await accessToken();
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
        options.extra[_usedTokenKey] = token;
      }
    }
    final hospital = hospitalId();
    if (hospital != null) {
      options.headers.putIfAbsent('X-Hospital-ID', () => '$hospital');
    }
    options.headers.putIfAbsent('X-Request-ID', () => _randomHex(_random, 16));
    handler.next(options);
  }
}

/// On a 401 for a request that carried a token: renew it once and retry.
class _RefreshInterceptor extends Interceptor {
  _RefreshInterceptor(this._client);

  final ApiClient _client;

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    final usedToken = options.extra[_usedTokenKey];
    final handlerForRefresh = _client._refreshHandler;
    if (err.response?.statusCode != 401 ||
        usedToken is! String ||
        options.extra[_retriedKey] == true ||
        handlerForRefresh == null) {
      handler.next(err);
      return;
    }
    final outcome = await handlerForRefresh.refresh(usedToken);
    switch (outcome) {
      case RefreshOutcome.refreshed:
        try {
          final retry = await _client.dio.fetch<Object?>(
            options.copyWith(extra: {...options.extra, _retriedKey: true}),
          );
          handler.resolve(retry);
        } on DioException catch (retryError) {
          handler.next(retryError);
        }
      case RefreshOutcome.rejected:
        await handlerForRefresh.onSessionExpired();
        handler.next(err);
      case RefreshOutcome.failed:
        handler.next(err);
    }
  }
}

/// Logs method, path and status but never the query string (it can hold a
/// patient search), bodies (passwords, OTPs) or headers (tokens).
class SafeLogInterceptor extends Interceptor {
  SafeLogInterceptor(this._sink);

  final ApiLogSink? _sink;
  static const _startedKey = 'hms.started';

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.extra[_startedKey] = DateTime.now();
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    _write(response.requestOptions, '${response.statusCode}');
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    _write(
      err.requestOptions,
      err.response?.statusCode?.toString() ?? err.type.name,
    );
    handler.next(err);
  }

  void _write(RequestOptions options, String outcome) {
    final sink = _sink;
    if (sink == null) return;
    final started = options.extra[_startedKey];
    final ms = started is DateTime
        ? DateTime.now().difference(started).inMilliseconds
        : null;
    final requestId = options.headers['X-Request-ID'] ?? '-';
    sink(
      '${options.method} ${options.uri.path} -> $outcome${ms == null ? '' : ' ${ms}ms'} [$requestId]',
    );
  }
}

/// A signed-in request refused locally because the session is ending.
class SignedOutRequest implements Exception {
  const SignedOutRequest();

  @override
  String toString() => 'The session is ending; the request was not sent.';
}
