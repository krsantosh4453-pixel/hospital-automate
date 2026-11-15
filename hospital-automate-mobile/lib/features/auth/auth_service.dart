import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../../core/network/api_client.dart';
import '../../core/network/api_exception.dart';
import '../../core/security/session_controller.dart';
import '../../core/security/token_store.dart';
import 'auth_models.dart';
import 'auth_repository.dart';
import 'google_identity.dart';

/// The account signed in but is not one the app serves (platform staff, or
/// an account with no staff membership or patient record).
class UnsupportedAccountException implements Exception {
  const UnsupportedAccountException();
}

/// Result of the first staff step: signed in, or a code is needed.
sealed class StaffSignInResult {
  const StaffSignInResult();
}

class StaffSignedIn extends StaffSignInResult {
  const StaffSignedIn();
}

class StaffOtpNeeded extends StaffSignInResult {
  const StaffOtpNeeded(this.challenge);

  final StaffOtpChallenge challenge;
}

/// Signs people in and out and keeps the token pair fresh.
///
/// * Every sign-in ends in [completeSignIn]: tokens to the secure store, then
///   `me/contexts` + the profile build the session. If that fails, the
///   tokens are dropped again so no half-signed-in state survives.
/// * [refresh] renews the access token once for any number of concurrent
///   requests that failed with 401.
/// * Passwords, codes and challenges pass through; none is stored or logged.
class AuthService implements TokenRefreshHandler {
  AuthService({
    required this._repository,
    required this._session,
    required this._store,
    required this._appVersion,
    this._google,
    TargetPlatform? platform,
    Random? random,
  }) : _platform = platform ?? defaultTargetPlatform,
       _random = random ?? Random.secure();

  final AuthRepository _repository;
  final SessionController _session;
  final TokenStore _store;
  final String _appVersion;
  final GoogleIdentity? _google;
  final TargetPlatform _platform;
  final Random _random;
  Future<RefreshOutcome>? _refreshing;

  // ---- Staff -------------------------------------------------------------

  /// Password step. As on the web: try the SMS code first; when the server
  /// says OTP cannot be used (`otp_unavailable`: switched off, not set up,
  /// no mobile number) sign in with the password, which the server itself
  /// refuses when its policy requires OTP.
  Future<StaffSignInResult> staffSignIn(
    String username,
    String password,
  ) async {
    final device = await deviceInfo();
    try {
      final challenge = await _repository.staffStartOtp(
        username,
        password,
        device,
      );
      return StaffOtpNeeded(challenge);
    } on ApiException catch (error) {
      if (!error.hasFlag('otp_unavailable')) rethrow;
    }
    await completeSignIn(
      await _repository.staffPasswordLogin(username, password, device),
    );
    return const StaffSignedIn();
  }

  Future<void> staffVerifyOtp(StaffOtpChallenge challenge, String otp) async =>
      completeSignIn(
        await _repository.staffVerifyOtp(
          challenge.challenge,
          otp,
          await deviceInfo(),
        ),
      );

  Future<void> staffResendOtp(StaffOtpChallenge challenge) =>
      _repository.staffResendOtp(challenge.challenge);

  Future<void> requestPasswordReset(String username) =>
      _repository.requestPasswordReset(username);

  Future<void> confirmPasswordReset(
    String username,
    String code,
    String newPassword,
  ) => _repository.confirmPasswordReset(username, code, newPassword);

  // ---- Patients ----------------------------------------------------------

  Future<OtpDelivery> patientRequestOtp(String phone) =>
      _repository.patientRequestOtp(phone);

  Future<void> patientVerifyOtp(String phone, String otp) async =>
      completeSignIn(
        await _repository.patientVerifyOtp(phone, otp, await deviceInfo()),
      );

  Future<void> patientEmailLogin(String email, String password) async =>
      completeSignIn(
        await _repository.patientEmailLogin(
          email,
          password,
          await deviceInfo(),
        ),
      );

  Future<void> patientIdLogin(String identifier, String password) async =>
      completeSignIn(
        await _repository.patientIdLogin(
          identifier,
          password,
          await deviceInfo(),
        ),
      );

  Future<RegistrationResult> registerPatient(
    PatientRegistration registration,
  ) => _repository.registerPatient(registration);

  Future<OtpDelivery> requestEmailOtp(String email) =>
      _repository.requestEmailOtp(email);

  Future<void> verifyEmailOtp(String email, String otp) =>
      _repository.verifyEmailOtp(email, otp);

  // ---- Family member / caregiver (view-only) ---------------------------

  Future<OtpDelivery> proxyRequestOtp(String phone) =>
      _repository.proxyRequestOtp(phone);

  Future<ProxyVerification> proxyVerifyOtp(String phone, String otp) =>
      _repository.proxyVerifyOtp(phone, otp);

  /// Opens [grant]'s records with the ticket from [proxyVerifyOtp].
  Future<void> proxySignIn(String ticket, ProxyGrantChoice grant) async =>
      completeSignIn(
        await _repository.proxyLogin(ticket, grant.id, await deviceInfo()),
      );

