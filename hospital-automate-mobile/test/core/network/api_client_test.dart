import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/api_client.dart';
import 'package:hms_mobile/core/network/api_exception.dart';

import '../../support/test_app.dart';

void main() {
  late FakeAdapter adapter;
  late List<String> logLines;

  ApiClient client({
    String? token = 'secret-access-token',
    int? hospital = 7,
    int status = 200,
    String body = '{"ok": true}',
  }) {
    adapter = FakeAdapter((_) async => jsonBody(body, status));
    logLines = [];
    return ApiClient(
      config: testConfig,
      accessToken: () async => token,
      hospitalId: () => hospital,
      adapter: adapter,
      log: logLines.add,
    );
  }

  test('sends requests under /api/v1/ with JSON, bearer token, hospital and request id', () async {
    final api = client();

    await api.get(
      '/home/stats/detail/',
      query: {'hospital': 7},
      decode: (json) => json,
    );

    final request = adapter.requests.single;
    expect(
      request.uri.toString(),
      'http://10.0.2.2:8000/api/v1/home/stats/detail/?hospital=7',
    );
    expect(request.headers['Accept'], 'application/json');
    expect(request.headers['Authorization'], 'Bearer secret-access-token');
    expect(request.headers['X-Hospital-ID'], '7');
    expect(request.headers['X-Request-ID'], matches(RegExp(r'^[0-9a-f]{16}$')));
  });

  test('sends no Authorization or X-Hospital-ID when signed out', () async {
    final api = client(token: null, hospital: null);

    await api.get('patients/', decode: (json) => json);

    expect(
      adapter.requests.single.headers.containsKey('Authorization'),
      isFalse,
    );
    expect(
      adapter.requests.single.headers.containsKey('X-Hospital-ID'),
      isFalse,
    );
  });

  test(
    'sends no signed-in request while the session is closing (finding 6)',
    () async {
      var closing = true;
      adapter = FakeAdapter((_) async => jsonBody('{"ok": true}', 200));
      final api = ApiClient(
        config: testConfig,
        accessToken: () async => 'secret-access-token',
        hospitalId: () => 7,
        adapter: adapter,
        blockAuthenticated: () => closing,
      );

      await expectLater(
        api.get('patients/', decode: (json) => json),
        throwsA(isA<ApiException>()),
      );
      expect(adapter.requests, isEmpty); // never reached the network

      // Sign-in endpoints stay usable, and requests resume after a sign-in.
      await api.post(
        'auth/staff/logout/',
        body: const {},
        anonymous: true,
        decode: (json) => json,
      );
      closing = false;
      await api.get('patients/', decode: (json) => json);
      expect(adapter.requests, hasLength(2));
      expect(
        adapter.requests.last.headers['Authorization'],
        'Bearer secret-access-token',
      );
    },
  );

  test('adds Idempotency-Key only to writes that pass one', () async {
    final api = client();
    final key = ApiClient.newIdempotencyKey();

    await api.post(
      'billing/payments/',
      body: {'amount': '10.00'},
      idempotencyKey: key,
      decode: (json) => json,
    );
    await api.post('patients/', body: const {}, decode: (json) => json);

    expect(key, matches(RegExp(r'^[0-9a-f]{32}$')));
    expect(adapter.requests[0].headers['Idempotency-Key'], key);
    expect(adapter.requests[1].headers.containsKey('Idempotency-Key'), isFalse);
  });

  test(
    'logs method, path and status but never the query, body or token',
    () async {
      final api = client();

      await api.get(
        'patients/',
        query: {'search': 'Test Patient One'},
        decode: (json) => json,
      );

      final line = logLines.single;
      expect(line, startsWith('GET /api/v1/patients/ -> 200'));
      expect(line, isNot(contains('Test Patient')));
      expect(line, isNot(contains('search')));
      expect(line, isNot(contains('secret-access-token')));
    },
  );

  test(
    'maps the backend error envelope to an ApiException with field errors',
    () async {
      final api = client(
        status: 400,
        body: '{"error": true, "status_code": 400, "message": "phone: invalid", "details": {"phone": ["invalid"]}}',
      );

      Object? error;
      try {
        await api.post('patients/', body: const {}, decode: (json) => json);
      } catch (e) {
        error = e;
      }

      expect(
        error,
        isA<ApiException>().having(
          (e) => e.kind,
          'kind',
          ApiErrorKind.validation,
        ),
      );
      expect((error! as ApiException).fieldErrors, {
        'phone': ['invalid'],
      });
      expect(error.toString(), isNot(contains('phone: invalid')));
    },
  );

  group('token refresh on 401', () {
    late _Tokens tokens;
    late _FakeRefresh refresher;

    /// A server that accepts only [valid] and answers 401 otherwise.
    ApiClient refreshingClient({required String valid}) {
      tokens = _Tokens('expired-token');
      adapter = FakeAdapter((options) async {
        final ok = options.headers['Authorization'] == 'Bearer $valid';
        return ok
            ? jsonBody('{"ok": true}', 200)
            : jsonBody('{"error": true, "status_code": 401}', 401);
      });
      final api = ApiClient(
        config: testConfig,
        accessToken: () async => tokens.access,
        hospitalId: () => 7,
        adapter: adapter,
        log: (_) {},
      );
      refresher = _FakeRefresh(tokens, newToken: valid);
      api.attachRefreshHandler(refresher);
      return api;
    }

    test(
      'renews an expired access token and retries the request once',
      () async {
        final api = refreshingClient(valid: 'fresh-token');

        final body = await api.get('home/stats/', decode: (json) => json);

        expect(body, {'ok': true});
        expect(refresher.calls, 1);
        expect(adapter.requests.map((r) => r.headers['Authorization']), [
          'Bearer expired-token',
          'Bearer fresh-token',
        ]);
      },
    );

    test('concurrent 401s share one refresh', () async {
      final api = refreshingClient(valid: 'fresh-token');

      await Future.wait([
        api.get('a/', decode: (json) => json),
        api.get('b/', decode: (json) => json),
        api.get('c/', decode: (json) => json),
      ]);

      expect(refresher.calls, 1);
    });

    test('a refused refresh ends the session and surfaces 401', () async {
      final api = refreshingClient(valid: 'never-issued');
      refresher.outcome = RefreshOutcome.rejected;

      await expectLater(
        api.get('home/stats/', decode: (json) => json),
        throwsA(
          isA<ApiException>().having(
            (e) => e.kind,
            'kind',
            ApiErrorKind.unauthorized,
          ),
        ),
      );
      expect(refresher.expired, 1);
    });

    test('a refresh that fails on the network keeps the session', () async {
      final api = refreshingClient(valid: 'never-issued');
      refresher.outcome = RefreshOutcome.failed;

      await expectLater(
        api.get('home/stats/', decode: (json) => json),
        throwsA(isA<ApiException>()),
      );
      expect(refresher.expired, 0);
    });

    test(
      'anonymous sign-in calls carry no token and never trigger a refresh',
      () async {
        final api = refreshingClient(valid: 'fresh-token');

        await expectLater(
          api.post(
            'auth/staff/login/',
            body: const {},
            anonymous: true,
            decode: (json) => json,
          ),
          throwsA(isA<ApiException>()),
        );

        expect(
          adapter.requests.single.headers.containsKey('Authorization'),
          isFalse,
        );
        expect(refresher.calls, 0);
      },
    );
  });

  group('both backend error formats', () {
    test(
      'sign-in format: {"error": "<sentence>"} keeps the sentence and flags',
      () async {
        final api = client(
          status: 503,
          body: '{"error": "SMS OTP is turned off on this server.", "otp_unavailable": true}',
        );

        final error = await _failure(
          api.post(
            'auth/staff/login/otp/start/',
            body: const {},
            anonymous: true,
            decode: (j) => j,
          ),
        );

        expect(error.kind, ApiErrorKind.unavailable);
        expect(error.serverMessage, 'SMS OTP is turned off on this server.');
        expect(error.hasFlag('otp_unavailable'), isTrue);
      },
    );

    test('standard envelope: message and details are read, "error": true is not a flag', () async {
      final api = client(
        status: 401,
        body: '{"error": true, "status_code": 401, "message": "Token is invalid", "details": {"detail": "Token is invalid"}}',
      );

      final error = await _failure(
        api.post(
          'auth/token/refresh/',
          body: const {},
          anonymous: true,
          decode: (j) => j,
        ),
      );

      expect(error.kind, ApiErrorKind.unauthorized);
      expect(error.serverMessage, 'Token is invalid');
      expect(error.flags, isEmpty);
    });
  });

  group('ApiException.kindForStatus', () {
    test('covers the statuses the backend documents', () {
      expect(ApiException.kindForStatus(403), ApiErrorKind.forbidden);
      expect(ApiException.kindForStatus(404), ApiErrorKind.notFound);
      expect(ApiException.kindForStatus(409), ApiErrorKind.conflict);
      expect(ApiException.kindForStatus(429), ApiErrorKind.rateLimited);
      expect(ApiException.kindForStatus(503), ApiErrorKind.unavailable);
      expect(ApiException.kindForStatus(500), ApiErrorKind.server);
    });

    test('a connection failure is a network error, a timeout is a timeout', () {
      final options = RequestOptions(path: '/');
      expect(
        ApiException.fromDio(
          DioException.connectionError(
            requestOptions: options,
            reason: 'refused',
          ),
        ).kind,
        ApiErrorKind.network,
      );
      expect(
        ApiException.fromDio(
          DioException.receiveTimeout(
            timeout: Duration.zero,
            requestOptions: options,
          ),
        ).kind,
        ApiErrorKind.timeout,
      );
    });
  });
}

Future<ApiException> _failure(Future<Object?> call) async {
  try {
    await call;
  } on ApiException catch (error) {
    return error;
  }
  throw StateError('expected an ApiException');
}

class _Tokens {
  _Tokens(this.access);

  String access;
}

/// Swaps in [newToken] like AuthService does, with the same single-flight rule.
class _FakeRefresh implements TokenRefreshHandler {
  _FakeRefresh(this.tokens, {required this.newToken});

  final _Tokens tokens;
  final String newToken;
  RefreshOutcome outcome = RefreshOutcome.refreshed;
  int calls = 0;
  int expired = 0;
  Future<RefreshOutcome>? _inFlight;

  @override
  Future<RefreshOutcome> refresh(String usedAccessToken) {
    if (tokens.access != usedAccessToken) {
      return Future.value(RefreshOutcome.refreshed);
    }
    return _inFlight ??= () async {
      calls++;
      await Future<void>.delayed(const Duration(milliseconds: 5));
      if (outcome == RefreshOutcome.refreshed) tokens.access = newToken;
      return outcome;
    }();
  }

  @override
  Future<void> onSessionExpired() async => expired++;
}
