import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// The JWT pair the backend issues at sign-in (`access` 15 min, `refresh` 7 days).
@immutable
class AuthTokens {
  const AuthTokens({required this.access, required this.refresh});

  /// `{"access": "...", "refresh": "..."}`, as every sign-in view and
  /// `auth/token/refresh/` return them. Throws when either is missing.
  factory AuthTokens.fromJson(Object? json) {
    if (json is Map &&
        json['access'] is String &&
        json['refresh'] is String &&
        (json['access'] as String).isNotEmpty &&
        (json['refresh'] as String).isNotEmpty) {
      return AuthTokens(
        access: json['access'] as String,
        refresh: json['refresh'] as String,
      );
    }
    throw const FormatException('sign-in response carries no token pair');
  }

  final String access;
  final String refresh;

  @override
  String toString() => 'AuthTokens(<redacted>)';
}

/// Where the session survives an app restart. Implementations must never
/// use plain SharedPreferences or files: tokens grant access to patient
/// records. Also keeps the chosen hospital and a per-install device id.
abstract interface class TokenStore {
  Future<String?> readAccessToken();
  Future<String?> readRefreshToken();
  Future<void> save(AuthTokens tokens);

  Future<int?> readHospitalId();
  Future<void> saveHospitalId(int? hospitalId);

  /// A random id for this installation, created on first use. Sent as
  /// `device_id` at sign-in so the server's session list can name devices.
  Future<String> deviceId(String Function() create);

  /// Forgets tokens and the chosen hospital (the device id stays).
  Future<void> clear();
}

/// Everything in the Android Keystore / iOS Keychain via flutter_secure_storage.
class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage])
    : _storage =
          storage ??
          const FlutterSecureStorage(
            iOptions: IOSOptions(
              accessibility: KeychainAccessibility.first_unlock_this_device,
            ),
          );

  static const _accessKey = 'hms.access_token';
  static const _refreshKey = 'hms.refresh_token';
  static const _hospitalKey = 'hms.active_hospital';
  static const _deviceKey = 'hms.device_id';

  final FlutterSecureStorage _storage;

  @override
  Future<String?> readAccessToken() => _storage.read(key: _accessKey);

  @override
  Future<String?> readRefreshToken() => _storage.read(key: _refreshKey);

  @override
  Future<void> save(AuthTokens tokens) async {
    await _storage.write(key: _accessKey, value: tokens.access);
    await _storage.write(key: _refreshKey, value: tokens.refresh);
  }

  @override
  Future<int?> readHospitalId() async =>
      int.tryParse(await _storage.read(key: _hospitalKey) ?? '');

  @override
  Future<void> saveHospitalId(int? hospitalId) => hospitalId == null
      ? _storage.delete(key: _hospitalKey)
      : _storage.write(key: _hospitalKey, value: '$hospitalId');

  @override
  Future<String> deviceId(String Function() create) async {
    final existing = await _storage.read(key: _deviceKey);
    if (existing != null && existing.isNotEmpty) return existing;
    final created = create();
    await _storage.write(key: _deviceKey, value: created);
    return created;
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _hospitalKey);
  }
}

/// Keeps everything in memory only; for tests.
class InMemoryTokenStore implements TokenStore {
  AuthTokens? _tokens;
  int? _hospitalId;
  String? _deviceId;

  @override
  Future<String?> readAccessToken() async => _tokens?.access;

  @override
  Future<String?> readRefreshToken() async => _tokens?.refresh;

  @override
  Future<void> save(AuthTokens tokens) async => _tokens = tokens;

  @override
  Future<int?> readHospitalId() async => _hospitalId;

  @override
  Future<void> saveHospitalId(int? hospitalId) async =>
      _hospitalId = hospitalId;

  @override
  Future<String> deviceId(String Function() create) async =>
      _deviceId ??= create();

  @override
  Future<void> clear() async {
    _tokens = null;
    _hospitalId = null;
  }
}

/// Whether this installation has started before. Kept in SharedPreferences,
/// which, unlike the iOS Keychain, is deleted together with the app.
abstract interface class InstallMarker {
  Future<bool> isSet();
  Future<void> set();
}

class SharedPreferencesInstallMarker implements InstallMarker {
  static const _key = 'hms.installed';

  @override
  Future<bool> isSet() async =>
      (await SharedPreferences.getInstance()).getBool(_key) ?? false;

  @override
  Future<void> set() async =>
      (await SharedPreferences.getInstance()).setBool(_key, true);
}

/// iOS keeps Keychain items after the app is deleted, so a reinstall (or
/// the next owner of a reset-but-restored phone) would resume the previous
/// person's session. On an installation's first start, stored tokens and
/// the chosen hospital are forgotten before anything reads them.
Future<void> forgetSessionFromPreviousInstall(
  TokenStore store,
  InstallMarker marker,
) async {
  if (await marker.isSet()) return;
  await store.clear();
  await marker.set();
}
