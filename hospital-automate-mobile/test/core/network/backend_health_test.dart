import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hms_mobile/core/network/backend_health.dart';

/// Answers every request with [respond] instead of touching the network.
class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.respond);

  final Future<ResponseBody> Function(RequestOptions options) respond;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) => respond(options);

  @override
  void close({bool force = false}) {}
}

Dio _dioReturning(
  Future<ResponseBody> Function(RequestOptions options) respond,
) => Dio()..httpClientAdapter = _FakeAdapter(respond);

ResponseBody _json(String body, int status) => ResponseBody.fromString(
  body,
  status,
  headers: {
    Headers.contentTypeHeader: [Headers.jsonContentType],
  },
);

void main() {
  const url = 'http://10.0.2.2:8000/health/';

  test('reports reachable when the backend says healthy', () async {
    final dio = _dioReturning(
      (_) async =>
          _json('{"status": "healthy", "service": "hms-backend"}', 200),
    );

    final result = await BackendHealth(dio).check(url);

    expect(result.reachable, isTrue);
    expect(result.message, 'hms-backend is healthy');
  });

  test(
    'explains a 400, which Django sends when the host is not in ALLOWED_HOSTS',
    () async {
      final dio = _dioReturning((_) async => _json('{}', 400));

      final result = await BackendHealth(dio).check(url);

      expect(result.reachable, isFalse);
      expect(result.message, contains('ALLOWED_HOSTS'));
    },
  );

  test(
    'explains a connection failure as the server not running or unreachable',
    () async {
      final dio = _dioReturning((options) async {
        throw DioException.connectionError(
          requestOptions: options,
          reason: 'refused',
        );
      });

      final result = await BackendHealth(dio).check(url);

      expect(result.reachable, isFalse);
      expect(result.message, contains('Cannot reach'));
    },
  );

  test('treats an unexpected body as unhealthy', () async {
    final dio = _dioReturning(
      (_) async => _json('{"status": "starting"}', 200),
    );

    final result = await BackendHealth(dio).check(url);

    expect(result.reachable, isFalse);
    expect(result.message, contains('starting'));
  });
}