  // ---- Google (patients) ------------------------------------------------

  /// Whether this build can offer "Continue with Google".
  bool get googleAvailable => _google?.isAvailable ?? false;

  /// Google's account picker, then the backend checks the ID token.
  /// Returns false when the person closed the picker (nothing changes).
  Future<bool> googleSignIn() async {
    final google = _google;
    if (google == null) {
      throw const GoogleSignInFailure(misconfigured: true);
    }
    final idToken = await google.requestIdToken();
    if (idToken == null) return false;
    await completeSignIn(
      await _repository.googleLogin(idToken, await deviceInfo()),
    );
    return true;
  }

  // ---- Session -----------------------------------------------------------

  /// Stores [tokens] and builds the session from the server's view of the
  /// account. Throws (and forgets the tokens) if that view cannot be read.
  Future<void> completeSignIn(AuthTokens tokens) async {
    await _store.save(tokens);
    try {
      await _loadSession();
    } catch (_) {
      await _store.clear();
      rethrow;
    }
  }

  /// At start-up: resume a stored session. With no tokens the app is signed
  /// out; if the server refuses them, they are dropped; if it cannot be
  /// reached, the session waits in [SessionStatus.restoreFailed] for [restore]
  /// to be tried again.
  Future<void> restore() async {
    _session.setStatus(SessionStatus.restoring);
    if (await _store.readRefreshToken() == null) {
      _session.setStatus(SessionStatus.signedOut);
      return;
    }
    try {
      await _loadSession();
    } on ApiException catch (error) {
      if (error.kind == ApiErrorKind.unauthorized ||
          error.kind == ApiErrorKind.forbidden) {
        await _session.signOut(expired: true);
      } else {
        _session.setStatus(SessionStatus.restoreFailed);
      }
    } on Object {
      // Unsupported account or an unreadable answer: start clean.
      await _session.signOut();
    }
  }

  Future<void> _loadSession() async {
    final contexts = await _repository.meContexts();
    final accountType = contexts.accountType;
    if (accountType == null) throw const UnsupportedAccountException();
    final user = accountType == AccountType.staff
        ? await _repository.staffMe()
        : await _repository.patientMe(accountType);
    await _session.start(
      SessionState(user: user, hospitals: contexts.hospitals),
      preferredHospitalId: await _store.readHospitalId(),
    );
  }

  /// Signs this device out on the server (best effort: an unreachable
  /// server must not keep the person signed in), then clears everything.
  Future<void> signOut() async {
    final refreshToken = await _store.readRefreshToken();
    if (refreshToken != null) {
      try {
        await _repository.logout(refreshToken);
      } on ApiException {
        // Already invalid or offline; the local sign-out below still happens.
      }
    }
    await _session.signOut();
  }

  /// Signs every device out, this one included. Throws if the server
  /// refuses, so the person is told it did not happen.
  Future<void> logoutAll() async {
    await _repository.logoutAll();
    await _session.signOut();
  }

  Future<List<DeviceSessionInfo>> sessions() => _repository.sessions();

  /// Signs one device out; revoking this device signs it out here too.
  Future<void> revokeSession(DeviceSessionInfo device) async {
    await _repository.revokeSession(device.id);
    if (device.current) await _session.signOut();
  }

  Future<DeviceInfo> deviceInfo() async => DeviceInfo(
    deviceId: await _store.deviceId(() => _randomHex(32)),
    platform: switch (_platform) {
      TargetPlatform.android => 'android',
      TargetPlatform.iOS => 'ios',
      _ => 'other',
    },
    appVersion: _appVersion,
  );

  String _randomHex(int length) => List.generate(
    length,
    (_) => _random.nextInt(16).toRadixString(16),
  ).join();

  // ---- Token refresh (TokenRefreshHandler) -----------------------------

  @override
  Future<RefreshOutcome> refresh(String usedAccessToken) async {
    // Another request already renewed the token: just retry with it.
    final current = await _store.readAccessToken();
    if (current != null && current != usedAccessToken) {
      return RefreshOutcome.refreshed;
    }
    return _refreshing ??= _renew().whenComplete(() => _refreshing = null);
  }

  Future<RefreshOutcome> _renew() async {
    final refreshToken = await _store.readRefreshToken();
    if (refreshToken == null) return RefreshOutcome.rejected;
    try {
      await _store.save(await _repository.refresh(refreshToken));
      return RefreshOutcome.refreshed;
    } on ApiException catch (error) {
      // 401: expired, rotated, revoked or signed out. 400: malformed token.
      final refused =
          error.kind == ApiErrorKind.unauthorized ||
          error.kind == ApiErrorKind.validation;
      return refused ? RefreshOutcome.rejected : RefreshOutcome.failed;
    } on FormatException {
      return RefreshOutcome.failed;
    }
  }

  @override
  Future<void> onSessionExpired() async {
    if (_session.status == SessionStatus.signedOut) return;
    await _session.signOut(expired: true);
  }
}
